import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useGlobalStore } from "../../../client/globalStore.js";
import { useGitIntegration } from "../../../client/git-integration/composables/useGitIntegration.js";

import { webSocket } from "../../../client/git-integration/services/webSocket.js";
import {
  cleanupGitEventHandlers,
  initializeGitEventHandlers,
} from "../../../client/git-integration/composables/eventHandler.js";

vi.mock("../../../client/git-integration/services/webSocket.js", () => ({
  webSocket: {
    connect: vi.fn(),
    disconnect: vi.fn(),
  },
}));

vi.mock("../../../client/git-integration/composables/eventHandler.js", () => ({
  cleanupGitEventHandlers: vi.fn(),
  initializeGitEventHandlers: vi.fn(),
}));

const TestComponent = {
  template: "<div></div>",
  setup() {
    useGitIntegration();
    return {};
  },
};

describe("useGitIntegration.js", () => {
  let globalStore;

  beforeEach(() => {
    setActivePinia(createPinia());
    globalStore = useGlobalStore();
    vi.clearAllMocks();
  });

  it("should NOT initialize services when git is disabled", () => {
    // Arrange
    globalStore.config = { value: { flatnotesGitEnabled: false } };
    // Act
    mount(TestComponent);
    // Assert
    expect(webSocket.connect).not.toHaveBeenCalled();
    expect(initializeGitEventHandlers).not.toHaveBeenCalled();
  });

  it("should initialize services when git is enabled", () => {
    // Arrange
    globalStore.config = { value: { flatnotesGitEnabled: true } };
    // Act
    mount(TestComponent);
    // Assert
    expect(webSocket.connect).toHaveBeenCalledOnce();
    expect(initializeGitEventHandlers).toHaveBeenCalledOnce();
  });

  it("should add visibilitychange event listener when enabled and clean it up", () => {
    const addEventListenerSpy = vi.spyOn(document, "addEventListener");
    const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

    globalStore.config = { value: { flatnotesGitEnabled: true } };

    const wrapper = mount(TestComponent);

    expect(addEventListenerSpy).toHaveBeenCalledWith(
      "visibilitychange",
      expect.any(Function),
    );

    wrapper.unmount();

    expect(cleanupGitEventHandlers).toHaveBeenCalledOnce();
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "visibilitychange",
      expect.any(Function),
    );
  });
});
