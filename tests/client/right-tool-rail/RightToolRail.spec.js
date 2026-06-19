import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RightToolRail from "../../../client/right-tool-rail/components/RightToolRail.vue";

describe("RightToolRail.vue", () => {
  it("offsets itself by the active panel width and renders tools", () => {
    const wrapper = mount(RightToolRail, {
      props: { activePanelWidth: 320 },
      slots: {
        default: '<button data-test="tool">Tool</button>',
      },
    });

    const rail = wrapper.find("[data-right-tool-rail]");

    expect(rail.attributes("style")).toContain("translateX(-320px)");
    expect(wrapper.find('[data-test="tool"]').exists()).toBe(true);
  });
});
