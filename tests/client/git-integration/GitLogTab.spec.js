import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";

// --- MOCKS ---
vi.mock("../../../client/git-integration/gitApi.js", () => ({
  getGitActivityLog: vi.fn().mockResolvedValue([]),
  clearGitActivityLog: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useRouter: () => ({ push: vi.fn() }) };
});
// --- END MOCKS ---

import GitLogTab from "../../../client/git-integration/components/tabs/GitLogTab.vue";
import { useLogStore } from "../../../client/git-integration/stores/logStore";
import { usePanelUiStore } from "../../../client/git-integration/stores/panelUiStore";

const stubs = { SvgIcon: true, LogDetail: true };

const mockLogs = [
  {
    id: "1",
    timestamp: new Date().toISOString(),
    level: "success",
    message: "Sync successful",
  },
  {
    id: "2",
    timestamp: new Date().toISOString(),
    level: "error",
    message: "Push failed",
  },
  {
    id: "3",
    timestamp: new Date().toISOString(),
    level: "info",
    message: "Pull started",
  },
];

describe("GitLogTab.vue", () => {
  let logStore;
  let panelUiStore;
  let wrapper;

  const mountComponent = () => {
    const pinia = createPinia();
    wrapper = mount(GitLogTab, {
      global: { plugins: [pinia, PrimeVue, ToastService], stubs },
    });
    logStore = useLogStore();
    panelUiStore = usePanelUiStore();
  };

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("Rendering and Filtering", () => {
    it("shows a message when there are no logs", async () => {
      mountComponent();
      logStore.logs = [];
      await wrapper.vm.$nextTick();
      expect(wrapper.text()).toContain("No logs to display");
    });

    it("renders all logs by default", async () => {
      mountComponent();
      logStore.logs = mockLogs;
      await wrapper.vm.$nextTick();
      const renderedLogs = wrapper.findAll(".border-b.p-2");
      expect(renderedLogs.length).toBe(3);
    });

    it("filters logs when a filter button is clicked", async () => {
      mountComponent();
      logStore.logs = mockLogs;
      await wrapper.vm.$nextTick();

      const successFilterButton = wrapper
        .findAll("button.rounded-full")
        .find((btn) => btn.text() === "Success");
      await successFilterButton.trigger("click");

      const renderedLogs = wrapper.findAll(".border-b.p-2");
      expect(renderedLogs.length).toBe(1);
      expect(wrapper.text()).toContain("Sync successful");
      expect(wrapper.text()).not.toContain("Push failed");
    });
  });

  describe("Actions", () => {
    it("calls confirmation and clears logs on 'Clear Log' click", async () => {
      mountComponent();
      const confirmSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(true);
      const clearSpy = vi.spyOn(logStore, "clearAllLogs");
      logStore.logs = mockLogs;
      await wrapper.vm.$nextTick();

      await wrapper
        .find('button[title="Clear all log entries"]')
        .trigger("click");

      expect(confirmSpy).toHaveBeenCalled();
      expect(clearSpy).toHaveBeenCalled();
    });
  });

  describe("Log Condensing", () => {
    it("condenses consecutive successful auto-fetch logs", async () => {
      mountComponent();
      logStore.logs = [
        {
          id: "auto-fetch-task",
          timestamp: new Date().toISOString(),
          level: "success",
          message: "Scheduled fetch successful",
        },
        {
          id: "auto-fetch-task",
          timestamp: new Date().toISOString(),
          level: "success",
          message: "Scheduled fetch successful",
        },
        {
          id: "some-other-id",
          timestamp: new Date().toISOString(),
          level: "error",
          message: "Something else failed",
        },
      ];
      await wrapper.vm.$nextTick();

      const renderedLogs = wrapper.findAll(".border-b.p-2");
      expect(renderedLogs.length).toBe(2);
      expect(wrapper.text()).toContain("Scheduled fetch successful (x2)");
      expect(wrapper.text()).toContain("Something else failed");
    });
  });
});
