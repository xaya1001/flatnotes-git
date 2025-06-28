// client/git-integration/tests/statusStore.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useStatusStore } from "../stores/statusStore.js";
import * as gitApi from "../gitApi.js";

// Mock the entire gitApi module
vi.mock("../gitApi.js");

describe("statusStore", () => {
  beforeEach(() => {
    // Create a fresh Pinia instance and make it active for each test
    setActivePinia(createPinia());
    // Reset mocks before each test
    vi.clearAllMocks();
  });

  it("should correctly parse and update state after a successful fetchStatus call", async () => {
    // 1. ARRANGE
    const store = useStatusStore();
    const mockApiResponse = {
      files: [{ path: "a.md", work_tree_status: "M", index_status: " " }],
      current_branch: "feature/new-ui",
      commits_ahead: 3,
      commits_behind: 2,
      is_tracking_upstream: true,
      repository_state: "CLEAN",
      files_changed_count: 1,
    };

    // Configure the mock to return our desired data
    gitApi.getGitStatus.mockResolvedValue(mockApiResponse);

    // 2. ACT
    await store.fetchStatus();

    // 3. ASSERT
    // Verify that the store's state has been updated correctly.
    expect(store.branchName).toBe("feature/new-ui");
    expect(store.commitsAhead).toBe(3);
    expect(store.commitsBehind).toBe(2);
    expect(store.filesChangedCount).toBe(1);
    expect(store.repositoryState).toBe("CLEAN");
    expect(store.summaryError).toBeNull();
    expect(store.isInitialLoadComplete).toBe(true);
    expect(store.gitStatus).toEqual(mockApiResponse);
  });

  it("should handle API errors during fetchStatus", async () => {
    // 1. ARRANGE
    const store = useStatusStore();
    const mockError = new Error("API Failure");
    mockError.response = { status: 428, data: { detail: "Git not init" } };

    gitApi.getGitStatus.mockRejectedValue(mockError);

    // 2. ACT
    await store.fetchStatus();

    // 3. ASSERT
    expect(store.summaryError).toBe("Git repository not initialized");
    expect(store.gitStatus).toEqual({ files: [] }); // State should be reset
    expect(store.isInitialLoadComplete).toBe(true); // Should still be marked as complete
  });
});
