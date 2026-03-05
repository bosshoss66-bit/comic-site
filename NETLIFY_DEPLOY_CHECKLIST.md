# Netlify Deployment Checklist

Use this checklist each time you publish significant comic updates.

## 1. Local content preparation

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

## 5. Netlify admin setup

- Create a GitHub OAuth App:
  - Homepage URL: your Netlify project URL
  - Callback URL: `https://api.netlify.com/auth/done`
- In Netlify Project configuration -> Access & security -> OAuth, install GitHub provider.
- Paste Client ID and Client Secret from GitHub OAuth App.
- Verify `/admin/` login works with GitHub.

## 6. Post-deploy smoke test

- Open `/` and confirm comic cards render.
- Open at least one reader deep link: `/comic/<slug>/1`.
- Test `Next`, `Previous`, keyboard arrows, swipe, and page jump.
- Verify "Continue Reading" appears after viewing pages.
- Confirm uploads load from `/uploads/...` paths.

## 7. Ongoing content operations

- Admins can add or delete comics in `/admin/` by editing `data/comics.json` through CMS.
- If image optimization is required for newly uploaded images, run optimization scripts from a local clone and push changes.
