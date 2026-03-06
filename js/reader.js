import {
  applyImageFallback,
  buildReaderPath,
  getOptimizedCandidate,
  loadComicData,
  saveProgress,
  shouldTryOptimized,
} from "/js/data.js";

const titleEl = document.getElementById("comic-title");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const pageIndicator = document.getElementById("page-indicator");
const pageJump = document.getElementById("page-jump");
const pageImage = document.getElementById("page-image");
const readerStage = document.getElementById("reader-stage");
const zoomLabel = document.getElementById("zoom-label");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const zoomResetBtn = document.getElementById("zoom-reset");
const readerWrap = document.getElementById("reader-wrap");

const DEFAULT_ZOOM = 1;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2.5;
const ZOOM_STEP = 0.25;

let activeComic = null;
let activePage = 1;
let zoomLevel = DEFAULT_ZOOM;
let basePageWidth = 0;

function parseReaderLocation() {
  const segments = window.location.pathname.split("/").filter(Boolean);
  if (segments[0] === "comic") {
    return {
      slug: decodeURIComponent(segments[1] || ""),
      page: Number.parseInt(segments[2] || "1", 10) || 1,
    };
  }

  const params = new URLSearchParams(window.location.search);
  return {
    slug: params.get("comic") || "",
    page: Number.parseInt(params.get("page") || "1", 10) || 1,
  };
}

function clampPage(page) {
  if (!activeComic) {
    return 1;
  }
  return Math.max(1, Math.min(page, activeComic.pages.length));
}

function preloadAdjacentPages() {
  const prev = activeComic.pages[activePage - 2];
  const next = activeComic.pages[activePage];
  [prev, next]
    .filter(Boolean)
    .forEach((source) => {
      const image = new Image();
      if (shouldTryOptimized(source)) {
        const optimized = getOptimizedCandidate(source);
        image.onerror = () => {
          image.onerror = null;
          image.src = source;
        };
        image.src = optimized;
        return;
      }
      image.src = source;
    });
}

function clampZoom(level) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, level));
}

function setZoomLevel(level) {
  zoomLevel = clampZoom(level);
  applyZoom();
}

function measureBasePageWidth() {
  if (!pageImage.complete || !pageImage.naturalWidth) {
    return;
  }

  const previousWidth = pageImage.style.width;
  const previousMaxWidth = pageImage.style.maxWidth;

  pageImage.style.width = "100%";
  pageImage.style.maxWidth = "1200px";
  basePageWidth = pageImage.getBoundingClientRect().width;

  pageImage.style.width = previousWidth;
  pageImage.style.maxWidth = previousMaxWidth;
}

function applyZoom() {
  if (basePageWidth > 0) {
    pageImage.style.width = `${Math.round(basePageWidth * zoomLevel)}px`;
    pageImage.style.maxWidth = "none";
  } else {
    pageImage.style.width = `${Math.round(zoomLevel * 100)}%`;
    pageImage.style.maxWidth = zoomLevel > DEFAULT_ZOOM ? "none" : "1200px";
  }
  zoomLabel.textContent = `${Math.round(zoomLevel * 100)}%`;
  zoomOutBtn.disabled = zoomLevel <= MIN_ZOOM;
  zoomInBtn.disabled = zoomLevel >= MAX_ZOOM;
}

function setPage(page, updateHistory = true) {
  if (!activeComic) {
    return;
  }

  activePage = clampPage(page);
  const originalSource = activeComic.pages[activePage - 1];
  const imageSource = shouldTryOptimized(originalSource)
    ? getOptimizedCandidate(originalSource)
    : originalSource;

  basePageWidth = 0;
  pageImage.src = imageSource;
  applyImageFallback(pageImage, originalSource);
  pageImage.alt = `${activeComic.title} page ${activePage}`;
  pageIndicator.textContent = `Page ${activePage} of ${activeComic.pages.length}`;
  prevBtn.disabled = activePage <= 1;
  nextBtn.disabled = activePage >= activeComic.pages.length;
  pageJump.value = String(activePage);

  if (updateHistory) {
    const path = buildReaderPath(activeComic.slug, activePage);
    window.history.replaceState({ slug: activeComic.slug, page: activePage }, "", path);
  }

  saveProgress(activeComic.slug, activePage, activeComic.pages.length);
  preloadAdjacentPages();
}

function goToPrevious() {
  if (activePage > 1) {
    setPage(activePage - 1);
  }
}

function goToNext() {
  if (activeComic && activePage < activeComic.pages.length) {
    setPage(activePage + 1);
  }
}

function attachEvents() {
  prevBtn.addEventListener("click", goToPrevious);
  nextBtn.addEventListener("click", goToNext);
  pageJump.addEventListener("change", () => {
    const value = Number.parseInt(pageJump.value, 10) || 1;
    setPage(value);
  });

  zoomOutBtn.addEventListener("click", () => {
    setZoomLevel(zoomLevel - ZOOM_STEP);
  });

  zoomInBtn.addEventListener("click", () => {
    setZoomLevel(zoomLevel + ZOOM_STEP);
  });

  zoomResetBtn.addEventListener("click", () => {
    setZoomLevel(DEFAULT_ZOOM);
    readerStage.scrollTo({ left: 0, top: 0, behavior: "smooth" });
  });

  window.addEventListener("keydown", (event) => {
    const targetTag = event.target?.tagName;
    if (targetTag === "INPUT" || targetTag === "SELECT" || targetTag === "TEXTAREA") {
      return;
    }

    if (event.key === "ArrowLeft") {
      goToPrevious();
    }
    if (event.key === "ArrowRight") {
      goToNext();
    }
  });

  pageImage.addEventListener("load", () => {
    requestAnimationFrame(() => {
      measureBasePageWidth();
      applyZoom();
    });
  });

  window.addEventListener("resize", () => {
    if (zoomLevel !== DEFAULT_ZOOM) {
      return;
    }

    requestAnimationFrame(() => {
      measureBasePageWidth();
      applyZoom();
    });
  });
}

function renderPageOptions(totalPages) {
  pageJump.innerHTML = "";
  for (let i = 1; i <= totalPages; i += 1) {
    const option = document.createElement("option");
    option.value = String(i);
    option.textContent = `Page ${i}`;
    pageJump.appendChild(option);
  }
}

function renderError(message) {
  readerWrap.innerHTML = `
    <div class="error-box" role="alert">
      <p>${message}</p>
      <p><a href="/">Return to comic library</a></p>
    </div>
  `;
}

async function main() {
  try {
    const { slug, page } = parseReaderLocation();
    if (!slug) {
      renderError("No comic was selected.");
      return;
    }

    const { site, comics } = await loadComicData();
    const comic = comics.find((item) => item.slug === slug);

    if (!comic) {
      renderError("Comic not found. It may have been removed.");
      return;
    }

    if (!Array.isArray(comic.pages) || comic.pages.length === 0) {
      renderError("This comic has no pages configured yet.");
      return;
    }

    activeComic = comic;
    titleEl.textContent = comic.title;
    document.title = `${comic.title} | Comic Reader`;

    renderPageOptions(comic.pages.length);
    attachEvents();
    applyZoom();
    setPage(page, true);
  } catch {
    renderError("The reader could not load comic data.");
  }
}

main();
