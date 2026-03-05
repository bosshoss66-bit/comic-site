#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPLOADS_DIR="${ROOT_DIR}/uploads"
APPLY=false

if [[ "${1-}" == "--apply" ]]; then
  APPLY=true
elif [[ -n "${1-}" ]]; then
  echo "Usage: $0 [--apply]" >&2
  exit 1
fi

if [[ ! -d "${UPLOADS_DIR}" ]]; then
  echo "uploads directory not found: ${UPLOADS_DIR}" >&2
  exit 1
fi

would_remove=0
skipped=0
freed_bytes=0

while IFS= read -r -d '' source; do
  if [[ "${source}" == *.opt.jpg ]]; then
    continue
  fi

  optimized="${source%.*}.opt.jpg"

  if [[ ! -f "${optimized}" ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  size=$(stat -f '%z' "${source}")
  would_remove=$((would_remove + 1))
  freed_bytes=$((freed_bytes + size))

  rel="${source#${ROOT_DIR}/}"
  if [[ "${APPLY}" == true ]]; then
    rm -f "${source}"
    echo "removed: ${rel}"
  else
    echo "would remove: ${rel}"
  fi
done < <(find "${UPLOADS_DIR}" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print0)

freed_mb=$(awk -v b="${freed_bytes}" 'BEGIN { printf "%.2f", b / 1024 / 1024 }')

if [[ "${APPLY}" == true ]]; then
  echo "Done. removed=${would_remove}, skipped=${skipped}, freed_mb=${freed_mb}"
else
  echo "Dry run complete. removable=${would_remove}, skipped=${skipped}, potential_freed_mb=${freed_mb}"
  echo "Re-run with --apply to delete originals that have .opt.jpg replacements."
fi
