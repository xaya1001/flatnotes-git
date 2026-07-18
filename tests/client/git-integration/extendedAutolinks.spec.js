import { describe, expect, it } from "vitest";

import {
  parseEmailLink,
  parseUrlLink,
} from "../../../client/components/toastui/extendedAutolinks.js";

describe("extendedAutolinks", () => {
  it("parses bare www links with an http URL", () => {
    expect(parseUrlLink("See www.example.com")).toEqual([
      {
        text: "www.example.com",
        range: [4, 18],
        url: "http://www.example.com",
      },
    ]);
  });

  it("parses http links without requiring an extra dot after the scheme", () => {
    expect(parseUrlLink("Open https://example.com/docs")).toEqual([
      {
        text: "https://example.com/docs",
        range: [5, 28],
        url: "https://example.com/docs",
      },
    ]);
  });

  it("does not include trailing punctuation in URL links", () => {
    expect(parseUrlLink("Open https://example.com/docs.")).toEqual([
      {
        text: "https://example.com/docs",
        range: [5, 28],
        url: "https://example.com/docs",
      },
    ]);
  });

  it("parses email links", () => {
    expect(parseEmailLink("Mail dev@example.com")).toEqual([
      {
        text: "dev@example.com",
        range: [5, 19],
        url: "mailto:dev@example.com",
      },
    ]);
  });
});
