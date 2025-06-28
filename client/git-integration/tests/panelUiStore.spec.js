// client/git-integration/tests/panelUiStore.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { usePanelUiStore } from "../stores/panelUiStore.js";
import { useLogStore } from "../stores/logStore.js";

// --- MOCK SETUP ---
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => ({
    add: vi.fn(),
  })),
}));
// --- END MOCK SETUP ---

describe("panelUiStore", () => {
  let panelStore;
  let logStore;

  beforeEach(() => {
    // Set up a clean Pinia environment for each test
    setActivePinia(createPinia());

    // Get the actual store instances
    panelStore = usePanelUiStore();
    logStore = useLogStore();

    // Clear any mocks from previous tests
    vi.clearAllMocks();
  });

  it("toggleSidebar flips the isSidebarVisible state", () => {
    expect(panelStore.isSidebarVisible).toBe(false);
    panelStore.toggleSidebar();
    expect(panelStore.isSidebarVisible).toBe(true);
  });

  it("hideSidebar only hides if not pinned", () => {
    panelStore.isSidebarVisible = true;
    panelStore.isPinned = true;
    panelStore.hideSidebar();
    expect(panelStore.isSidebarVisible).toBe(true);

    panelStore.isPinned = false;
    panelStore.hideSidebar();
    expect(panelStore.isSidebarVisible).toBe(false);
  });

  it("showConfirmation should resolve true and not log when confirmed", async () => {
    // Spy on the logStore's action for this specific test
    const addLogSpy = vi.spyOn(logStore, "addLog");

    const promise = panelStore.showConfirmation({ title: "Test" });

    expect(panelStore.isConfirmModalVisible).toBe(true);

    panelStore.resolveConfirmation(true);

    await promise;
    expect(addLogSpy).not.toHaveBeenCalled();
  });

  it("showConfirmation should resolve false and log when cancelled", async () => {
    // Spy on the logStore's action for this specific test
    const addLogSpy = vi.spyOn(logStore, "addLog");

    const promise = panelStore.showConfirmation({ title: "Test Cancel" });

    expect(panelStore.isConfirmModalVisible).toBe(true);

    panelStore.resolveConfirmation(false);

    await promise;

    expect(addLogSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        level: "info",
        message: "Test Cancel: Operation cancelled by user.",
      }),
    );
  });
});
