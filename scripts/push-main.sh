#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  echo "Usage: $0 [remote-url]"
  echo "  remote-url optional: if provided, sets origin to this URL first."
  exit 0
fi

if [[ -n "${1-}" ]]; then
  remote_url="$1"
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "${remote_url}"
    echo "Updated origin -> ${remote_url}"
  else
    git remote add origin "${remote_url}"
    echo "Added origin -> ${remote_url}"
  fi
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "No origin remote configured. Pass the repo URL as argument." >&2
  echo "Example: $0 git@github.com:your-org/comic-site.git" >&2
  exit 1
fi

git push -u origin main
