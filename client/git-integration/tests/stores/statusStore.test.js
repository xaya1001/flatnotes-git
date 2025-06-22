// client/git-integration/tests/stores/statusStore.test.js

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useStatusStore } from "../../stores/statusStore";
import * as gitApi from "../../gitApi";
import { useConflictStore } from "../../stores/conflictStore";

// --- Mocking Setup ---

// Mock the entire gitApi module
vi.mock("../../gitApi", () => ({
  getGitStatus: vi.fn(),
}));

// Create a persistent mock object for the conflict store.
const mockConflictStore = {
  enterConflictMode: vi.fn(),
  exitConflictMode: vi.fn(),
  isInConflict: false,
};

// Mock the useConflictStore hook to ALWAYS return our single mock object.
vi.mock("../../stores/conflictStore", () => ({
  useConflictStore: vi.fn(() => mockConflictStore),
}));

// Mock UI dependencies
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => ({ add: vi.fn() })),
}));

vi.mock("vue-router", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

// --- Test Suite ---

describe("Git Status Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockConflictStore.isInConflict = false;
  });

  it("initializes with correct default state", () => {
    const store = useStatusStore();
    expect(store.gitStatus).toEqual({ files: [] });
    expect(store.commitMessage).toBe("");
    expect(store.isLoading).toBe(true);
    expect(store.summaryError).toBe(null);
    expect(store.branchName).toBe("");
    expect(store.filesChangedCount).toBe(0);
    expect(store.commitsAhead).toBe(0);
    expect(store.commitsBehind).toBe(0);
    expect(store.isTrackingUpstream).toBe(true);
    expect(store.repositoryState).toBe("CLEAN");
    expect(store.isInitialLoadComplete).toBe(false);
  });

  describe("Actions", () => {
    describe("fetchStatus", () => {
      it("should update state on successful fetch", async () => {
        const mockStatusData = {
          files: [
            { path: "test.md", index_status: "A", work_tree_status: " " },
          ],
          current_branch: "main",
          commits_ahead: 1,
          commits_behind: 2,
          is_tracking_upstream: true,
          repository_state: "CLEAN",
          files_changed_count: 1,
        };
        gitApi.getGitStatus.mockResolvedValue(mockStatusData);

        const store = useStatusStore();
        await store.fetchStatus();

        expect(store.gitStatus).toEqual(mockStatusData);
        expect(store.branchName).toBe("main");
        expect(store.commitsAhead).toBe(1);
        expect(store.commitsBehind).toBe(2);
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

      it("enters conflict mode when fetchStatus reports a conflict state", async () => {
        const mockConflictData = {
          files: [
            { path: "conflict.md", index_status: "U", work_tree_status: "U" },
          ],
          repository_state: "REBASING_CONFLICT",
        };
        gitApi.getGitStatus.mockResolvedValue(mockConflictData);

        const statusStore = useStatusStore();
        await statusStore.fetchStatus();

        expect(mockConflictStore.enterConflictMode).toHaveBeenCalledOnce();
        expect(mockConflictStore.enterConflictMode).toHaveBeenCalledWith(
          {
            state: "REBASING_CONFLICT",
            conflicted_files: ["conflict.md"],
          },
          { silent: true },
        );
      });

      it("exits conflict mode when fetchStatus reports a clean state", async () => {
        mockConflictStore.isInConflict = true;

        const mockCleanData = {
          files: [],
          repository_state: "CLEAN",
        };
        gitApi.getGitStatus.mockResolvedValue(mockCleanData);

        const statusStore = useStatusStore();
        await statusStore.fetchStatus();

        expect(mockConflictStore.exitConflictMode).toHaveBeenCalledOnce();
      });
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

    it("tooltipText shows loading message initially", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = false;
      expect(store.tooltipText).toBe("Loading Git status...");
    });

    it("tooltipText shows clean message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.branchName = "main";
      expect(store.tooltipText).toBe("Branch 'main' is up to date.");
    });

    it("tooltipText shows commits ahead and behind", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.branchName = "feature-branch";
      store.commitsBehind = 2;
      store.commitsAhead = 3;
      expect(store.tooltipText).toBe(
        "Branch 'feature-branch': 2 to pull, 3 to push. Click to view.",
      );
    });

    it("tooltipText shows local changes", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.branchName = "main";
      store.filesChangedCount = 5;
      expect(store.tooltipText).toBe(
        "Branch 'main': 5 changes. Click to view.",
      );
    });

    // The logic in the component is `repositoryState.value.includes("REBASE")`
    // So "REBASING_CONFLICT" should work. Let's test both cases explicitly.

    it("tooltipText shows rebase conflict message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.repositoryState = "REBASING_CONFLICT"; // Explicitly set REBASING
      expect(store.tooltipText).toBe(
        "Conflict: Rebase in progress. Click to resolve.",
      );
    });

    it("tooltipText shows merge conflict message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.repositoryState = "MERGING_CONFLICT"; // Explicitly set MERGING
      expect(store.tooltipText).toBe(
        "Conflict: Merge in progress. Click to resolve.",
      );
    });

    it("tooltipText shows server error message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.summaryError = "Could not connect";
      expect(store.tooltipText).toBe("Error: Could not connect.");
    });

    it("tooltipText shows not tracking upstream message", () => {
      const store = useStatusStore();
      store.isInitialLoadComplete = true;
      store.branchName = "local-only";
      store.isTrackingUpstream = false;
      expect(store.tooltipText).toBe(
        "Branch 'local-only': Branch not tracking remote. Click to view.",
      );
    });
  });
});
