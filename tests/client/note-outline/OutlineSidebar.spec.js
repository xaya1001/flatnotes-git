import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OutlineSidebar from "../../../client/note-outline/components/OutlineSidebar.vue";
import { useOutlineStore } from "../../../client/note-outline/stores/outlineStore.js";

const stubs = {
  CopyNoteButton: { template: '<button data-test="copy-note"></button>' },
  Sidebar: {
    props: ["visible"],
    template: '<section v-if="visible" data-test="sidebar"><slot /></section>',
  },
  SvgIcon: true,
};

describe("OutlineSidebar.vue", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    setActivePinia(createPinia());
    useOutlineStore().showSidebar();
  });

  it("shows an empty message when the note has no headings", () => {
    const wrapper = mount(OutlineSidebar, { global: { stubs } });

    expect(wrapper.find('[data-test="sidebar"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("No headings in this note.");
  });

  it("renders nested headings and scrolls to the selected heading", async () => {
    document.body.innerHTML =
      '<h1 id="intro">Intro</h1><h2 id="details">Details</h2>';
    const target = document.getElementById("details");
    target.scrollIntoView = vi.fn();

    const store = useOutlineStore();
    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);

    const wrapper = mount(OutlineSidebar, { global: { stubs } });
    const buttons = wrapper.findAll("nav button");

    expect(buttons).toHaveLength(2);
    expect(buttons[0].attributes("style")).toContain("padding-left: 12px");
    expect(buttons[1].attributes("style")).toContain("padding-left: 26px");

    await buttons[1].trigger("click");

    expect(store.activeHeadingId).toBe("details");
    expect(target.scrollIntoView).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "start",
    });
  });

  it("pins and closes the sidebar through header controls", async () => {
    const store = useOutlineStore();
    const wrapper = mount(OutlineSidebar, { global: { stubs } });
    const buttons = wrapper.findAll("button");

    await buttons
      .find((button) => button.attributes("title") === "Pin Panel")
      .trigger("click");
    expect(store.isPinned).toBe(true);

    await buttons
      .find((button) => button.attributes("title") === "Close Panel")
      .trigger("click");
    expect(store.isSidebarVisible).toBe(false);
  });
});
