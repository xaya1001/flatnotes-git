import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { h } from "vue";
import FileTable from "../components/shared/FileTable.vue";

const SvgIconStub = {
  template: '<span class="svg-icon-stub"></span>',
};

const DataTableStub = {
  props: ["value"],
  setup(props, { slots }) {
    const columns = slots.default ? slots.default() : [];
    return () =>
      h(
        "div",
        { class: "datatable-stub" },
        (props.value || []).map((itemData) =>
          h(
            "div",
            { class: "simulated-row" },
            columns.map((column) => {
              const bodySlot = column.children.body;
              return bodySlot ? bodySlot({ data: itemData }) : null;
            }),
          ),
        ),
      );
  },
};

describe("FileTable.vue", () => {
  it("renders a message when no files are provided", () => {
    const wrapper = mount(FileTable, {
      props: {
        files: [],
        isLoading: false,
      },
      global: {
        stubs: {
          DataTable: true,
          Column: true,
          SvgIcon: SvgIconStub,
        },
      },
    });

    expect(wrapper.text()).toContain("No changes.");
  });

  // CORRECTED AND MORE SPECIFIC TEST
  it("renders unstaged files with correct work_tree_status", () => {
    const mockUnstagedFiles = [
      { path: "new-file.md", index_status: " ", work_tree_status: "A" },
      { path: "modified-file.md", index_status: " ", work_tree_status: "M" },
    ];

    const wrapper = mount(FileTable, {
      props: {
        files: mockUnstagedFiles,
        isLoading: false,
        actionPrimaryIcon: "stage", // This table is for unstaged changes
      },
      global: {
        stubs: {
          DataTable: DataTableStub,
          SvgIcon: SvgIconStub,
        },
      },
    });

    expect(wrapper.text()).toContain("new-file.md");
    expect(wrapper.text()).toContain("modified-file.md");

    const statuses = wrapper.findAll(".font-mono");
    // statusToShow should return work_tree_status because action is 'stage'
    expect(statuses[0].text()).toBe("A");
    expect(statuses[1].text()).toBe("M");
  });

  // ADDED A NEW TEST FOR THE OTHER CASE
  it("renders staged files with correct index_status", () => {
    const mockStagedFiles = [
      { path: "staged-delete.md", index_status: "D", work_tree_status: " " },
      { path: "staged-rename.md", index_status: "R", work_tree_status: " " },
    ];

    const wrapper = mount(FileTable, {
      props: {
        files: mockStagedFiles,
        isLoading: false,
        actionPrimaryIcon: "unstage", // This table is for staged changes
      },
      global: {
        stubs: {
          DataTable: DataTableStub,
          SvgIcon: SvgIconStub,
        },
      },
    });

    const statuses = wrapper.findAll(".font-mono");
    // statusToShow should return index_status because action is 'unstage'
    expect(statuses[0].text()).toBe("D");
    expect(statuses[1].text()).toBe("R");
  });

  it("applies the correct CSS class for file status", () => {
    const mockFiles = [
      { path: "new-file.md", index_status: " ", work_tree_status: "A" },
      { path: "modified-file.md", index_status: " ", work_tree_status: "M" },
      { path: "deleted-file.md", index_status: " ", work_tree_status: "D" },
    ];

    const wrapper = mount(FileTable, {
      props: {
        files: mockFiles,
        isLoading: false,
        actionPrimaryIcon: "stage",
      },
      global: {
        stubs: {
          DataTable: DataTableStub,
          SvgIcon: SvgIconStub,
        },
      },
    });

    const statuses = wrapper.findAll(".font-mono");
    expect(statuses[0].classes().some((c) => c.includes("green"))).toBe(true);
    expect(statuses[1].classes().some((c) => c.includes("blue"))).toBe(true);
    expect(statuses[2].classes().some((c) => c.includes("red"))).toBe(true);
  });

  it("emits 'action:primary' event with correct filepath on button click", async () => {
    const mockFiles = [
      { path: "file-to-stage.md", index_status: " ", work_tree_status: "M" },
    ];
    const wrapper = mount(FileTable, {
      props: {
        files: mockFiles,
        actionPrimaryIcon: "stage",
      },
      global: {
        stubs: {
          DataTable: DataTableStub,
          SvgIcon: SvgIconStub,
        },
      },
    });

    await wrapper.find('button[title="Stage"]').trigger("click");

    const primaryActionEvents = wrapper.emitted("action:primary");
    expect(primaryActionEvents).toHaveLength(1);
    expect(primaryActionEvents[0]).toEqual(["file-to-stage.md"]);
  });

  it("emits 'open' event when open button is clicked for an .md file", async () => {
    const mockFiles = [
      { path: "my-note.md", index_status: "M", work_tree_status: " " },
      { path: "image.png", index_status: "A", work_tree_status: " " },
    ];
    const wrapper = mount(FileTable, {
      props: {
        files: mockFiles,
        // No action icon needed for this test
      },
      global: {
        stubs: {
          DataTable: DataTableStub,
          SvgIcon: SvgIconStub,
        },
      },
    });

    const openButtons = wrapper.findAll('button[title="Open File"]');
    expect(openButtons).toHaveLength(1);

    await openButtons[0].trigger("click");

    const openEvents = wrapper.emitted("open");
    expect(openEvents).toHaveLength(1);
    expect(openEvents[0]).toEqual(["my-note.md"]);
  });
});
