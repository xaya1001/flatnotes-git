import codeSyntaxHighlight from "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight-all.js";
import router from "../../router.js";

const customHTMLRenderer = {
  // Add id attribute to headings
  heading(node, { entering, getChildrenText, origin }) {
    const original = origin();
    if (entering) {
      original.attributes = {
        id: getChildrenText(node)
          .toLowerCase()
          .replace(/[^a-z0-9-\s]*/g, "")
          .trim()
          .replace(/\s/g, "-"),
      };
    }
    return original;
  },
  // Convert relative hash links to absolute links
  link(_, { entering, origin }) {
    const original = origin();
    if (entering) {
      const href = original.attributes.href;
      if (href.startsWith("#")) {
        const targetRoute = {
          ...router.currentRoute.value,
          hash: href,
        };
        original.attributes.href = router.resolve(targetRoute).href;
      }
    }
    return original;
  },

  // --- MERMAID ---
  codeBlock(node) {
    const language = node.lang || "txt";
    const content = node.literal;

    const trimmedContent = content.trim();
    const isMermaid =
      trimmedContent.startsWith("graph") ||
      trimmedContent.startsWith("sequenceDiagram") ||
      trimmedContent.startsWith("gantt") ||
      trimmedContent.startsWith("classDiagram") ||
      trimmedContent.startsWith("stateDiagram") ||
      trimmedContent.startsWith("pie") ||
      trimmedContent.startsWith("erDiagram") ||
      trimmedContent.startsWith("journey");

    if (isMermaid) {
      return [
        {
          type: "openTag",
          tagName: "pre",
          attributes: { class: "custom-mermaid-block" },
        },
        { type: "text", content: content + "\n" },
        { type: "closeTag", tagName: "pre" },
      ];
    }

    return [
      { type: "openTag", tagName: "pre" },
      {
        type: "openTag",
        tagName: "code",
        attributes: { "data-language": language },
      },
      { type: "text", content },
      { type: "closeTag", tagName: "code" },
      { type: "closeTag", tagName: "pre" },
    ];
  },
};

const baseOptions = {
  height: "100%",
  plugins: [codeSyntaxHighlight],
  customHTMLRenderer: customHTMLRenderer,
  usageStatistics: false,
};

export default baseOptions;
