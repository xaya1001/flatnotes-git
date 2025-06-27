// client/git-integration/tests/stores/conflictStore.test.js (REFACTORED)

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useConflictStore } from "../../stores/conflictStore";
import * as gitApi from "../../gitApi";

// --- Mocking Setup ---

vi.mock("../../gitApi", () => ({
  gitConflictContinue: vi.fn(),
  gitConflictAbort: vi.fn(),
}));

// Mock the actionsStore dependency, as it's still used for loading states
const mockActionsStore = { isActionLoading: false };
vi.mock("../../stores/actionsStore", () => ({
  useActionsStore: vi.fn(() => mockActionsStore),
}));

// Mock UI dependencies
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => ({ add: vi.fn() })),
}));

// --- Test Suite ---

describe("Git Conflict Store (Refactored)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockActionsStore.isActionLoading = false;
  });

  // The store no longer holds state, so no need to test initialization
  // or enter/exit methods.

  describe("Actions", () => {
    describe("handleContinue", () => {
      it("calls the correct API and manages loading state", async () => {
        gitApi.gitConflictContinue.mockResolvedValue({ message: "Success" });
        const store = useConflictStore();

        const promise = store.handleContinue();

        expect(mockActionsStore.isActionLoading).toBe(true);
        await promise;
        expect(gitApi.gitConflictContinue).toHaveBeenCalledOnce();
        expect(mockActionsStore.isActionLoading).toBe(false);
      });

      it("handles API failure correctly", async () => {
        const mockError = new Error("API Failed");
        gitApi.gitConflictContinue.mockRejectedValue(mockError);
        const store = useConflictStore();

        // We expect the promise to reject, but we need to catch it
        await expect(store.handleContinue()).rejects.toThrow("API Failed");

        expect(gitApi.gitConflictContinue).toHaveBeenCalledOnce();
        expect(mockActionsStore.isActionLoading).toBe(false); // Ensure loading is false even on error
      });
    });

    describe("handleAbort", () => {
      it("calls the correct API and manages loading state", async () => {
        gitApi.gitConflictAbort.mockResolvedValue({ message: "Aborted" });
        const store = useConflictStore();

        const promise = store.handleAbort();

        expect(mockActionsStore.isActionLoading).toBe(true);
        await promise;
        expect(gitApi.gitConflictAbort).toHaveBeenCalledOnce();
        expect(mockActionsStore.isActionLoading).toBe(false);
      });
    });
  });
});
