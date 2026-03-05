#!/usr/bin/env python3
"""Browser-based local comic manager.

Launch this script (or Comic Manager.command) and it opens a local web UI
for adding/removing comics without terminal commands.
"""

from __future__ import annotations

import cgi
import html
import socket
import socketserver
import subprocess
import tempfile
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import comic_admin

HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "on", "yes"}


def comic_rows(comics: list[dict]) -> str:
    if not comics:
        return "<tr><td colspan='5'>No comics yet.</td></tr>"

    rows = []
    for comic in comics:
        slug = comic.get("slug", "")
        title = comic.get("title", "")
        pages = len(comic.get("pages", []))
        cover = comic.get("cover", "")
        desc = comic.get("description", "")
        rows.append(
            "<tr>"
            f"<td>{esc(slug)}</td>"
            f"<td>{esc(title)}</td>"
            f"<td>{pages}</td>"
            f"<td>{esc(cover)}</td>"
            f"<td>{esc(desc)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def comic_options(comics: list[dict]) -> str:
    options = []
    for comic in comics:
        slug = comic.get("slug", "")
        title = comic.get("title", slug)
        options.append(f"<option value='{esc(slug)}'>{esc(title)} ({esc(slug)})</option>")
    return "\n".join(options)


def render_page(message: str = "", is_error: bool = False) -> bytes:
    comics = comic_admin.get_comics()
    comics = sorted(comics, key=lambda c: (c.get("title", "").lower(), c.get("slug", "").lower()))

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
    :root {{
      --bg: #f6f4ef;
      --card: #ffffff;
      --line: #d9d5cc;
      --ink: #1f1f1f;
      --ink-soft: #555;
      --brand: #e15723;
      --ok: #14532d;
      --ok-bg: #dcfce7;
      --err: #7f1d1d;
      --err-bg: #fee2e2;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    .layout {{ display: grid; gap: 16px; grid-template-columns: 1fr 1fr; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
    }}
    .full {{ grid-column: 1 / -1; }}
    label {{ display: block; margin: 10px 0 4px; font-weight: 600; }}
    input[type="text"], textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      font: inherit;
    }}
    textarea {{ min-height: 66px; resize: vertical; }}
    input[type="file"] {{ width: 100%; margin-top: 4px; }}
    .row {{ display: flex; gap: 10px; align-items: center; margin-top: 10px; }}
    button {{
      border: 1px solid #c84a1e;
      background: var(--brand);
      color: white;
      font: inherit;
      border-radius: 8px;
      padding: 9px 14px;
      cursor: pointer;
    }}
    button.secondary {{ background: #fff; color: #1f1f1f; border-color: var(--line); }}
    .status {{ margin-bottom: 14px; border-radius: 8px; padding: 10px 12px; font-weight: 600; }}
    .status.ok {{ background: var(--ok-bg); color: var(--ok); }}
    .status.error {{ background: var(--err-bg); color: var(--err); }}
    .status.muted {{ background: #eef2f7; color: #334155; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-top: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--ink-soft); font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }}
    .hint {{ color: var(--ink-soft); font-size: 13px; margin-top: 8px; }}
    @media (max-width: 980px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Comic Manager</h1>
  <p class="hint">Local admin panel for adding/removing comics in this repo. After changes, commit + push to deploy on Netlify.</p>
  {status_html}

  <div class="layout">
    <section class="card">
      <h2>Add / Replace Comic</h2>
      <form method="post" action="/add" enctype="multipart/form-data">
        <label for="slug">Slug</label>
        <input id="slug" name="slug" type="text" placeholder="my-comic-episode-one" required />

        <label for="title">Title</label>
        <input id="title" name="title" type="text" placeholder="My Comic: Episode One" required />

        <label for="description">Description</label>
        <textarea id="description" name="description" placeholder="Short description"></textarea>

        <label for="pages">Comic Pages (select all pages in order)</label>
        <input id="pages" name="pages" type="file" accept="image/*" multiple required />

        <label for="cover">Optional Cover Image (defaults to first page)</label>
        <input id="cover" name="cover" type="file" accept="image/*" />

        <div class="row">
          <label><input type="checkbox" name="replace" /> Replace if slug already exists</label>
        </div>

        <div class="row">
          <button type="submit">Add / Replace Comic</button>
          <button class="secondary" type="reset">Clear</button>
        </div>
      </form>
      <p class="hint">Uploads are converted/optimized to <code>.opt.jpg</code> automatically.</p>
    </section>

    <section class="card">
      <h2>Delete Comic</h2>
      <form method="post" action="/delete">
        <label for="delete_slug">Select Comic</label>
        <select id="delete_slug" name="slug" required>
          <option value="">Choose comic...</option>
          {comic_options(comics)}
        </select>

        <div class="row">
          <label><input type="checkbox" name="delete_files" checked /> Also delete image files in uploads/&lt;slug&gt;</label>
        </div>

        <div class="row">
          <button type="submit">Delete Selected Comic</button>
        </div>
      </form>
      <p class="hint">Delete removes from <code>data/comics.json</code> and optionally from <code>uploads/</code>.</p>
    </section>

    <section class="card">
      <h2>Publish to GitHub</h2>
      <form method="post" action="/publish">
        <label for="commit_message">Commit Message</label>
        <input
          id="commit_message"
          name="commit_message"
          type="text"
          placeholder="Update comic library"
          value="Update comic library"
        />

        <div class="row">
          <label><input type="checkbox" name="apply_prune" checked /> Run image prune during preflight</label>
        </div>

        <div class="row">
          <button type="submit">Publish Changes</button>
        </div>
      </form>
      <p class="hint">
        Runs release preflight, stages all changes, creates a commit, and pushes to <code>origin/main</code>.
      </p>
    </section>

    <section class="card full">
      <h2>Current Comics</h2>
      <table>
        <thead>
          <tr><th>Slug</th><th>Title</th><th>Pages</th><th>Cover</th><th>Description</th></tr>
        </thead>
        <tbody>
          {comic_rows(comics)}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""
    return html_doc.encode("utf-8")


class ManagerHandler(BaseHTTPRequestHandler):
    server_version = "ComicManagerHTTP/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/":
            self._send_not_found()
            return

        params = urllib.parse.parse_qs(parsed.query)
        message = params.get("message", [""])[0]
        is_error = parse_bool(params.get("error", ["0"])[0])
        body = render_page(message=message, is_error=is_error)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        return subprocess.run(
            command,
            cwd=SCRIPT_DIR.parent,
            text=True,
            capture_output=True,
            check=False,
        )

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
