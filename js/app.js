import {
  applyImageFallback,
  buildReaderPath,
  getOptimizedCandidate,
  getProgressFor,
  loadComicData,
  readProgress,
  shouldTryOptimized,
} from "/js/data.js";

const comicGrid = document.getElementById("comic-grid");
const continuePanel = document.getElementById("continue-panel");
const continueLink = document.getElementById("continue-link");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderComics(comics, progressMap) {
  if (comics.length === 0) {
    comicGrid.innerHTML = "<p>No comics are published yet.</p>";
    return;
  }

  comicGrid.innerHTML = comics
    .map((comic, index) => {
      const pageTotal = Array.isArray(comic.pages) ? comic.pages.length : 0;
      const progress = getProgressFor(progressMap, comic.slug);
      const continueBadge = progress
        ? `<span class=\"continue-chip\">Continue at p.${progress.page}</span>`
        : "";

      const coverSource = shouldTryOptimized(comic.cover)
        ? getOptimizedCandidate(comic.cover)
        : comic.cover;

      return `
        <a class="comic-card" href="${buildReaderPath(comic.slug, 1)}" style="animation-delay:${Math.min(index * 75, 450)}ms" aria-label="Open ${escapeHtml(comic.title)}">
          <img class="comic-cover" src="${escapeHtml(coverSource)}" data-original="${escapeHtml(comic.cover)}" alt="${escapeHtml(comic.title)} cover" loading="lazy" decoding="async" />
          <div class="comic-meta">
            <h3>${escapeHtml(comic.title)}</h3>
            <p>${escapeHtml(comic.description || "")}</p>
            <div class="meta-row">
              <span>${pageTotal} pages</span>
              ${continueBadge}
            </div>
          </div>
        </a>
      `;
    })
    .join("");

  comicGrid.querySelectorAll("img[data-original]").forEach((image) => {
    const originalSource = image.getAttribute("data-original");
    if (!originalSource || image.src.endsWith(originalSource)) {
      return;
    }
    applyImageFallback(image, originalSource);
  });
}

function renderContinuePanel(comics, progressMap) {
  const entries = Object.entries(progressMap)
    .filter(([, entry]) => entry?.updatedAt)
    .sort((a, b) => new Date(b[1].updatedAt).getTime() - new Date(a[1].updatedAt).getTime());

  if (entries.length === 0) {
    continuePanel.hidden = true;
    return;
  }

  const [slug, progress] = entries[0];
  const comic = comics.find((item) => item.slug === slug);
  if (!comic) {
    continuePanel.hidden = true;
    return;
  }

  const safePage = Math.max(1, Math.min(progress.page, comic.pages.length));
  continueLink.href = buildReaderPath(slug, safePage);
  continueLink.textContent = `${comic.title} - Page ${safePage} of ${comic.pages.length}`;
  continuePanel.hidden = false;
}

async function main() {
  try {
    const { site, comics } = await loadComicData();
    if (site?.title) {
      document.title = site.title;
    }

    const progressMap = readProgress();
    renderContinuePanel(comics, progressMap);
    renderComics(comics, progressMap);
  } catch (error) {
    comicGrid.innerHTML = `<p>Unable to load comics. ${escapeHtml(error.message)}</p>`;
  }
}

main();
