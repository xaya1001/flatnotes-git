import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LogDetail from "../../../client/git-integration/components/shared/LogDetail.vue";

describe("LogDetail.vue", () => {
  it("renders nested commit, pull, and push details", () => {
    const wrapper = mount(LogDetail, {
      props: {
        details: {
          commit: {
            hash: "abcdef1234567890",
            message: "save note",
            files_changed: [
              { status: "M", path: "note.md" },
              { status: "R", old_path: "old.md", path: "new.md" },
            ],
          },
          pull: {
            commits_received: 2,
            files_updated: [{ status: "A", path: "remote.md" }],
          },
          push: {
            commits_pushed: 1,
            files_changed: [{ status: "D", path: "deleted.md" }],
            commits: [{ hash: "1234567890abcdef", message: "push note" }],
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Commit");
    expect(wrapper.text()).toContain("abcdef1");
    expect(wrapper.text()).toContain("save note");
    expect(wrapper.text()).toContain("Files (2)");
    expect(wrapper.text()).toContain("old.md");
    expect(wrapper.text()).toContain("new.md");
    expect(wrapper.text()).toContain("Pull");
    expect(wrapper.text()).toContain("Commits Received: 2");
    expect(wrapper.text()).toContain("remote.md");
    expect(wrapper.text()).toContain("Push");
    expect(wrapper.text()).toContain("Commits Pushed: 1");
    expect(wrapper.text()).toContain("1234567");
    expect(wrapper.text()).toContain("push note");
  });

  it("accepts direct commit, pull, and push detail shapes", () => {
    expect(
      mount(LogDetail, {
        props: { details: { hash: "fedcba9876543210", message: "direct" } },
      }).text(),
    ).toContain("fedcba9");

    expect(
      mount(LogDetail, {
        props: { details: { commits_received: 0 } },
      }).text(),
    ).toContain("Commits Received: 0");

    expect(
      mount(LogDetail, {
        props: { details: { commits_pushed: 0 } },
      }).text(),
    ).toContain("Commits Pushed: 0");
  });

  it("falls back for unstructured detail text", () => {
    const wrapper = mount(LogDetail, {
      props: { details: "plain log details" },
    });

    expect(wrapper.find("pre").exists()).toBe(true);
    expect(wrapper.text()).toContain("plain log details");
  });
});
