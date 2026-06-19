import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

import CopyNoteButton from "../../../client/note-outline/components/CopyNoteButton.vue";
import { getNote } from "../../../client/api.js";

const toastAdd = vi.fn();
let route;

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useRoute: () => route,
  };
});

vi.mock("primevue/usetoast", () => ({
  useToast: () => ({ add: toastAdd }),
}));

vi.mock("../../../client/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getNote: vi.fn(),
  };
});

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(),
  },
});

const stubs = {
  SvgIcon: true,
};

describe("CopyNoteButton.vue", () => {
  beforeEach(() => {
    route = { params: { title: "Example Note" } };
    toastAdd.mockClear();
    vi.mocked(getNote).mockReset();
    vi.mocked(navigator.clipboard.writeText).mockReset();
  });

  it("copies the current saved note markdown", async () => {
    vi.mocked(getNote).mockResolvedValue({
      title: "Example Note",
      content: "# Heading\n\nBody",
    });
    vi.mocked(navigator.clipboard.writeText).mockResolvedValue(undefined);

    const wrapper = mount(CopyNoteButton, { global: { stubs } });
    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(getNote).toHaveBeenCalledWith("Example Note");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "# Heading\n\nBody",
    );
    expect(toastAdd).toHaveBeenCalled();
  });

  it("does nothing without a note title", async () => {
    route = { params: {} };
    const wrapper = mount(CopyNoteButton, { global: { stubs } });

    await wrapper.find("button").trigger("click");

    expect(getNote).not.toHaveBeenCalled();
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });
});
