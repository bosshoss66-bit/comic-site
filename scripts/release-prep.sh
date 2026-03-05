#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY_PRUNE=false

if [[ "${1-}" == "--apply-prune" ]]; then
  APPLY_PRUNE=true
elif [[ -n "${1-}" ]]; then
  echo "Usage: $0 [--apply-prune]" >&2
  exit 1
fi

cd "${ROOT_DIR}"

echo "==> Optimizing uploaded images"
./scripts/optimize-images.sh

echo "==> Prune originals check"
if [[ "${APPLY_PRUNE}" == true ]]; then
  ./scripts/prune-original-images.sh --apply
else
  ./scripts/prune-original-images.sh
fi

echo "==> Validating content files"
if command -v jq >/dev/null 2>&1; then
  jq . data/comics.json >/dev/null
  echo "comics.json valid"
else
  echo "warning: jq not found; skipping JSON validation"
fi

if command -v ruby >/dev/null 2>&1; then
  ruby -e 'require "yaml"; YAML.load_file("admin/config.yml")'
  echo "admin/config.yml valid"
else
  echo "warning: ruby not found; skipping YAML validation"
fi

echo "==> Git status summary"
git status --short

echo "==> Latest commit"
git log --oneline -n 1

echo "Release prep complete."
