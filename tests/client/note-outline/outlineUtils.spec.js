import { afterEach, describe, expect, it } from "vitest";

import {
  collectOutlineHeadings,
  slugifyHeading,
} from "../../../client/note-outline/outlineUtils.js";

describe("outlineUtils", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("slugifies unicode headings while removing punctuation", () => {
    expect(slugifyHeading("  章节 1: API 设计!  ")).toBe("章节-1-api-设计");
  });

  it("collects headings from the toast viewer and assigns ids", () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h1>Intro</h1>
        <p>Body</p>
        <h2>Details</h2>
      </article>
    `;

    expect(collectOutlineHeadings(document)).toEqual([
      { id: "intro", text: "Intro", level: 1 },
      { id: "details", text: "Details", level: 2 },
    ]);
    expect(document.querySelector("h1").id).toBe("intro");
    expect(document.querySelector("h2").id).toBe("details");
  });

  it("collects headings when the toast viewer is passed directly", () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h2>Direct Viewer</h2>
      </article>
    `;

    expect(
      collectOutlineHeadings(document.querySelector(".toast-viewer")),
    ).toEqual([{ id: "direct-viewer", text: "Direct Viewer", level: 2 }]);
  });

  it("ignores headings outside the toast viewer", () => {
    document.body.innerHTML = `
      <h1>Page Title</h1>
      <article>
        <h2>Outside Viewer</h2>
      </article>
    `;

    expect(collectOutlineHeadings(document)).toEqual([]);
  });

  it("creates stable unique ids for duplicate headings", () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h2>Repeat</h2>
        <h3>Repeat</h3>
        <h4>Repeat</h4>
      </article>
    `;

    expect(
      collectOutlineHeadings(document).map((heading) => heading.id),
    ).toEqual(["repeat", "repeat-2", "repeat-3"]);
  });

  it("preserves unique existing heading ids", () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h2 id="custom-id">Existing</h2>
      </article>
    `;

    expect(collectOutlineHeadings(document)).toEqual([
      { id: "custom-id", text: "Existing", level: 2 },
    ]);
  });

  it("ignores empty headings", () => {
    document.body.innerHTML = `
      <article class="toast-viewer">
        <h2>   </h2>
        <h3>Valid</h3>
      </article>
    `;

    expect(collectOutlineHeadings(document)).toEqual([
      { id: "valid", text: "Valid", level: 3 },
    ]);
  });
});
