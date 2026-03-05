# Comic Site (Netlify)

Static comic library and reader designed for Netlify hosting.

## What is implemented

- Homepage comic grid with thumbnails, title, description, and page count.
- Deep links per page (`/comic/<slug>/<page>`).
- Reader with Previous/Next, page indicator, page jump dropdown.
- Keyboard navigation (`Left`/`Right`) and swipe navigation on mobile.
- Local reading progress + homepage "Continue Reading" panel.
- Reader preloads adjacent pages for smoother transitions.
- Zoom controls for easier reading on smaller screens.
- Accessible controls, focus states, and responsive layout.
- Local admin CLI for adding/removing comics and uploading images (no browser auth required).
- Local browser-based Comic Manager app for adding/removing comics (no terminal commands required).

## Project structure

- `index.html`: homepage grid.
- `reader.html`: comic reader page.
- `styles.css`: shared styling.
- `js/data.js`: data loading + progress storage.
- `js/app.js`: homepage rendering.
- `js/reader.js`: reader behavior.
- `data/comics.json`: comic catalog (admin editable).
- `uploads/`: comic images.
- `Comic Manager.command`: double-click launcher for the local Comic Manager app.
- `scripts/comic_admin.py`: primary add/delete/list content manager.
- `scripts/comic_manager_web.py`: local browser-based manager for add/delete comic operations.
- `scripts/optimize-images.sh`: generates optimized `*.opt.jpg` files.
- `scripts/prune-original-images.sh`: safely deletes originals once optimized replacements exist.
- `scripts/release-prep.sh`: one-command pre-deploy check (optimize + prune check + validation + git status).
- `scripts/push-main.sh`: configures `origin` (optional URL arg) and pushes `main`.

## Content workflow (recommended, no terminal required)

1. In Finder, open this folder and double-click:
   - `Comic Manager.command`
2. A local browser page opens automatically.
3. In the app:
   - Use **Add / Replace Comic** to load new comic pages from an image folder.
   - Use **Delete Selected Comic** to remove old comics (optionally remove files too).
4. After content edits, publish changes to GitHub:
   - Use your preferred Git app, or ask me to run the push commands for you.

## CLI workflow (optional)

This is the advanced/manual path and also does not depend on Netlify/GitHub popup auth.

1. Add a comic from a folder of page images:

```bash
python3 ./scripts/comic_admin.py add \
  --slug your-comic-slug \
  --title "Your Comic Title" \
  --description "Short description" \
  --source-dir "/absolute/path/to/page-images"
```

2. List comics:

```bash
python3 ./scripts/comic_admin.py list
```

3. Delete a comic entry (keep files):

```bash
python3 ./scripts/comic_admin.py delete --slug your-comic-slug
```

4. Delete a comic entry and uploaded files:

```bash
python3 ./scripts/comic_admin.py delete --slug your-comic-slug --delete-files
```

5. Prepare and publish updates:

```bash
./scripts/release-prep.sh --apply-prune
git add .
git commit -m "Update comic library"
git push
```

## Image optimization workflow

Run this before committing large new comic uploads:

```bash
./scripts/optimize-images.sh
```

Optional cleanup after optimization:

```bash
./scripts/prune-original-images.sh
./scripts/prune-original-images.sh --apply
```

One-command pre-release check:

```bash
./scripts/release-prep.sh
```

Apply pruning inside the same command:

```bash
./scripts/release-prep.sh --apply-prune
```

What it does:

- Scans `uploads/` for `jpg/jpeg/png`.
- Creates `*.opt.jpg` files (resized + compressed) beside originals.
- The site automatically prefers `*.opt.jpg` and falls back to originals if missing.
- The prune script removes originals only when matching `*.opt.jpg` files exist.

## Local preview

From this directory, preferred:

```bash
netlify dev
```

Then open [http://localhost:8888](http://localhost:8888).

Fallback if Netlify CLI is not installed:

```bash
python3 -m http.server 8888
```

Open [http://localhost:8888](http://localhost:8888). The app auto-falls back to query URLs for local servers.

## Deploy to Netlify

1. Connect this `comic-site` folder as a new Netlify site.
2. Build command: none.
3. Publish directory: `.`
4. Deploy.

Netlify will apply routing using `netlify.toml`.

Deployment steps are also listed in [NETLIFY_DEPLOY_CHECKLIST.md](./NETLIFY_DEPLOY_CHECKLIST.md).

## Git setup

If this folder is not yet a Git repo:

```bash
git init -b main
git add .
git commit -m "Initial comic site scaffold"
```

Push to a remote:

```bash
./scripts/push-main.sh git@github.com:your-org/your-repo.git
```

If `origin` already exists:

```bash
./scripts/push-main.sh
```
