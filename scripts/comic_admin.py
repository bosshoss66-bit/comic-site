#!/usr/bin/env python3
"""Local comic management tool.

This avoids browser admin auth issues by editing data/comics.json and uploads/ directly.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "comics.json"
UPLOADS_DIR = ROOT / "uploads"
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def natural_key(name: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def new_content_version() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def save_data(data: dict) -> None:
    site = data.setdefault("site", {})
    site["contentVersion"] = new_content_version()
    with DATA_PATH.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def list_images(source_dir: Path) -> list[Path]:
    images = [
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS and not path.name.startswith(".")
    ]
    images.sort(key=lambda p: natural_key(p.name))
    return images


def run_cmd(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def convert_image(source: Path, destination: Path) -> None:
    if shutil.which("sips"):
        run_cmd(
            [
                "sips",
                "--resampleHeightWidthMax",
                "1900",
                "--setProperty",
                "format",
                "jpeg",
                "--setProperty",
                "formatOptions",
                "72",
                str(source),
                "--out",
                str(destination),
            ]
        )
        return

    if shutil.which("magick"):
        run_cmd(
            [
                "magick",
                str(source),
                "-auto-orient",
                "-resize",
                "1900x1900>",
                "-quality",
                "72",
                str(destination),
            ]
        )
        return

    raise RuntimeError("No image converter found. Install 'sips' (macOS) or 'magick' (ImageMagick).")


def find_comic_index(comics: list[dict], slug: str) -> int:
    for idx, comic in enumerate(comics):
        if comic.get("slug") == slug:
            return idx
    return -1


def get_comics() -> list[dict]:
    data = load_data()
    comics = data.get("comics", [])
    return comics


def add_comic(
    *,
    slug: str,
    title: str,
    description: str,
    source_dir: Path,
    cover: Path | None = None,
    replace: bool = False,
) -> dict:
    slug = slug.strip().lower()
    title = title.strip()
    description = description.strip()
    source_dir = source_dir.expanduser().resolve()

    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError("Slug must use lowercase letters, numbers, and dashes only.")
    if not title:
        raise ValueError("Title is required.")
    if not source_dir.is_dir():
        raise ValueError(f"Source folder not found: {source_dir}")

    images = list_images(source_dir)
    if not images:
        raise ValueError("No image files found in source folder.")

    data = load_data()
    comics = data.setdefault("comics", [])
    existing_index = find_comic_index(comics, slug)
    target_dir = UPLOADS_DIR / slug

    if existing_index >= 0:
        if not replace:
            raise ValueError(f"Slug '{slug}' already exists. Enable replace to overwrite.")
        comics.pop(existing_index)
        if target_dir.exists():
            shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    cover_source = cover.expanduser().resolve() if cover else images[0]
    if not cover_source.exists():
        raise ValueError(f"Cover image not found: {cover_source}")

    cover_out = target_dir / "cover.opt.jpg"
    convert_image(cover_source, cover_out)

    page_paths: list[str] = []
    for page_number, image in enumerate(images, start=1):
        filename = f"{page_number:03d}.opt.jpg"
        output = target_dir / filename
        convert_image(image, output)
        page_paths.append(f"/uploads/{slug}/{filename}")

    comic = {
        "slug": slug,
        "title": title,
        "description": description,
        "version": new_content_version(),
        "cover": f"/uploads/{slug}/cover.opt.jpg",
        "pages": page_paths,
    }

    comics.append(comic)
    save_data(data)
    return comic


def delete_comic(*, slug: str, delete_files: bool = False) -> dict:
    slug = slug.strip().lower()
    data = load_data()
    comics = data.get("comics", [])
    idx = find_comic_index(comics, slug)
    if idx < 0:
        raise ValueError(f"Comic slug not found: {slug}")

    removed = comics.pop(idx)
    save_data(data)

    if delete_files:
        target_dir = UPLOADS_DIR / slug
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)

    return removed


def cmd_list(_: argparse.Namespace) -> int:
    comics = get_comics()
    if not comics:
        print("No comics found.")
        return 0

    for comic in comics:
        pages = comic.get("pages", [])
        print(f"{comic.get('slug')} | {comic.get('title')} | pages={len(pages)}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    comic = add_comic(
        slug=args.slug,
        title=args.title,
        description=args.description,
        source_dir=Path(args.source_dir),
        cover=Path(args.cover) if args.cover else None,
        replace=args.replace,
    )
    print(
        f"Added comic '{comic.get('title')}' ({comic.get('slug')}) with {len(comic.get('pages', []))} pages."
    )
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    removed = delete_comic(slug=args.slug, delete_files=args.delete_files)
    print(f"Deleted comic '{removed.get('title')}' ({removed.get('slug')}).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage comics in this static site.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List current comics")
    list_parser.set_defaults(func=cmd_list)

    add_parser = sub.add_parser("add", help="Add a comic from a local image folder")
    add_parser.add_argument("--slug", required=True, help="comic slug (lowercase-and-dashes)")
    add_parser.add_argument("--title", required=True, help="comic title")
    add_parser.add_argument("--description", default="", help="short description")
    add_parser.add_argument("--source-dir", required=True, help="folder containing page images")
    add_parser.add_argument("--cover", help="optional cover image path (defaults to first page)")
    add_parser.add_argument("--replace", action="store_true", help="replace existing comic with same slug")
    add_parser.set_defaults(func=cmd_add)

    delete_parser = sub.add_parser("delete", help="Delete a comic from data/comics.json")
    delete_parser.add_argument("--slug", required=True, help="comic slug to delete")
    delete_parser.add_argument(
        "--delete-files",
        action="store_true",
        help="also delete uploads/<slug> image files",
    )
    delete_parser.set_defaults(func=cmd_delete)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as error:  # pragma: no cover
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
