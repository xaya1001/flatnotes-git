import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useOutlineStore } from "../../../client/note-outline/stores/outlineStore.js";

describe("outlineStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("activates the first heading when headings are first loaded", () => {
    const store = useOutlineStore();

    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);

    expect(store.activeHeadingId).toBe("intro");
  });

  it("keeps the active heading when it still exists", () => {
    const store = useOutlineStore();
    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);
    store.setActiveHeading("details");

    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
      { id: "more", text: "More", level: 2 },
    ]);

    expect(store.activeHeadingId).toBe("details");
  });

  it("falls back to the first heading when the active heading disappears", () => {
    const store = useOutlineStore();
    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);
    store.setActiveHeading("details");

    store.setHeadings([{ id: "intro", text: "Intro", level: 1 }]);

    expect(store.activeHeadingId).toBe("intro");
  });
});
