import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const statusStoreMock = {
  fetchStatus: vi.fn(),
  setWebSocketFallbackActive: vi.fn(),
};

vi.mock("../../../client/git-integration/stores/statusStore", () => ({
  useStatusStore: () => statusStoreMock,
}));

describe("webSocket service", () => {
  let webSocketInstances;
  let originalWebSocket;
  let consoleWarnSpy;

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.close = vi.fn();
      webSocketInstances.push(this);
    }
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    vi.clearAllMocks();
    webSocketInstances = [];
    originalWebSocket = global.WebSocket;
    global.WebSocket = MockWebSocket;
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    consoleWarnSpy.mockRestore();
    vi.useRealTimers();
  });

  async function loadService() {
    const module = await import(
      "../../../client/git-integration/services/webSocket.js"
    );
    return module.webSocket;
  }

  it("activates fallback polling when the socket closes", async () => {
    const webSocket = await loadService();

    webSocket.connect();
    webSocketInstances[0].onclose();

    expect(statusStoreMock.setWebSocketFallbackActive).toHaveBeenCalledWith(
      true,
    );
    expect(statusStoreMock.fetchStatus).toHaveBeenCalledTimes(1);

    webSocket.disconnect();
  });

  it("clears fallback after a successful reconnect", async () => {
    const webSocket = await loadService();

    webSocket.connect();
    webSocketInstances[0].onclose();
    vi.advanceTimersByTime(4999);
    expect(webSocketInstances).toHaveLength(1);

    vi.advanceTimersByTime(1);
    expect(webSocketInstances).toHaveLength(2);

    webSocketInstances[1].onopen();
    expect(statusStoreMock.setWebSocketFallbackActive).toHaveBeenLastCalledWith(
      false,
    );

    webSocket.disconnect();
  });

  it("backs off reconnect attempts until a socket opens", async () => {
    const webSocket = await loadService();

    webSocket.connect();
    webSocketInstances[0].onclose();
    vi.advanceTimersByTime(5000);

    webSocketInstances[1].onclose();
    vi.advanceTimersByTime(9999);
    expect(webSocketInstances).toHaveLength(2);

    vi.advanceTimersByTime(1);
    expect(webSocketInstances).toHaveLength(3);

    webSocket.disconnect();
  });

  it("does not create duplicate connections while reconnect is pending", async () => {
    const webSocket = await loadService();

    webSocket.connect();
    webSocketInstances[0].onclose();
    webSocket.connect();

    expect(webSocketInstances).toHaveLength(1);

    webSocket.disconnect();
  });
});
