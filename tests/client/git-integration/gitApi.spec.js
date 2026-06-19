import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../client/api.js";
import {
  clearGitActivityLog,
  getBranches,
  getGitActivityLog,
  getGitCommitFiles,
  getGitLog,
  getGitStatus,
  gitAddAll,
  gitCommit,
  gitConflictAbort,
  gitConflictContinue,
  gitDiscardAll,
  gitDiscardFile,
  gitPull,
  gitPush,
  gitResetToRemote,
  gitRestoreFile,
  gitStageFile,
  gitSyncWorkspace,
  gitUnstageAll,
  gitUnstageFile,
  switchBranch,
} from "../../../client/git-integration/gitApi.js";

vi.mock("../../../client/api.js", () => ({
  api: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("gitApi.js", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.delete.mockResolvedValue({});
    api.get.mockResolvedValue({ data: { message: "ok" } });
    api.post.mockResolvedValue({ data: { message: "ok" } });
  });

  it.each([
    [getGitStatus, [], "api/git/status"],
    [getGitLog, [25, 3], "api/git/log", { params: { limit: 25, page: 3 } }],
    [getGitActivityLog, [], "api/git/activity-log"],
    [getGitCommitFiles, ["abc123"], "api/git/commits/abc123/files"],
    [getBranches, [], "api/git/branches"],
  ])("returns data from GET wrapper %#", async (fn, args, url, config) => {
    await expect(fn(...args)).resolves.toEqual({ message: "ok" });

    if (config) {
      expect(api.get).toHaveBeenCalledWith(url, config);
    } else {
      expect(api.get).toHaveBeenCalledWith(url);
    }
  });

  it.each([
    [gitAddAll, [], "api/git/add_all"],
    [gitUnstageAll, [], "api/git/unstage_all"],
    [gitCommit, ["save note"], "api/git/commit", { message: "save note" }],
    [
      gitPull,
      [{ prune: true }],
      "api/git/pull",
      null,
      { params: { prune: true } },
    ],
    [
      gitPush,
      [{ force: false }],
      "api/git/push",
      null,
      { params: { force: false } },
    ],
    [gitStageFile, ["note.md"], "api/git/stage_file", { filepath: "note.md" }],
    [
      gitUnstageFile,
      ["note.md"],
      "api/git/unstage_file",
      { filepath: "note.md" },
    ],
    [
      gitDiscardFile,
      ["note.md"],
      "api/git/discard_file",
      { filepath: "note.md" },
    ],
    [gitDiscardAll, [], "api/git/discard_all", { confirm: true }],
    [gitSyncWorkspace, ["sync"], "api/git/sync", { message: "sync" }],
    [
      switchBranch,
      ["feature"],
      "api/git/branches/switch",
      { branch_name: "feature" },
    ],
    [gitResetToRemote, [], "api/git/reset-to-remote", { confirm: true }],
    [
      gitRestoreFile,
      ["abc123", "note.md"],
      "api/git/restore-file",
      { commit_hash: "abc123", filepath: "note.md" },
    ],
    [gitConflictContinue, [], "api/git/conflict/continue"],
    [gitConflictAbort, [], "api/git/conflict/abort"],
  ])(
    "returns data from POST wrapper %#",
    async (fn, args, url, body, config) => {
      await expect(fn(...args)).resolves.toEqual({ message: "ok" });

      if (config) {
        expect(api.post).toHaveBeenCalledWith(url, body, config);
      } else if (body !== undefined) {
        expect(api.post).toHaveBeenCalledWith(url, body);
      } else {
        expect(api.post).toHaveBeenCalledWith(url);
      }
    },
  );

  it("deletes the activity log without requiring response data", async () => {
    await expect(clearGitActivityLog()).resolves.toBeUndefined();

    expect(api.delete).toHaveBeenCalledWith("api/git/activity-log");
  });

  it.each([
    [getGitStatus, "get"],
    [gitAddAll, "post"],
    [clearGitActivityLog, "delete"],
  ])("rejects API errors from %s", async (fn, method) => {
    const error = new Error("network failed");
    api[method].mockRejectedValueOnce(error);

    await expect(fn()).rejects.toBe(error);
  });

  it("sends explicit confirmation when discarding all changes", async () => {
    await gitDiscardAll();

    expect(api.post).toHaveBeenCalledWith("api/git/discard_all", {
      confirm: true,
    });
  });

  it("sends explicit confirmation when resetting to remote", async () => {
    await gitResetToRemote();

    expect(api.post).toHaveBeenCalledWith("api/git/reset-to-remote", {
      confirm: true,
    });
  });
});
