import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  cleanupGitEventHandlers,
  initializeGitEventHandlers,
} from "../../../client/git-integration/composables/eventHandler.js";
import eventBus from "../../../client/git-integration/services/eventBus.js";
import { useStatusStore } from "../../../client/git-integration/stores/statusStore.js";

// --- MOCK SETUP ---
vi.mock("../../../client/git-integration/stores/statusStore.js", () => ({
  useStatusStore: vi.fn(),
}));
// --- END MOCK SETUP ---

describe("eventHandler.js", () => {
  let statusStoreMock;

  beforeEach(() => {
    cleanupGitEventHandlers();
    // Before each test, create a fresh spy and configure the mock to use it.
    const fetchStatusSpy = vi.fn();
    statusStoreMock = { fetchStatus: fetchStatusSpy };
    useStatusStore.mockReturnValue(statusStoreMock);

    // Clear any calls from previous tests
    fetchStatusSpy.mockClear();
  });

  it('should call fetchStatus on "note:saved" event', () => {
    // 1. Arrange: Register the event handlers
    initializeGitEventHandlers();

    // 2. Act: Emit the event
    eventBus.emit("note:saved");

    // 3. Assert: Verify the mock was called
    expect(statusStoreMock.fetchStatus).toHaveBeenCalled();
  });

  it('should call fetchStatus on "note:deleted" event', () => {
    // 1. Arrange
    initializeGitEventHandlers();

    // 2. Act
    eventBus.emit("note:deleted");

    // 3. Assert
    expect(statusStoreMock.fetchStatus).toHaveBeenCalled();
  });

  // Optional: A test to ensure no cross-talk
  it("should not call fetchStatus for an unrelated event", () => {
    // 1. Arrange
    initializeGitEventHandlers();

    // 2. Act
    eventBus.emit("some:other:event");

    // 3. Assert
    expect(statusStoreMock.fetchStatus).not.toHaveBeenCalled();
  });

  it("should not register duplicate handlers", () => {
    initializeGitEventHandlers();
    initializeGitEventHandlers();

    eventBus.emit("note:saved");

    expect(statusStoreMock.fetchStatus).toHaveBeenCalledTimes(1);
  });
});
