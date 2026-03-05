const DATA_URL = "/data/comics.json";
const PROGRESS_KEY = "comic-progress-v1";

export async function loadComicData() {
  const response = await fetch(DATA_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load comic data: ${response.status}`);
  }

  const payload = await response.json();
  return {
    site: payload.site ?? {},
    comics: Array.isArray(payload.comics) ? payload.comics : [],
  };
}

export function readProgress() {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function saveProgress(slug, page, totalPages) {
  const progress = readProgress();
  progress[slug] = {
    page,
    totalPages,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
}

export function getProgressFor(progressMap, slug) {
  const entry = progressMap[slug];
  if (!entry || typeof entry.page !== "number") {
    return null;
  }
  return entry;
}

export function buildReaderPath(slug, page) {
  const host = window.location.hostname;
  const isLocal =
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "[::1]" ||
    host.endsWith(".local");

  if (isLocal) {
    return `/reader.html?comic=${encodeURIComponent(slug)}&page=${page}`;
  }

  return `/comic/${encodeURIComponent(slug)}/${page}`;
}

export function getOptimizedCandidate(path) {
  if (typeof path !== "string") {
    return "";
  }
  return path.replace(/\.(jpe?g|png)$/i, ".opt.jpg");
}

export function shouldTryOptimized(path) {
  return /\.(jpe?g|png)$/i.test(path);
}

export function applyImageFallback(imageElement, originalSource) {
  if (!imageElement) {
    return;
  }

  imageElement.onerror = () => {
    imageElement.onerror = null;
    imageElement.src = originalSource;
  };
}
