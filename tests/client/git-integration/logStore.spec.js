import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useLogStore } from "../../../client/git-integration/stores/logStore.js";
import * as gitApi from "../../../client/git-integration/gitApi.js";
import eventBus from "../../../client/git-integration/services/eventBus.js";
import {
  GIT_OPERATION,
  GIT_CONFLICT,
} from "../../../client/git-integration/events.js";

// --- MOCKS ---
vi.mock("../../../client/git-integration/gitApi.js", () => ({
  getGitActivityLog: vi.fn(),
  clearGitActivityLog: vi.fn(),
}));

const mockToastAdd = vi.fn();
vi.mock("primevue/usetoast", () => ({
  useToast: vi.fn(() => ({
    add: mockToastAdd,
  })),
}));
// --- END MOCKS ---

describe("logStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("addLog adds a new entry to the logs", () => {
    const store = useLogStore();
    store.addLog({ level: "info", message: "Test log" });
    expect(store.logs.length).toBe(1);
    expect(store.logs[0].message).toBe("Test log");
  });

  it("clearAllLogs calls the API and refetches on success", async () => {
    const store = useLogStore();
    const newLogs = [
      {
        id: "1",
        message: "new log",
        level: "info",
        timestamp: new Date().toISOString(),
      },
    ];

    // Arrange: Mock the sequence of API calls
    gitApi.clearGitActivityLog.mockResolvedValue();
    gitApi.getGitActivityLog.mockResolvedValue(newLogs); // This is what fetchActivityLog will get

    // Act
    await store.clearAllLogs();

    // Assert
    // 1. Check that the correct API sequence was called
    expect(gitApi.clearGitActivityLog).toHaveBeenCalled();
    expect(gitApi.getGitActivityLog).toHaveBeenCalled(); // <-- We check the *effect* of the internal call

    // 2. Check that the store's state was updated correctly
    expect(store.logs).toEqual(
      newLogs.map((log) => ({ ...log, status: "completed" })),
    );

    // 3. Check that the user was notified
    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "success" }),
    );
  });

  it("clearAllLogs handles API failure", async () => {
    const store = useLogStore();
    gitApi.clearGitActivityLog.mockRejectedValue(new Error("API Error"));

    await store.clearAllLogs();

    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "error" }),
    );
  });

  it("listens to and processes GIT_OPERATION events correctly", () => {
    const store = useLogStore();
    const operationId = "op-123";
    const actionName = "Test Action";

    // WILL_START
    eventBus.emit(GIT_OPERATION.WILL_START, { operationId, actionName });
    expect(store.logs[0].message).toBe(actionName);
    expect(store.logs[0].status).toBe("pending");

    // DID_SUCCEED
    const response = { details: "Success details" };
    eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
      operationId,
      actionName,
      response,
    });
    expect(store.logs[0].message).toContain("successful");
    expect(store.logs[0].level).toBe("success");
    expect(store.logs[0].details).toBe("Success details");
    expect(store.logs[0].status).toBe("completed");
    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "success" }),
    );

    // DID_FAIL
    const failOperationId = "op-456";
    const error = { response: { data: { detail: "Failure details" } } };
    eventBus.emit(GIT_OPERATION.WILL_START, {
      operationId: failOperationId,
      actionName,
    });
    eventBus.emit(GIT_OPERATION.DID_FAIL, {
      operationId: failOperationId,
      actionName,
      err: error,
    });
    expect(store.logs[0].message).toContain("Failed");
    expect(store.logs[0].level).toBe("error");
    expect(store.logs[0].details).toBe("Failure details");
  });

  it("listens to and processes GIT_CONFLICT event correctly", () => {
    const store = useLogStore();
    const operationId = "op-789";
    const errorData = {
      state: "REBASING_CONFLICT",
      conflicted_files: ["a.md"],
    };

    eventBus.emit(GIT_OPERATION.WILL_START, {
      operationId,
      actionName: "Sync",
    });
    eventBus.emit(GIT_CONFLICT.DETECTED, { operationId, errorData });

    expect(store.logs[0].level).toBe("warn");
    expect(store.logs[0].message).toContain("Sync failed: Rebase Conflict");
  });
});
