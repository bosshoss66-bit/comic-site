#!/usr/bin/env python3
"""Browser-based local comic manager.

Launch this script (or Comic Manager.command) and it opens a local web UI
for adding/removing comics without terminal commands.
"""

from __future__ import annotations

import cgi
import html
import mimetypes
import socket
import socketserver
import subprocess
import tempfile
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import comic_admin

HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB
LIVE_SITE_URL = "https://badkyndcomics.netlify.app"
ROOT_DIR = SCRIPT_DIR.parent


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "on", "yes"}


def run_local_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT_DIR, text=True, capture_output=True, check=False)


def git_text(args: list[str]) -> str:
    result = run_local_command(["git", *args])
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def normalize_repo_url(remote_url: str) -> str:
    raw = remote_url.strip()
    if not raw:
        return ""
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.removeprefix("git@github.com:")
    if raw.endswith(".git"):
        raw = raw[:-4]
    return raw


def get_netlify_project_slug(live_site_url: str) -> str:
    parsed = urllib.parse.urlparse(live_site_url)
    host = parsed.netloc.split(":")[0]
    if host.endswith(".netlify.app"):
        return host.split(".")[0]
    return ""


def get_deployment_status() -> dict[str, Any]:
    branch = git_text(["branch", "--show-current"]) or "unknown"
    head_short = git_text(["rev-parse", "--short", "HEAD"]) or "unknown"
    head_full = git_text(["rev-parse", "HEAD"])
    head_subject = git_text(["log", "-1", "--pretty=%s"]) or ""
    porcelain = git_text(["status", "--porcelain"])
    working_clean = not bool(porcelain)
    remote_url = normalize_repo_url(git_text(["remote", "get-url", "origin"]))

    sync_state = "Unknown"
    ahead = behind = 0
    ahead_behind = run_local_command(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"])
    if ahead_behind.returncode == 0:
        parts = (ahead_behind.stdout or "").strip().split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            behind = int(parts[0])
            ahead = int(parts[1])
            if ahead == 0 and behind == 0:
                sync_state = "Synced with origin/main"
            elif ahead > 0 and behind == 0:
                sync_state = f"Ahead by {ahead} commit(s)"
            elif ahead == 0 and behind > 0:
                sync_state = f"Behind by {behind} commit(s)"
            else:
                sync_state = f"Diverged (ahead {ahead}, behind {behind})"

    netlify_project_slug = get_netlify_project_slug(LIVE_SITE_URL)
    netlify_project_url = f"https://app.netlify.com/projects/{netlify_project_slug}" if netlify_project_slug else ""
    netlify_deploys_url = f"{netlify_project_url}/deploys" if netlify_project_url else ""

    commit_url = f"{remote_url}/commit/{head_full}" if remote_url and head_full else ""
    commits_url = f"{remote_url}/commits/main" if remote_url else ""

    return {
        "branch": branch,
        "head_short": head_short,
        "head_subject": head_subject,
        "working_clean": working_clean,
        "sync_state": sync_state,
        "remote_url": remote_url,
        "commit_url": commit_url,
        "commits_url": commits_url,
        "netlify_project_url": netlify_project_url,
        "netlify_deploys_url": netlify_deploys_url,
    }


def comic_cards(comics: list[dict]) -> str:
    if not comics:
        return "<p class='empty-state'>No comics yet. Add a comic from the form on the left.</p>"

    cards: list[str] = []
    for comic in comics:
        slug = str(comic.get("slug", "") or "")
        title = str(comic.get("title", "") or slug)
        pages = len(comic.get("pages", []))
        cover = str(comic.get("cover", "") or "")
        description = str(comic.get("description", "") or "")
        description_text = description if description else "No description provided."
        reader_url = f"{LIVE_SITE_URL}/comic/{urllib.parse.quote(slug)}/1"

        cover_html = (
            f"<img class='cover-thumb' src='{esc(cover)}' alt='Cover for {esc(title)}' loading='lazy' />"
            if cover
            else "<div class='cover-thumb placeholder'>No cover</div>"
        )

        cards.append(
            "<article class='comic-card'>"
            "<div class='comic-card-top'>"
            f"{cover_html}"
            "<div class='comic-card-main'>"
            f"<h3 class='comic-title'>{esc(title)}</h3>"
            f"<p class='slug-line'>{esc(slug)}</p>"
            "<div class='comic-meta'>"
            f"<span>{pages} page(s)</span>"
            f"<a href='{esc(reader_url)}' target='_blank' rel='noopener'>Open reader</a>"
            "</div>"
            f"<p class='description'>{esc(description_text)}</p>"
            "</div>"
            "</div>"
            f"<p class='cover-path'><code>{esc(cover or 'Cover will use first page')}</code></p>"
            "</article>"
        )
    return "\n".join(cards)


def comic_options(comics: list[dict]) -> str:
    options = []
    for comic in comics:
        slug = comic.get("slug", "")
        title = comic.get("title", slug)
        options.append(f"<option value='{esc(slug)}'>{esc(title)} ({esc(slug)})</option>")
    return "\n".join(options)


def render_deployment_panel(status: dict[str, Any]) -> str:
    head_line = esc(status["head_short"])
    if status["head_subject"]:
        head_line += f" - {esc(status['head_subject'])}"

    clean_text = "Clean working tree" if status["working_clean"] else "Uncommitted changes present"

    links: list[str] = []
    if status["remote_url"]:
        links.append(
            f"<a href='{esc(status['remote_url'])}' target='_blank' rel='noopener'>GitHub Repository</a>"
        )
    if status["commit_url"]:
        links.append(
            f"<a href='{esc(status['commit_url'])}' target='_blank' rel='noopener'>Latest Commit</a>"
        )
    if status["commits_url"]:
        links.append(
            f"<a href='{esc(status['commits_url'])}' target='_blank' rel='noopener'>Commit History</a>"
        )
    if status["netlify_project_url"]:
        links.append(
            f"<a href='{esc(status['netlify_project_url'])}' target='_blank' rel='noopener'>Netlify Project</a>"
        )
    if status["netlify_deploys_url"]:
        links.append(
            f"<a href='{esc(status['netlify_deploys_url'])}' target='_blank' rel='noopener'>Netlify Deploys</a>"
        )

    links_html = " ".join(links) if links else "<span class='muted'>No remote/deploy links available.</span>"

    return (
        "<section class='card deploy-card'>"
        "<div class='section-heading'>"
        "<h2>Deployment Status</h2>"
        "<p class='hint'>Quick visibility into local git state and Netlify links.</p>"
        "</div>"
        "<div class='stat-grid'>"
        "<div class='stat-item'>"
        "<span class='label'>Branch</span>"
        f"<strong>{esc(status['branch'])}</strong>"
        "</div>"
        "<div class='stat-item'>"
        "<span class='label'>Latest commit</span>"
        f"<strong>{head_line}</strong>"
        "</div>"
        "<div class='stat-item'>"
        "<span class='label'>Repo state</span>"
        f"<strong>{esc(clean_text)}</strong>"
        "</div>"
        "<div class='stat-item'>"
        "<span class='label'>Sync</span>"
        f"<strong>{esc(status['sync_state'])}</strong>"
        "</div>"
        "</div>"
        f"<div class='link-row'>{links_html}</div>"
        "</section>"
    )


def render_page(message: str = "", is_error: bool = False) -> bytes:
    comics = comic_admin.get_comics()
    comics = sorted(comics, key=lambda c: (c.get("title", "").lower(), c.get("slug", "").lower()))
    deploy = get_deployment_status()

    status_class = "status error" if is_error else "status ok"
    status_html = (
        f"<div class='{status_class}'>{esc(message)}</div>" if message else "<div class='status muted'>Ready.</div>"
    )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Comic Manager</title>
  <style>
    @font-face {{
      font-family: "Mochibop";
      src: url("/assets/fonts/Mochibop-Demo.ttf") format("truetype");
      font-display: swap;
    }}
    :root {{
      --bg: #f4f4f8;
      --bg-accent: #fef9ee;
      --card: #ffffff;
      --line: #ddd9cf;
      --ink: #1f2024;
      --ink-soft: #5d6572;
      --brand: #ea5b2b;
      --brand-strong: #be3f14;
      --brand-soft: #fff1e8;
      --ok: #0f5132;
      --ok-bg: #d1f5dd;
      --err: #7f1d1d;
      --err-bg: #fee2e2;
      --shadow: 0 14px 40px rgba(31, 32, 36, 0.11);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      line-height: 1.45;
    }}
    .page {{
      width: min(1500px, 100%);
      margin: 0 auto;
      padding: 22px 20px 28px;
    }}
    h1, h2, h3 {{ margin: 0; }}
    .page-header {{
      margin-bottom: 14px;
      padding: 18px 20px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background:
        radial-gradient(circle at top right, rgba(234, 91, 43, 0.14), transparent 48%),
        linear-gradient(145deg, var(--bg-accent), #ffffff 70%);
      box-shadow: var(--shadow);
    }}
    .page-header h1 {{
      font-family: "Mochibop", "Trebuchet MS", sans-serif;
      font-size: clamp(2rem, 3vw + 1rem, 3.35rem);
      color: #20242d;
      margin-bottom: 6px;
      letter-spacing: 0.02em;
    }}
    .page-header p {{
      margin: 0;
      color: var(--ink-soft);
      font-size: 0.98rem;
    }}
    .page-header a {{
      color: var(--brand-strong);
      font-weight: 700;
      text-decoration-thickness: 2px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .stack {{
      display: grid;
      gap: 16px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .section-heading {{
      margin-bottom: 10px;
    }}
    .section-heading h2 {{
      font-size: 1.2rem;
      margin-bottom: 3px;
    }}
    .label {{
      color: var(--ink-soft);
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      font-weight: 800;
      display: block;
      margin-bottom: 4px;
    }}
    .field {{
      margin: 12px 0 0;
    }}
    label {{
      display: block;
      margin: 0 0 5px;
      font-weight: 700;
      font-size: 0.94rem;
    }}
    input[type="text"], textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }}
    input[type="text"]:focus, textarea:focus, select:focus {{
      outline: 3px solid rgba(234, 91, 43, 0.22);
      border-color: #d7b6a7;
      outline-offset: 1px;
    }}
    textarea {{ min-height: 78px; resize: vertical; }}
    .upload-area {{
      margin-top: 12px;
      border: 1px dashed #cbbda9;
      border-radius: 12px;
      background: #fffaf4;
      padding: 11px 12px;
    }}
    .upload-area .field:first-child {{
      margin-top: 0;
    }}
    input[type="file"] {{
      width: 100%;
      margin-top: 2px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 7px;
      background: #fff;
    }}
    .row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 12px;
    }}
    .checkbox {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      font-weight: 600;
      color: #384250;
    }}
    .checkbox input {{
      accent-color: var(--brand);
      width: 16px;
      height: 16px;
      margin: 0;
    }}
    button {{
      border: 1px solid var(--brand-strong);
      background: var(--brand);
      color: white;
      font: inherit;
      font-weight: 700;
      border-radius: 11px;
      padding: 9px 14px;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
    }}
    button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 10px 20px rgba(190, 63, 20, 0.2);
      filter: brightness(1.02);
    }}
    button:focus-visible {{
      outline: 3px solid rgba(234, 91, 43, 0.24);
      outline-offset: 2px;
    }}
    button.secondary {{
      background: #fff;
      color: #1f2430;
      border-color: var(--line);
    }}
    .status {{
      margin: 0 0 14px;
      border-radius: 10px;
      padding: 10px 12px;
      font-weight: 700;
      border: 1px solid transparent;
    }}
    .status.ok {{ background: var(--ok-bg); color: var(--ok); }}
    .status.error {{ background: var(--err-bg); color: var(--err); }}
    .status.muted {{
      background: #edf3fb;
      color: #334155;
      border-color: #cfdceb;
    }}
    .hint {{
      color: var(--ink-soft);
      font-size: 0.87rem;
      margin: 7px 0 0;
    }}
    .deploy-card .stat-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }}
    .deploy-card .stat-item {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffcf8;
      padding: 8px 10px;
      min-width: 0;
    }}
    .deploy-card strong {{
      font-size: 0.92rem;
      display: block;
      word-break: break-word;
    }}
    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 11px;
    }}
    .link-row a {{
      color: #21437a;
      font-weight: 700;
      text-decoration-thickness: 2px;
    }}
    .muted {{
      color: var(--ink-soft);
      font-size: 0.9rem;
    }}
    .comic-list {{
      display: grid;
      gap: 10px;
    }}
    .comic-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px;
      background: #fffdfa;
    }}
    .comic-card-top {{
      display: grid;
      grid-template-columns: 76px minmax(0, 1fr);
      gap: 10px;
    }}
    .cover-thumb {{
      width: 76px;
      height: 106px;
      border-radius: 9px;
      object-fit: cover;
      border: 1px solid var(--line);
      background: #f0ece3;
    }}
    .cover-thumb.placeholder {{
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      color: #6b7280;
      font-size: 0.74rem;
      padding: 6px;
    }}
    .comic-card-main {{
      min-width: 0;
    }}
    .comic-title {{
      margin: 0;
      font-family: "Mochibop", "Trebuchet MS", sans-serif;
      font-size: 1.34rem;
      line-height: 1;
      color: #222531;
    }}
    .slug-line {{
      margin: 4px 0 0;
      font-size: 0.88rem;
      color: #687485;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      word-break: break-word;
    }}
    .comic-meta {{
      margin-top: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      font-size: 0.86rem;
      color: #505866;
      font-weight: 700;
    }}
    .comic-meta a {{
      color: #1e4f8f;
      text-decoration-thickness: 2px;
      white-space: nowrap;
    }}
    .description {{
      margin: 6px 0 0;
      color: #333b46;
      font-size: 0.92rem;
    }}
    .cover-path {{
      margin: 7px 0 0;
      color: #667180;
      font-size: 0.78rem;
      overflow-wrap: anywhere;
    }}
    .empty-state {{
      margin: 4px 0 0;
      border: 1px dashed var(--line);
      border-radius: 11px;
      padding: 13px;
      color: var(--ink-soft);
      background: #fffefb;
    }}
    @media (max-width: 1100px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .page {{
        padding: 16px;
      }}
    }}
    @media (max-width: 640px) {{
      .comic-card-top {{
        grid-template-columns: 1fr;
      }}
      .cover-thumb {{
        width: 100%;
        height: auto;
        aspect-ratio: 1 / 1.4;
      }}
      .deploy-card .stat-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
  <header class="page-header">
    <h1>Comic Manager</h1>
    <p>
      Local admin panel for adding, replacing, deleting, and publishing comics.
      Live site: <a href="{esc(LIVE_SITE_URL)}" target="_blank" rel="noopener">{esc(LIVE_SITE_URL)}</a>
    </p>
  </header>
  {status_html}

  <div class="layout">
    <div class="stack">
    <section class="card">
      <div class="section-heading">
        <h2>Add / Replace Comic</h2>
        <p class="hint">Fill the metadata, then upload pages in reading order.</p>
      </div>
      <form method="post" action="/add" enctype="multipart/form-data">
        <div class="field">
          <label for="slug">Slug</label>
          <input id="slug" name="slug" type="text" placeholder="my-comic-episode-one" required />
        </div>
        <div class="field">
          <label for="title">Title</label>
          <input id="title" name="title" type="text" placeholder="My Comic: Episode One" required />
        </div>
        <div class="field">
          <label for="description">Description</label>
          <textarea id="description" name="description" placeholder="Short description"></textarea>
        </div>

        <div class="upload-area">
          <div class="field">
            <label for="pages">Comic Pages (select all pages in order)</label>
            <input id="pages" name="pages" type="file" accept="image/*" multiple required />
          </div>
          <div class="field">
            <label for="cover">Optional Cover Image (defaults to first page)</label>
            <input id="cover" name="cover" type="file" accept="image/*" />
          </div>
        </div>
        <div class="row">
          <label class="checkbox"><input type="checkbox" name="replace" /> Replace if slug already exists</label>
        </div>
        <div class="row">
          <button type="submit">Add / Replace Comic</button>
          <button class="secondary" type="reset">Clear</button>
        </div>
      </form>
      <p class="hint">Uploads are converted/optimized to <code>.opt.jpg</code> automatically.</p>
    </section>

    <section class="card">
      <div class="section-heading">
        <h2>Delete Comic</h2>
        <p class="hint">Choose a comic slug and remove it from the library.</p>
      </div>
      <form method="post" action="/delete">
        <div class="field">
          <label for="delete_slug">Select Comic</label>
          <select id="delete_slug" name="slug" required>
            <option value="">Choose comic...</option>
            {comic_options(comics)}
          </select>
        </div>
        <div class="row">
          <label class="checkbox"><input type="checkbox" name="delete_files" checked /> Also delete files in uploads/&lt;slug&gt;</label>
        </div>
        <div class="row">
          <button type="submit">Delete Selected Comic</button>
        </div>
      </form>
      <p class="hint">Delete removes from <code>data/comics.json</code> and optionally from <code>uploads/</code>.</p>
    </section>

    <section class="card">
      <div class="section-heading">
        <h2>Publish to GitHub</h2>
        <p class="hint">Run preflight, commit all staged changes, and push to origin/main.</p>
      </div>
      <form method="post" action="/publish">
        <div class="field">
          <label for="commit_message">Commit Message</label>
          <input
            id="commit_message"
            name="commit_message"
            type="text"
            placeholder="Update comic library"
            value="Update comic library"
          />
        </div>
        <div class="row">
          <label class="checkbox"><input type="checkbox" name="apply_prune" checked /> Run image prune during preflight</label>
        </div>
        <div class="row">
          <button type="submit">Publish Changes</button>
        </div>
      </form>
    </section>
    </div>

    <div class="stack">
      {render_deployment_panel(deploy)}

      <section class="card">
        <div class="section-heading">
          <h2>Current Comics</h2>
          <p class="hint">Live library metadata from <code>data/comics.json</code>.</p>
        </div>
        <div class="comic-list">
          {comic_cards(comics)}
        </div>
      </section>
    </div>
    </div>
  </div>
  </div>
</body>
</html>
"""
    return html_doc.encode("utf-8")


class ManagerHandler(BaseHTTPRequestHandler):
    server_version = "ComicManagerHTTP/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path.startswith("/assets/") or parsed.path.startswith("/uploads/"):
            self._send_static(parsed.path.lstrip("/"))
            return

        if parsed.path == "/":
            params = urllib.parse.parse_qs(parsed.query)
            message = params.get("message", [""])[0]
            is_error = parse_bool(params.get("error", ["0"])[0])
            body = render_page(message=message, is_error=is_error)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._send_not_found()

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/add":
                self._handle_add()
                return
            if self.path == "/delete":
                self._handle_delete()
                return
            if self.path == "/publish":
                self._handle_publish()
                return
            self._send_not_found()
        except Exception as error:  # pragma: no cover
            self._redirect(f"Request failed: {error}", error=True)

    def _handle_add(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > MAX_UPLOAD_BYTES:
            self._redirect("Upload too large. Keep total files under 500MB.", error=True)
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )

            slug = (form.getfirst("slug") or "").strip()
            title = (form.getfirst("title") or "").strip()
            description = (form.getfirst("description") or "").strip()
            replace = parse_bool(form.getfirst("replace"))

            pages_field = form["pages"] if "pages" in form else None
            if pages_field is None:
                self._redirect("No page images were uploaded.", error=True)
                return

            page_items = pages_field if isinstance(pages_field, list) else [pages_field]
            page_items = [item for item in page_items if getattr(item, "filename", "")]
            if not page_items:
                self._redirect("No page images were uploaded.", error=True)
                return

            cover_item = form["cover"] if "cover" in form else None
            has_cover = cover_item is not None and bool(getattr(cover_item, "filename", ""))

            with tempfile.TemporaryDirectory(prefix="comic-manager-") as tmp_dir:
                tmp_path = Path(tmp_dir)
                pages_dir = tmp_path / "pages"
                pages_dir.mkdir(parents=True, exist_ok=True)

                for index, item in enumerate(page_items, start=1):
                    safe_name = Path(item.filename).name or f"page-{index}.jpg"
                    destination = pages_dir / f"{index:03d}_{safe_name}"
                    data = item.file.read()
                    destination.write_bytes(data)

                cover_path = None
                if has_cover:
                    safe_cover = Path(cover_item.filename).name or "cover.jpg"
                    cover_path = tmp_path / f"cover_{safe_cover}"
                    cover_path.write_bytes(cover_item.file.read())

                comic = comic_admin.add_comic(
                    slug=slug,
                    title=title,
                    description=description,
                    source_dir=pages_dir,
                    cover=cover_path,
                    replace=replace,
                )

            self._redirect(
                f"Saved comic '{comic.get('title', slug)}' with {len(comic.get('pages', []))} pages.",
                error=False,
            )
        except Exception as error:  # pragma: no cover
            self._redirect(str(error), error=True)

    def _handle_delete(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))

        slug = (params.get("slug", [""])[0] or "").strip()
        delete_files = parse_bool(params.get("delete_files", ["0"])[0])

        if not slug:
            self._redirect("Select a comic to delete.", error=True)
            return

        try:
            removed = comic_admin.delete_comic(slug=slug, delete_files=delete_files)
            self._redirect(f"Deleted comic '{removed.get('title', slug)}'.", error=False)
        except Exception as error:  # pragma: no cover
            self._redirect(str(error), error=True)

    @staticmethod
    def _run_command(command: list[str]) -> subprocess.CompletedProcess:
        return run_local_command(command)

    @staticmethod
    def _compact_output(result: subprocess.CompletedProcess, limit: int = 300) -> str:
        text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        text = " ".join(text.strip().split())
        return text[:limit]

    def _handle_publish(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))

        commit_message = (params.get("commit_message", [""])[0] or "").strip() or "Update comic library"
        apply_prune = parse_bool(params.get("apply_prune", ["0"])[0])

        prep_command = ["./scripts/release-prep.sh", "--apply-prune"] if apply_prune else ["./scripts/release-prep.sh"]
        prep = self._run_command(prep_command)
        if prep.returncode != 0:
            details = self._compact_output(prep)
            message = "Preflight failed."
            if details:
                message += f" {details}"
            self._redirect(message, error=True)
            return

        add = self._run_command(["git", "add", "."])
        if add.returncode != 0:
            details = self._compact_output(add)
            message = "git add failed."
            if details:
                message += f" {details}"
            self._redirect(message, error=True)
            return

        staged = self._run_command(["git", "diff", "--cached", "--quiet"])
        if staged.returncode == 0:
            self._redirect("No changes to publish.", error=False)
            return
        if staged.returncode not in (0, 1):
            self._redirect("Could not determine staged changes.", error=True)
            return

        commit = self._run_command(["git", "commit", "-m", commit_message])
        if commit.returncode != 0:
            details = self._compact_output(commit)
            message = "git commit failed."
            if details:
                message += f" {details}"
            self._redirect(message, error=True)
            return

        push = self._run_command(["git", "push"])
        if push.returncode != 0:
            details = self._compact_output(push)
            message = "git push failed."
            if details:
                message += f" {details}"
            self._redirect(message, error=True)
            return

        new_head = self._run_command(["git", "rev-parse", "--short", "HEAD"])
        commit_hash = self._compact_output(new_head, limit=16) if new_head.returncode == 0 else ""
        done_message = "Published to GitHub successfully."
        if commit_hash:
            done_message += f" Commit {commit_hash}."
        self._redirect(done_message, error=False)

    def _redirect(self, message: str, error: bool) -> None:
        query = urllib.parse.urlencode({"message": message, "error": "1" if error else "0"})
        self.send_response(303)
        self.send_header("Location", f"/?{query}")
        self.end_headers()

    def _send_static(self, relative_url_path: str) -> None:
        decoded = urllib.parse.unquote(relative_url_path)
        rel_path = Path(decoded)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            self._send_not_found()
            return

        root = ROOT_DIR.resolve()
        file_path = (ROOT_DIR / rel_path).resolve()

        try:
            file_path.relative_to(root)
        except ValueError:
            self._send_not_found()
            return

        if not file_path.is_file():
            self._send_not_found()
            return

        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_not_found()
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_not_found(self) -> None:
        body = b"Not Found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def find_port(start_port: int) -> int:
    port = start_port
    for _ in range(30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((HOST, port)) != 0:
                return port
        port += 1
    raise RuntimeError("Could not find an open local port.")


def main() -> int:
    port = find_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"

    with ReusableTCPServer((HOST, port), ManagerHandler) as httpd:
        print("Comic Manager running.")
        print(f"Open: {url}")
        print("Press Ctrl+C to stop.")

        try:
            webbrowser.open(url)
        except Exception:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
