// client/git-integration/tests/historyStore.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useHistoryStore } from "../stores/historyStore.js";
import * as gitApi from "../gitApi.js";

vi.mock("../gitApi.js", () => ({
  getGitLog: vi.fn(),
  getGitCommitFiles: vi.fn(),
}));

const mockToastAdd = vi.fn();
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => ({
    add: mockToastAdd,
  })),
}));

const mockRouterPush = vi.fn();
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useRouter: () => ({
      push: mockRouterPush,
    }),
  };
});

describe("historyStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("fetchGitLog should handle API failure gracefully", async () => {
    // Arrange
    const store = useHistoryStore(); // Instantiate store inside the test
    const error = new Error("API Failed");
    gitApi.getGitLog.mockRejectedValue(error);

    // Act
    await store.fetchGitLog();

    // Assert
    expect(store.isLoading).toBe(false);
    expect(store.gitLog).toEqual([]);
    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "error",
        summary: "Error Fetching Log",
      }),
    );
  });

  it("openNoteInEditor should call router.push with correct params", () => {
    // Arrange
    const store = useHistoryStore();
    const path = "My Awesome Note.md";

    // Act
    store.openNoteInEditor(path);

    // Assert
    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "note",
      params: { title: "My Awesome Note" },
    });
  });

  it("toggleCommitExpansion should fetch files if not in cache", async () => {
    // Arrange
    const store = useHistoryStore();
    const commitHash = "abc1234";
    const mockFiles = [{ path: "test.md", status: "A" }];
    gitApi.getGitCommitFiles.mockResolvedValue(mockFiles);

    // Act
    await store.toggleCommitExpansion(commitHash);

    // Assert
    expect(store.expandedCommit).toBe(commitHash);
    expect(gitApi.getGitCommitFiles).toHaveBeenCalledWith(commitHash);
    expect(store.commitFilesCache[commitHash]).toEqual(mockFiles);
    expect(store.isFilesLoading).toBe(false);
  });

  it("toggleCommitExpansion should handle API failure when fetching files", async () => {
    // Arrange
    const store = useHistoryStore();
    const commitHash = "def5678";
    const error = new Error("Failed to fetch files");
    gitApi.getGitCommitFiles.mockRejectedValue(error);

    // Act
    await store.toggleCommitExpansion(commitHash);

    // Assert
    expect(store.expandedCommit).toBe(commitHash);
    expect(store.isFilesLoading).toBe(false);
    expect(store.commitFilesCache[commitHash]).toEqual([]);
    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "error",
        summary: "Error Fetching Commit Files",
      }),
    );
  });
});
