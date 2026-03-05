# Netlify Deployment Checklist

Use this checklist each time you publish significant comic updates.

## 1. Local content preparation

- Confirm `data/comics.json` entries are valid (slug/title/cover/pages).
- Ensure page order is correct for every comic.
- Generate optimized image variants:

```bash
./scripts/optimize-images.sh
```

- Optional, to reduce repo size by removing originals that have optimized copies:

```bash
./scripts/prune-original-images.sh
./scripts/prune-original-images.sh --apply
```

## 2. Git update

```bash
git add .
git commit -m "Update comics content"
```

## 3. Push to remote

```bash
git remote -v
# if needed: git remote add origin <your-repo-url>
git push -u origin main
```

## 4. Netlify site configuration

- Connect repository to Netlify.
- Build command: leave empty.
- Publish directory: `.`
- Confirm `netlify.toml` and `_redirects` are included in deploy.

## 5. Netlify admin setup

- Enable Identity in Netlify.
- Enable Git Gateway.
- Invite admin users.
- Verify `/admin/` login works.

## 6. Post-deploy smoke test

- Open `/` and confirm comic cards render.
- Open at least one reader deep link: `/comic/<slug>/1`.
- Test `Next`, `Previous`, keyboard arrows, swipe, and page jump.
- Verify "Continue Reading" appears after viewing pages.
- Confirm uploads load from `/uploads/...` paths.

## 7. Ongoing content operations

- Admins can add or delete comics in `/admin/` by editing `data/comics.json` through CMS.
- If image optimization is required for newly uploaded images, run optimization scripts from a local clone and push changes.
