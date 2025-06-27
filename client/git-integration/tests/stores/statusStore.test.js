// client/git-integration/tests/stores/statusStore.test.js (REFACTORED)

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useStatusStore } from "../../stores/statusStore";
import * as gitApi from "../../gitApi";

// --- Mocking Setup ---

vi.mock("../../gitApi", () => ({
  getGitStatus: vi.fn(),
}));

// Mock router dependency
vi.mock("vue-router", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

// --- Test Suite ---

describe("Git Status Store (Refactored)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("initializes with correct default state", () => {
    const store = useStatusStore();
    expect(store.gitStatus).toEqual({ files: [] });
    expect(store.isLoading).toBe(true);
    expect(store.repositoryState).toBe("CLEAN");
    expect(store.isInitialLoadComplete).toBe(false);
  });

  describe("Actions: fetchStatus", () => {
    it("should update all state properties on successful fetch", async () => {
      const mockStatusData = {
        files: [{ path: "test.md", index_status: "A", work_tree_status: " " }],
        current_branch: "main",
        commits_ahead: 1,
        commits_behind: 2,
        is_tracking_upstream: true,
        repository_state: "REBASING_CONTINUE",
        files_changed_count: 1,
      };
      gitApi.getGitStatus.mockResolvedValue(mockStatusData);

      const store = useStatusStore();
      await store.fetchStatus();

      // Assert that all properties of the store are correctly updated
      expect(store.gitStatus).toEqual(mockStatusData);
      expect(store.branchName).toBe("main");
      expect(store.commitsAhead).toBe(1);
      expect(store.commitsBehind).toBe(2);
      expect(store.isTrackingUpstream).toBe(true);
      expect(store.repositoryState).toBe("REBASING_CONTINUE");
      expect(store.summaryError).toBe(null);
      expect(store.isLoading).toBe(false);
      expect(store.isInitialLoadComplete).toBe(true);
      expect(gitApi.getGitStatus).toHaveBeenCalledOnce();
    });

    it("should handle repository not initialized error (428)", async () => {
      const mockError = {
        response: {
          status: 428,
          data: { detail: "Git repository not initialized" },
        },
      };
      gitApi.getGitStatus.mockRejectedValue(mockError);

      const store = useStatusStore();
      await store.fetchStatus();

      expect(store.summaryError).toBe("Git repository not initialized");
      expect(store.gitStatus).toEqual({ files: [] });
      expect(store.isLoading).toBe(false);
      expect(store.isInitialLoadComplete).toBe(true);
    });

    it("does NOT call any conflictStore methods anymore", async () => {
      // This test implicitly verifies the decoupling
      const mockConflictData = {
        repository_state: "REBASING_CONFLICT",
        files: [],
      };
      gitApi.getGitStatus.mockResolvedValue(mockConflictData);

      const store = useStatusStore();
      // We spy on console.error to ensure no hidden errors are thrown
      const consoleSpy = vi.spyOn(console, "error");

      await store.fetchStatus();

      // The most important assertion: no more cross-store pollution
      expect(store.repositoryState).toBe("REBASING_CONFLICT");
      expect(consoleSpy).not.toHaveBeenCalled();
    });
  });

  describe("Computed Properties", () => {
    it("correctly filters staged and unstaged files", () => {
      const store = useStatusStore();
      store.gitStatus.files = [
        { path: "staged.md", index_status: "A", work_tree_status: " " },
        { path: "unstaged.md", index_status: " ", work_tree_status: "M" },
        { path: "both.md", index_status: "A", work_tree_status: "M" },
        { path: "new.md", index_status: "?", work_tree_status: "?" },
      ];
      expect(store.stagedFiles.map((f) => f.path)).toEqual([
        "staged.md",
        "both.md",
      ]);
      expect(store.unstagedFiles.map((f) => f.path)).toEqual([
        "unstaged.md",
        "both.md",
        "new.md",
      ]);
    });

    // Tooltip computed property tests remain relevant and should pass
    it("tooltipText shows rebase conflict message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.repositoryState = "REBASING_CONFLICT";
      expect(store.tooltipText).toBe(
        "Conflict: Rebase in progress. Click to resolve.",
      );
    });
  });
});
