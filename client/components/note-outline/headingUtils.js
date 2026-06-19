export function slugifyHeading(text, fallback = "heading") {
  const slug = String(text || "")
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[^\p{Letter}\p{Number}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");

  return slug || fallback;
}

function uniqueHeadingId(baseId, seenIds) {
  let id = baseId;
  let suffix = 2;
  while (seenIds.has(id)) {
    id = `${baseId}-${suffix}`;
    suffix += 1;
  }
  seenIds.add(id);
  return id;
}

export function extractHeadings(rootElement, options = {}) {
  if (!rootElement || typeof rootElement.querySelectorAll !== "function") {
    return [];
  }

  const { selector = "h1, h2, h3, h4, h5, h6" } = options;
  const seenIds = new Set();

  return Array.from(rootElement.querySelectorAll(selector))
    .map((element, index) => {
      const level = Number(element.tagName.substring(1));
      const text = element.textContent.trim();
      if (!text || Number.isNaN(level)) return null;

      const existingId = element.id?.trim();
      const baseId = existingId || slugifyHeading(text, `heading-${index + 1}`);
      const id = uniqueHeadingId(baseId, seenIds);

      if (element.id !== id) {
        element.id = id;
      }

      return { id, level, text, element };
    })
    .filter(Boolean);
}
