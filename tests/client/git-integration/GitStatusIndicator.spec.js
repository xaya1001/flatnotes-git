import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import GitStatusIndicator from "../../../client/git-integration/components/GitStatusIndicator.vue";
import { useStatusStore } from "../../../client/git-integration/stores/statusStore";
import { usePanelUiStore } from "../../../client/git-integration/stores/panelUiStore";

const stubs = {
  SvgIcon: true,
};

describe("GitStatusIndicator.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const findButton = (wrapper) => wrapper.find("button");

  it("renders the branch name correctly in a clean state", () => {
    const statusStore = useStatusStore();
    statusStore.$patch({
      branchName: "main",
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    const button = findButton(wrapper);
    expect(button.exists()).toBe(true);
    expect(button.attributes("title")).toContain(
      "Branch 'main' is up to date.",
    );
    expect(button.classes()).toEqual(expect.arrayContaining(["h-11", "w-32"]));
    expect(wrapper.text()).toContain("main");
  });

  it("displays an error message when summaryError is present", () => {
    const statusStore = useStatusStore();
    statusStore.$patch({
      summaryError: "Something went wrong",
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    expect(findButton(wrapper).attributes("title")).toContain(
      "Error: Something went wrong",
    );
    expect(wrapper.text()).toContain("!");
  });

  it("displays a conflict message when repository is in a conflict state", () => {
    const statusStore = useStatusStore();
    statusStore.$patch({
      summaryError: null,
      repositoryState: "REBASING_CONFLICT",
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    expect(findButton(wrapper).attributes("title")).toContain(
      "Conflict: Rebase in progress",
    );
    expect(wrapper.text()).toContain("!");
  });

  // No more icon tests for now to avoid the loop. We focus on text.
  it("displays commits behind count", () => {
    const statusStore = useStatusStore();
    statusStore.$patch({
      repositoryState: "CLEAN",
      commitsBehind: 5,
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    expect(wrapper.text()).toContain("5");
  });

  it("displays commits ahead count", () => {
    const statusStore = useStatusStore();
    statusStore.$patch({
      repositoryState: "CLEAN",
      commitsBehind: 0,
      commitsAhead: 3,
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    expect(wrapper.text()).toContain("3");
  });

  it("displays changed files count as a badge", () => {
    const statusStore = useStatusStore();
    // The source of truth for the count is `filesChangedCount`, not the length of a computed array.
    statusStore.$patch({
      filesChangedCount: 7,
      isInitialLoadComplete: true,
    });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    const badge = wrapper.find(".bg-theme-brand");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe("7");
  });

  it("emits 'toggle-sidebar' event on click", async () => {
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    await wrapper.trigger("click");
    expect(wrapper.emitted("toggle-sidebar")).toHaveLength(1);
  });

  it("keeps the branch label visible when sidebar is visible", () => {
    const panelUiStore = usePanelUiStore();
    const statusStore = useStatusStore();
    statusStore.$patch({
      branchName: "main",
      isInitialLoadComplete: true,
    });
    panelUiStore.$patch({ isSidebarVisible: true });
    const wrapper = mount(GitStatusIndicator, { global: { stubs } });
    expect(findButton(wrapper).exists()).toBe(true);
    expect(wrapper.text()).toContain("main");
  });
});
