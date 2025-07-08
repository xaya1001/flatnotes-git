// client/git-integration/tests/useGitOperation.spec.js

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { defineComponent } from "vue";
import { GIT_OPERATION, GIT_CONFLICT } from "../events.js";
import { useGitOperation } from "../composables/useGitOperation.js";
import eventBus from "../services/eventBus.js";

// Mock dependencies
vi.mock("../services/eventBus.js", () => ({
  default: {
    emit: vi.fn(),
  },
}));

// We will mock useToast for the specific test that needs it.
const mockToastAdd = vi.fn();
vi.mock("primevue/usetoast", () => ({
  useToast: () => ({
    add: mockToastAdd,
  }),
}));

// Create a test harness component. This is good practice but not strictly
// necessary anymore since we are mocking useToast. However, it's a robust
// pattern for other composables, so we'll keep it.
const TestComponent = defineComponent({
  props: ["actionName", "operationFunc"],
  template: "<div></div>",
  setup(props) {
    const operation = useGitOperation(props.actionName, props.operationFunc);
    return { operation };
  },
});

describe("useGitOperation.js", () => {
  beforeEach(() => {
    // Clear mocks before each test
    vi.clearAllMocks();
    mockToastAdd.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // A simplified harness mount function
  const mountHarness = (actionName, operationFunc) => {
    return mount(TestComponent, {
      props: {
        actionName,
        operationFunc,
      },
    });
  };

  it("should handle a successful operation correctly", async () => {
    const mockOperationFunc = vi.fn().mockResolvedValue({ detail: "Success!" });
    const wrapper = mountHarness("Test Success", mockOperationFunc);

    const { isLoading, error, data, execute } = wrapper.vm.operation;
    await execute("arg1", "arg2");

    expect(isLoading.value).toBe(false);
    expect(data.value).toEqual({ detail: "Success!" });
    expect(error.value).toBeNull();
    expect(mockOperationFunc).toHaveBeenCalledWith("arg1", "arg2");

    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.WILL_START,
      expect.any(Object),
    );
    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.DID_SUCCEED,
      expect.any(Object),
    );
  });

  it("should handle a generic failed operation correctly", async () => {
    const mockApiError = new Error("Network Error");
    mockApiError.response = { status: 500, data: { detail: "Server Down" } };
    const mockOperationFunc = vi.fn().mockRejectedValue(mockApiError);
    const wrapper = mountHarness("Test Failure", mockOperationFunc);

    const { execute } = wrapper.vm.operation;
    await expect(execute()).rejects.toThrow("Network Error");

    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.WILL_START,
      expect.any(Object),
    );
    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.DID_FAIL,
      expect.any(Object),
    );
  });

  it("should handle a 409 conflict error specifically", async () => {
    const conflictErrorData = {
      state: "REBASING_CONFLICT",
      conflicted_files: ["note.md"],
    };
    const mockApiError = {
      response: { status: 409, data: { detail: conflictErrorData } },
    };
    const mockOperationFunc = vi.fn().mockRejectedValue(mockApiError);
    const wrapper = mountHarness("Test Conflict", mockOperationFunc);

    const { execute } = wrapper.vm.operation;
    await expect(execute()).rejects.toBe(mockApiError);

    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.WILL_START,
      expect.any(Object),
    );
    expect(eventBus.emit).toHaveBeenCalledWith(GIT_CONFLICT.DETECTED, {
      operationId: expect.any(String),
      errorData: conflictErrorData,
    });
    expect(eventBus.emit).not.toHaveBeenCalledWith(
      GIT_OPERATION.DID_FAIL,
      expect.anything(),
    );
  });

  it("should handle a 401 authentication error by showing toast and emitting DID_FAIL", async () => {
    const authErrorData = {
      state: "AUTHENTICATION_FAILED",
      message: "Git remote authentication failed.",
    };
    const mockApiError = {
      response: { status: 401, data: { detail: authErrorData } },
    };
    const mockOperationFunc = vi.fn().mockRejectedValue(mockApiError);

    const wrapper = mountHarness("Test Auth Failure", mockOperationFunc);

    const { execute } = wrapper.vm.operation;
    await expect(execute()).rejects.toBe(mockApiError);

    // Assert that the specific toast was shown
    expect(mockToastAdd).toHaveBeenCalledOnce();
    expect(mockToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "error",
        summary: "Git Authentication Failed",
      }),
    );

    // Assert that both WILL_START and DID_FAIL events were emitted
    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.WILL_START,
      expect.any(Object),
    );
    expect(eventBus.emit).toHaveBeenCalledWith(
      GIT_OPERATION.DID_FAIL,
      expect.any(Object),
    );
  });
});
