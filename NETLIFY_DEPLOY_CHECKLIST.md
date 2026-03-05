# Netlify Deployment Checklist

Use this checklist each time you publish significant comic updates.

## 1. Local content preparation

- Preferred no-terminal workflow:
  - Double-click `Comic Manager.command` in Finder.
  - Use the GUI to add/replace/delete comics.

- Add/remove comics with the local admin tool:

```bash
python3 ./scripts/comic_admin.py list
python3 ./scripts/comic_admin.py add --slug your-comic --title "Your Comic" --description "Short description" --source-dir "/path/to/images"
python3 ./scripts/comic_admin.py delete --slug old-comic --delete-files
```

- Confirm `data/comics.json` entries are valid (slug/title/cover/pages).
- Ensure page order is correct for every comic.
- Preferred one-command workflow:

```bash
./scripts/release-prep.sh
```

- If you also want to prune originals in the same run:

```bash
./scripts/release-prep.sh --apply-prune
```

## 2. Git update

```bash
git add .
git commit -m "Update comics content"
```

## 3. Push to remote

```bash
./scripts/push-main.sh git@github.com:your-org/your-repo.git
```

## 4. Netlify site configuration

- Connect repository to Netlify.
- Build command: leave empty.
- Publish directory: `.`
- Confirm `netlify.toml` and `_redirects` are included in deploy.

## 5. Optional browser admin

- Browser admin (`/admin`) is optional and can be skipped.
- Recommended production workflow is local script updates + git push.

## 6. Post-deploy smoke test

- Open `/` and confirm comic cards render.
- Open at least one reader deep link: `/comic/<slug>/1`.
- Test `Next`, `Previous`, keyboard arrows, swipe, and page jump.
- Verify "Continue Reading" appears after viewing pages.
- Confirm uploads load from `/uploads/...` paths.

## 7. Ongoing content operations

- Preferred workflow: `Comic Manager.command` GUI.
- Use `python3 ./scripts/comic_admin.py add/delete/list` for all content changes.
- Run `./scripts/release-prep.sh --apply-prune` before commits when adding large new image sets.
