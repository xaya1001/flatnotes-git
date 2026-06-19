import { nextTick, onUnmounted, unref, watch } from "vue";

import { collectOutlineHeadings } from "../outlineUtils.js";
import { useOutlineStore } from "../stores/outlineStore.js";

const VIEWER_SELECTOR = ".toast-viewer";
const VIEWER_CHECK_INTERVAL_MS = 500;

export function useNoteOutline(route, enabled = true) {
  const outlineStore = useOutlineStore();
  let mutationObserver = null;
  let intersectionObserver = null;
  let refreshFrame = null;
  let viewerCheckTimer = null;
  let observedViewer = null;
  const visibleHeadingIds = new Set();

  function disconnectObservers() {
    if (mutationObserver) {
      mutationObserver.disconnect();
      mutationObserver = null;
    }
    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }
    if (refreshFrame) {
      cancelAnimationFrame(refreshFrame);
      refreshFrame = null;
    }
    if (viewerCheckTimer) {
      clearTimeout(viewerCheckTimer);
      viewerCheckTimer = null;
    }
    observedViewer = null;
    visibleHeadingIds.clear();
  }

  function updateActiveHeadingFromVisibleHeadings() {
    const visibleHeading = outlineStore.headings
      .map((heading) => ({
        id: heading.id,
        element: document.getElementById(heading.id),
      }))
      .filter(({ id, element }) => element && visibleHeadingIds.has(id))
      .sort(
        (a, b) =>
          a.element.getBoundingClientRect().top -
          b.element.getBoundingClientRect().top,
      )[0];

    if (visibleHeading?.id) {
      outlineStore.setActiveHeading(visibleHeading.id);
    }
  }

  function observeActiveHeading(headings, viewer) {
    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }
    visibleHeadingIds.clear();
    if (!("IntersectionObserver" in window)) return;

    intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const id = entry.target.id;
          if (!id) return;
          if (entry.isIntersecting) {
            visibleHeadingIds.add(id);
            return;
          }
          visibleHeadingIds.delete(id);
        });
        updateActiveHeadingFromVisibleHeadings();
      },
      {
        root: null,
        rootMargin: "-20% 0px -70% 0px",
        threshold: 0,
      },
    );

    headings.forEach((heading) => {
      const element = document.getElementById(heading.id);
      if (element && viewer.contains(element)) {
        intersectionObserver.observe(element);
      }
    });
  }

  function refreshOutline(viewer = observedViewer) {
    refreshFrame = null;
    if (!viewer || !document.contains(viewer)) {
      outlineStore.setHeadings([]);
      visibleHeadingIds.clear();
      return;
    }

    const headings = collectOutlineHeadings(viewer);
    outlineStore.setHeadings(headings);
    observeActiveHeading(headings, viewer);
  }

  function scheduleRefresh(viewer = observedViewer) {
    if (refreshFrame) return;
    refreshFrame = requestAnimationFrame(() => refreshOutline(viewer));
  }

  function syncViewerObserver() {
    const viewer = document.querySelector(VIEWER_SELECTOR);
    if (viewer === observedViewer) return;

    if (mutationObserver) {
      mutationObserver.disconnect();
      mutationObserver = null;
    }
    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }
    if (refreshFrame) {
      cancelAnimationFrame(refreshFrame);
      refreshFrame = null;
    }
    visibleHeadingIds.clear();
    observedViewer = viewer;

    if (!viewer) {
      outlineStore.setHeadings([]);
      return;
    }

    scheduleRefresh(viewer);
    mutationObserver = new MutationObserver(() => scheduleRefresh(viewer));
    mutationObserver.observe(viewer, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  function scheduleViewerCheck() {
    if (viewerCheckTimer) return;
    viewerCheckTimer = setTimeout(() => {
      viewerCheckTimer = null;
      if (!unref(enabled) || route.name !== "note" || !route.params.title) {
        return;
      }
      syncViewerObserver();
      scheduleViewerCheck();
    }, VIEWER_CHECK_INTERVAL_MS);
  }

  async function startForCurrentRoute() {
    disconnectObservers();
    if (!unref(enabled) || route.name !== "note" || !route.params.title) {
      outlineStore.reset();
      return;
    }

    await nextTick();
    syncViewerObserver();
    scheduleViewerCheck();
  }

  watch([() => route.fullPath, () => unref(enabled)], startForCurrentRoute, {
    immediate: true,
  });

  onUnmounted(() => {
    disconnectObservers();
  });
}
