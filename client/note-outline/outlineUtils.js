const headingSelector = "h1, h2, h3, h4, h5, h6";
const viewerSelector = ".toast-viewer";

export function slugifyHeading(text, fallback = "heading") {
  const slug = text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\p{L}\p{N}_-]+/gu, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return slug || fallback;
}

function makeUniqueId(base, usedIds, element) {
  let id = base;
  let count = 2;
  let existingElement = document.getElementById(id);
  while (usedIds.has(id) || (existingElement && existingElement !== element)) {
    id = `${base}-${count}`;
    count += 1;
    existingElement = document.getElementById(id);
  }
  usedIds.add(id);
  return id;
}

export function collectOutlineHeadings(root = document) {
  const viewer = root.matches?.(viewerSelector)
    ? root
    : root.querySelector?.(viewerSelector);
  if (!viewer) return [];
  const usedIds = new Set();
  return Array.from(viewer.querySelectorAll(headingSelector))
    .map((element, index) => {
      const text = element.textContent.trim();
      if (!text) return null;

      const level = Number(element.tagName.slice(1));
      const existingId = element.id?.trim();
      const baseId = existingId || slugifyHeading(text, `heading-${index + 1}`);
      const id = makeUniqueId(baseId, usedIds, element);

      if (element.id !== id) {
        element.id = id;
      }

      return { id, text, level };
    })
    .filter(Boolean);
}
