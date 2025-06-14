// A singleton module to manage the EventSource connection.

let eventSource = null;

export function connectToGitEvents() {
  if (!eventSource) {
    const pathPrefix = window.FLATNOTES_PATH_PREFIX || "";
    const eventUrl = `${pathPrefix}/api/git/events`;

    console.log(`Connecting to SSE at ${eventUrl}`);
    eventSource = new EventSource(eventUrl);

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      // The error event on individual stores will handle UI feedback.
      // This will cause the connection to close. We can try to reconnect.
      eventSource.close();
      eventSource = null; // Allow reconnection on next call
    };
  }
  return eventSource;
}

export function disconnectFromGitEvents() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    console.log("SSE connection closed.");
  }
}
