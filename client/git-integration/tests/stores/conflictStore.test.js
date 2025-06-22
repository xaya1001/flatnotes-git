// client/git-integration/tests/stores/conflictStore.test.js

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useToast } from "primevue/usetoast";
import { useConflictStore } from "../../stores/conflictStore";
import { useActionsStore } from "../../stores/actionsStore";
import * as gitApi from "../../gitApi";
import eventBus from "../../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../../events";

// --- Mocking Setup ---

vi.mock("../../gitApi", () => ({
  gitConflictContinue: vi.fn(),
  gitConflictAbort: vi.fn(),
}));

vi.mock("../../eventBus", () => ({
  default: {
    on: vi.fn(),
    emit: vi.fn(),
  },
}));

const mockActionsStore = {
  isActionLoading: false,
};
vi.mock("../../stores/actionsStore", () => ({
  useActionsStore: vi.fn(() => mockActionsStore),
}));

const mockToast = {
  add: vi.fn(),
};
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => mockToast),
}));

// --- Test Suite ---

describe("Git Conflict Store", () => {
  let actionsStore;

  beforeEach(() => {
    setActivePinia(createPinia());
    actionsStore = useActionsStore();
    vi.clearAllMocks();
    // Also reset the mock store's properties before each test
    actionsStore.isActionLoading = false;
  });

  it("initializes with correct default state", () => {
    const store = useConflictStore();
    expect(store.isInConflict).toBe(false);
    expect(store.conflictedFiles).toEqual([]);
  });

  describe("enterConflictMode", () => {
    it("sets conflict state correctly for a REBASE conflict", () => {
      const store = useConflictStore();
      const errorData = {
        state: "REBASING_CONFLICT",
        conflicted_files: ["file1.md", "file2.md"],
      };
      store.enterConflictMode(errorData);
      expect(store.isInConflict).toBe(true);
      expect(store.conflictedFiles).toEqual(["file1.md", "file2.md"]);
    });

    it("uses an empty array if conflicted_files is missing", () => {
      const store = useConflictStore();
      const errorData = { state: "MERGING_CONFLICT" };
      store.enterConflictMode(errorData);
      expect(store.isInConflict).toBe(true);
      expect(store.conflictedFiles).toEqual([]);
    });

    it("shows a toast message by default", () => {
      const store = useConflictStore();
      const errorData = { state: "REBASING_CONFLICT", conflicted_files: [] };
      store.enterConflictMode(errorData);
      expect(mockToast.add).toHaveBeenCalledOnce();
      expect(mockToast.add).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: "warn",
          summary: "Sync Conflict: Rebase",
        }),
      );
    });

    it("does not show a toast message when silent option is true", () => {
      const store = useConflictStore();
      const errorData = { state: "REBASING_CONFLICT", conflicted_files: [] };
      store.enterConflictMode(errorData, { silent: true });
      expect(mockToast.add).not.toHaveBeenCalled();
    });
  });

  describe("exitConflictMode", () => {
    it("resets the state correctly", () => {
      const store = useConflictStore();
      store.isInConflict = true;
      store.conflictedFiles = ["file1.md"];
      store.exitConflictMode();
      expect(store.isInConflict).toBe(false);
      expect(store.conflictedFiles).toEqual([]);
    });
  });

  describe("handleContinue", () => {
    it("calls API, exits conflict mode, and emits success event", async () => {
      const store = useConflictStore();
      const mockResponse = { message: "Continue successful" };
      gitApi.gitConflictContinue.mockResolvedValue(mockResponse);
      store.isInConflict = true;

      await store.handleContinue();

      expect(gitApi.gitConflictContinue).toHaveBeenCalledOnce();
      expect(store.isInConflict).toBe(false);
      expect(eventBus.emit).toHaveBeenCalledWith(
        GIT_CONFLICT.RESOLVED,
        expect.any(Object),
      );
    });

    it("handles API failure and emits fail event", async () => {
      const store = useConflictStore();
      const mockError = new Error("API Failed");
      mockError.response = {}; // Simulate an axios-like error object
      gitApi.gitConflictContinue.mockRejectedValue(mockError);
      store.isInConflict = true;

      await store.handleContinue();

      expect(gitApi.gitConflictContinue).toHaveBeenCalledOnce();
      expect(store.isInConflict).toBe(true);
      expect(eventBus.emit).toHaveBeenCalledWith(
        GIT_OPERATION.DID_FAIL,
        expect.objectContaining({ err: mockError }),
      );
    });

    it("sets and unsets isActionLoading on the actionsStore", async () => {
      gitApi.gitConflictContinue.mockResolvedValue({});
      const store = useConflictStore();

      const promise = store.handleContinue();

      expect(actionsStore.isActionLoading).toBe(true);
      await promise;
      expect(actionsStore.isActionLoading).toBe(false);
    });
  });

  describe("handleAbort", () => {
    it("calls API, exits conflict mode, and emits success event", async () => {
      const store = useConflictStore();
      const mockResponse = { message: "Abort successful" };
      gitApi.gitConflictAbort.mockResolvedValue(mockResponse);
      store.isInConflict = true;

      await store.handleAbort();

      expect(gitApi.gitConflictAbort).toHaveBeenCalledOnce();
      expect(store.isInConflict).toBe(false);
      expect(eventBus.emit).toHaveBeenCalledWith(
        GIT_CONFLICT.RESOLVED,
        expect.any(Object),
      );
    });
  });
});
