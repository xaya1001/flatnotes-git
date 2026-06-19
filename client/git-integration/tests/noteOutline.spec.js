import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";

import NoteOutline from "../../components/note-outline/NoteOutline.vue";
import {
  extractHeadings,
  slugifyHeading,
} from "../../components/note-outline/headingUtils.js";

const stubs = {
  SvgIcon: true,
};

const headings = [
  {
    id: "intro",
    level: 1,
    text: "Intro",
    element: document.createElement("h1"),
  },
  {
    id: "details",
    level: 2,
    text: "Details",
    element: document.createElement("h2"),
  },
];

describe("note outline heading utilities", () => {
  it("keeps unicode heading text when generating slugs", () => {
    expect(slugifyHeading("项目 背景")).toBe("项目-背景");
  });

  it("falls back when a heading has no slug content", () => {
    expect(slugifyHeading("!!!", "heading-1")).toBe("heading-1");
  });

  it("extracts headings, fixes missing ids, and de-duplicates ids", () => {
    const root = document.createElement("div");
    root.innerHTML = `
      <h1>项目背景</h1>
      <p># Not a heading</p>
      <h2 id="details">Details</h2>
      <h2 id="details">Details Again</h2>
    `;

    const result = extractHeadings(root);

    expect(result.map((heading) => heading.id)).toEqual([
      "项目背景",
      "details",
      "details-2",
    ]);
    expect(root.querySelectorAll("h2")[1].id).toBe("details-2");
  });
});

describe("NoteOutline.vue", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("innerWidth", 1600);
  });

  it("renders heading links and emits navigation when clicked", async () => {
    const wrapper = mount(NoteOutline, {
      props: { headings, activeId: "details" },
      global: { stubs },
    });

    expect(wrapper.text()).toContain("On this note");
    expect(wrapper.text()).toContain("Intro");
    expect(wrapper.text()).toContain("Details");

    await wrapper.findAll("nav button")[1].trigger("click");
    expect(wrapper.emitted("navigate")[0][0]).toMatchObject({
      id: "details",
      text: "Details",
    });
  });

  it("hides itself when there are not enough headings", () => {
    const wrapper = mount(NoteOutline, {
      props: { headings: headings.slice(0, 1), minHeadings: 2 },
      global: { stubs },
    });

    expect(wrapper.find("aside").exists()).toBe(false);
    expect(wrapper.find("button[aria-label='Expand outline']").exists()).toBe(
      false,
    );
  });

  it("collapses by default on narrow screens", () => {
    vi.stubGlobal("innerWidth", 900);

    const wrapper = mount(NoteOutline, {
      props: { headings },
      global: { stubs },
    });

    expect(wrapper.find("button[aria-label='Expand outline']").exists()).toBe(
      true,
    );
  });
});
