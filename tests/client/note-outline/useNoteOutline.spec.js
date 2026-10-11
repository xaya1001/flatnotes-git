import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { defineComponent, nextTick, reactive, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useNoteOutline } from "../../../client/note-outline/composables/useNoteOutline.js";
import { useOutlineStore } from "../../../client/note-outline/stores/outlineStore.js";

describe("useNoteOutline", () => {
  let pinia;
  let mutationInstances;
  let intersectionInstances;
  let rafCallbacks;
  let route;
  let enabled;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    document.body.innerHTML = "";
    mutationInstances = [];
    intersectionInstances = [];
    rafCallbacks = [];
    route = reactive({
      name: "note",
      params: { title: "Example" },
      fullPath: "/note/Example",
    });
    enabled = ref(true);

    vi.useFakeTimers();
    vi.stubGlobal(
      "requestAnimationFrame",
      vi.fn((callback) => {
        rafCallbacks.push(callback);
        return rafCallbacks.length;
      }),
    );
    vi.stubGlobal("cancelAnimationFrame", vi.fn());

    class MockMutationObserver {
      constructor(callback) {
        this.callback = callback;
        this.disconnect = vi.fn();
        this.observe = vi.fn();
        mutationInstances.push(this);
      }
    }

    class MockIntersectionObserver {
      constructor(callback) {
        this.callback = callback;
        this.disconnect = vi.fn();
        this.observe = vi.fn();
        intersectionInstances.push(this);
      }
    }

    vi.stubGlobal("MutationObserver", MockMutationObserver);
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  function mountHarness() {
    const Harness = defineComponent({
      setup() {
        useNoteOutline(route, enabled);
        return () => null;
      },
    });

    return mount(Harness, {
      global: {
        plugins: [pinia],
      },
    });
  }

  async function settleWatcher() {
    await nextTick();
    await nextTick();
    runAnimationFrames();
    await nextTick();
  }

  function runAnimationFrames() {
    const callbacks = rafCallbacks.splice(0);
    callbacks.forEach((callback) => callback());
  }

  it("resets state and does not observe outside note routes", async () => {
    const store = useOutlineStore();
    store.setHeadings([{ id: "intro", text: "Intro", level: 1 }]);
    route.name = "home";
    route.params = {};
    route.fullPath = "/";

    const wrapper = mountHarness();
    await settleWatcher();

    expect(store.headings).toEqual([]);
    expect(mutationInstances).toHaveLength(0);
    expect(intersectionInstances).toHaveLength(0);

    wrapper.unmount();
  });

  it("collects viewer headings, observes them, and refreshes on mutations", async () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h1>Intro</h1>
        <h2>Details</h2>
      </article>
    `;
    const store = useOutlineStore();

    const wrapper = mountHarness();
    await settleWatcher();

    expect(store.headings).toEqual([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);
    expect(mutationInstances[0].observe).toHaveBeenCalledWith(
      document.querySelector(".toast-viewer"),
      { childList: true, subtree: true, characterData: true },
    );
    expect(intersectionInstances.at(-1).observe).toHaveBeenCalledTimes(2);

    const nextHeading = document.createElement("h3");
    nextHeading.textContent = "More";
    document.querySelector(".toast-viewer").appendChild(nextHeading);
    mutationInstances[0].callback();
    runAnimationFrames();

    expect(store.headings.map((heading) => heading.id)).toEqual([
      "intro",
      "details",
      "more",
    ]);

    wrapper.unmount();
  });

  it("updates the active heading from intersection events", async () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h1 id="intro">Intro</h1>
        <h2 id="details">Details</h2>
      </article>
    `;
    const store = useOutlineStore();
    const wrapper = mountHarness();
    await settleWatcher();

    const details = document.getElementById("details");
    details.getBoundingClientRect = () => ({ top: 20 });

    intersectionInstances
      .at(-1)
      .callback([{ target: details, isIntersecting: true }]);

    expect(store.activeHeadingId).toBe("details");

    wrapper.unmount();
  });

  it("clears headings when the viewer disappears and disconnects on unmount", async () => {
    document.body.innerHTML =
      '<article class="toast-viewer"><h1>Intro</h1></article>';
    const store = useOutlineStore();
    const wrapper = mountHarness();
    await settleWatcher();
    expect(store.headings).toHaveLength(1);

    document.querySelector(".toast-viewer").remove();
    vi.advanceTimersByTime(500);

    expect(store.headings).toEqual([]);

    wrapper.unmount();
    expect(mutationInstances[0].disconnect).toHaveBeenCalled();
    expect(intersectionInstances[0].disconnect).toHaveBeenCalled();
  });
});
