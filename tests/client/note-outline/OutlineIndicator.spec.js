import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import OutlineIndicator from "../../../client/note-outline/components/OutlineIndicator.vue";
import { useOutlineStore } from "../../../client/note-outline/stores/outlineStore.js";

const stubs = {
  RightToolRailItem: {
    props: ["active", "iconPath", "title"],
    emits: ["activate"],
    template:
      '<button :title="title" :data-active="active" @click="$emit(\'activate\')"><slot /></button>',
  },
};

describe("OutlineIndicator.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("shows an empty-state tooltip when no headings exist", () => {
    const wrapper = mount(OutlineIndicator, { global: { stubs } });

    expect(wrapper.find("button").attributes("title")).toBe(
      "No headings in this note.",
    );
  });

  it("shows heading count, active state, and emits activation", async () => {
    const store = useOutlineStore();
    store.setHeadings([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);
    store.showSidebar();

    const wrapper = mount(OutlineIndicator, { global: { stubs } });
    const button = wrapper.find("button");

    expect(button.attributes("title")).toBe("Outline: 2 headings.");
    expect(button.attributes("data-active")).toBe("true");
    await button.trigger("click");
    expect(wrapper.emitted("toggle-sidebar")).toHaveLength(1);
  });
});
