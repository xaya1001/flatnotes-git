// client/git-integration/tests/useGitOperation.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useGitOperation } from "../composables/useGitOperation.js";
import eventBus from "../services/eventBus.js";
import { GIT_OPERATION, GIT_CONFLICT } from "../events.js";

vi.mock("../services/eventBus.js", () => ({
  default: {
    emit: vi.fn(),
  },
}));

describe("useGitOperation.js", () => {
  // Before each test, clear any previous mock history.
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // After each test, restore original implementations.
  afterEach(() => {
    vi.restoreAllMocks();
  });

  // --- Test Case 1: Successful Operation ---
  it("should handle a successful operation correctly", async () => {
    // 1. Arrange
    const mockActionName = "Test Success";
    const mockApiResponse = { detail: "Success!" };
    // Create a mock API function that resolves successfully.
    const mockOperationFunc = vi.fn().mockResolvedValue(mockApiResponse);

    // Instantiate the composable.
    const { isLoading, error, data, execute } = useGitOperation(
      mockActionName,
      mockOperationFunc,
    );

    // 2. Act
    const promise = execute("arg1", "arg2");

    // Assert that isLoading becomes true immediately.
    expect(isLoading.value).toBe(true);

    // Await the operation to complete.
    await promise;

    // 3. Assert
    // Assert final state.
    expect(isLoading.value).toBe(false);
    expect(data.value).toEqual(mockApiResponse);
    expect(error.value).toBeNull();

    // Assert the API function was called with correct arguments.
    expect(mockOperationFunc).toHaveBeenCalledWith("arg1", "arg2");

    // Assert event bus emissions.
    expect(eventBus.emit).toHaveBeenCalledTimes(2);
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_OPERATION.WILL_START, {
      actionName: mockActionName,
      operationId: expect.any(String), // We don't care about the exact UUID.
    });
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_OPERATION.DID_SUCCEED, {
      actionName: mockActionName,
      operationId: expect.any(String),
      response: mockApiResponse,
    });
  });

  // --- Test Case 2: Failed Operation (Generic Error) ---
  it("should handle a generic failed operation correctly", async () => {
    // 1. Arrange
    const mockActionName = "Test Failure";
    const mockApiError = new Error("Network Error");
    mockApiError.response = { status: 500, data: { detail: "Server Down" } };
    // Create a mock API function that rejects.
    const mockOperationFunc = vi.fn().mockRejectedValue(mockApiError);

    const { isLoading, error, data, execute } = useGitOperation(
      mockActionName,
      mockOperationFunc,
    );

    // 2. Act
    // We expect this to throw, so we wrap it.
    await expect(execute()).rejects.toThrow("Network Error");

    // 3. Assert
    expect(isLoading.value).toBe(false);
    expect(data.value).toBeNull();
    expect(error.value).toEqual(mockApiError); // The error object should be stored.

    expect(eventBus.emit).toHaveBeenCalledTimes(2);
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_OPERATION.WILL_START, {
      actionName: mockActionName,
      operationId: expect.any(String),
    });
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_OPERATION.DID_FAIL, {
      actionName: mockActionName,
      operationId: expect.any(String),
      err: mockApiError,
    });
  });

  // --- Test Case 3: Failed Operation (Conflict Error) ---
  it("should handle a 409 conflict error specifically", async () => {
    // 1. Arrange
    const mockActionName = "Test Conflict";
    const conflictErrorData = {
      state: "REBASING_CONFLICT",
      conflicted_files: ["note.md"],
    };
    const mockApiError = {
      response: {
        status: 409,
        data: {
          detail: conflictErrorData,
        },
      },
    };
    const mockOperationFunc = vi.fn().mockRejectedValue(mockApiError);

    const { isLoading, error, data, execute } = useGitOperation(
      mockActionName,
      mockOperationFunc,
    );

    // 2. Act
    await expect(execute()).rejects.toBe(mockApiError);

    // 3. Assert
    expect(isLoading.value).toBe(false);
    expect(data.value).toBeNull();
    expect(error.value).toEqual(mockApiError);

    // This is the key difference: it should emit a CONFLICT event, not a generic FAIL event.
    expect(eventBus.emit).toHaveBeenCalledTimes(2);
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_OPERATION.WILL_START, {
      actionName: mockActionName,
      operationId: expect.any(String),
    });
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_CONFLICT.DETECTED, {
      operationId: expect.any(String),
      errorData: conflictErrorData,
    });
    // Ensure it did NOT emit the generic fail event.
    expect(eventBus.emit).not.toHaveBeenCalledWith(
      GIT_OPERATION.DID_FAIL,
      expect.anything(),
    );
  });
});
