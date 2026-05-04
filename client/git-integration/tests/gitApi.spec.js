// client/git-integration/tests/gitApi.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../../api.js";
import { gitDiscardAll, gitResetToRemote } from "../gitApi.js";

vi.mock("../../api.js", () => ({
  api: {
    post: vi.fn(),
  },
}));

describe("gitApi.js", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.post.mockResolvedValue({ data: { message: "ok" } });
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
