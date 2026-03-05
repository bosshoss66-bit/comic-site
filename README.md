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
- `/admin` editor for adding/removing comics and uploading images.

## Project structure

- `index.html`: homepage grid.
- `reader.html`: comic reader page.
- `styles.css`: shared styling.
- `js/data.js`: data loading + progress storage.
- `js/app.js`: homepage rendering.
- `js/reader.js`: reader behavior.
- `data/comics.json`: comic catalog (admin editable).
- `admin/`: Decap CMS setup.
- `uploads/`: comic images.
- `scripts/optimize-images.sh`: generates optimized `*.opt.jpg` files.

## Admin workflow (upload/delete comics)

1. In Netlify site settings, enable **Identity**.
2. Under Identity settings, enable **Git Gateway**.
3. Invite your admin users under Identity.
4. Open `/admin/` on your deployed site and log in.
5. Open **Comics Data**.
6. Add a comic entry, upload a cover image, and upload page images in order.
7. Remove a comic entry to delete it from the site.
8. Save/publish to commit the content changes.

Note: deleting a comic entry removes it from the catalog immediately, but uploaded image files may still remain in `uploads/` unless manually deleted.

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
