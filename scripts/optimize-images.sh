#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPLOADS_DIR="${ROOT_DIR}/uploads"

if [[ ! -d "${UPLOADS_DIR}" ]]; then
  echo "uploads directory not found: ${UPLOADS_DIR}" >&2
  exit 1
fi

if command -v sips >/dev/null 2>&1; then
  TOOL="sips"
elif command -v magick >/dev/null 2>&1; then
  TOOL="magick"
else
  echo "No supported image tool found. Install 'sips' (macOS) or ImageMagick 'magick'." >&2
  exit 1
fi

echo "Using ${TOOL} to optimize images in ${UPLOADS_DIR}"

optimized=0
skipped=0

while IFS= read -r -d '' source; do
  if [[ "${source}" == *.opt.jpg ]]; then
    continue
  fi

  output="${source%.*}.opt.jpg"

  if [[ -f "${output}" && "${output}" -nt "${source}" ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "${TOOL}" == "sips" ]]; then
    # Resize longest edge to 1900px and re-encode to JPEG for lighter network payload.
    sips --resampleHeightWidthMax 1900 --setProperty format jpeg --setProperty formatOptions 72 "${source}" --out "${output}" >/dev/null 2>&1
  else
    magick "${source}" -auto-orient -resize '1900x1900>' -quality 72 "${output}"
  fi

  optimized=$((optimized + 1))
  echo "optimized: ${output#${ROOT_DIR}/}"
done < <(find "${UPLOADS_DIR}" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print0)

echo "Done. optimized=${optimized}, skipped=${skipped}"
