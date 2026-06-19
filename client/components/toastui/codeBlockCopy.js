const BUTTON_CLASS = "toastui-code-copy-button";
const HANDLER_FLAG = "__flatnotesCodeBlockCopyHandler";

export function enhanceCodeBlockCopy(containerElement) {
  if (!containerElement) return;

  containerElement.querySelectorAll("pre").forEach((pre) => {
    if (pre.classList.contains("lang-mermaid")) return;
    if (!pre.querySelector("code")) return;
    if (pre.querySelector(`.${BUTTON_CLASS}`)) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = BUTTON_CLASS;
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code block");
    pre.appendChild(button);
  });

  if (containerElement[HANDLER_FLAG]) return;

  containerElement.addEventListener("click", handleCopyClick);
  containerElement[HANDLER_FLAG] = true;
}

async function handleCopyClick(event) {
  const button = event.target.closest?.(`.${BUTTON_CLASS}`);
  if (!button || !event.currentTarget.contains(button)) return;

  const code = button.closest("pre")?.querySelector("code");
  if (!code) return;

  event.preventDefault();
  try {
    await copyText(code.textContent || "");
    showTemporaryState(button, "Copied");
  } catch {
    showTemporaryState(button, "Failed");
  }
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall back for browsers that expose Clipboard API but deny this call.
    }
  }

  fallbackCopyText(text);
}

function fallbackCopyText(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function showTemporaryState(button, label) {
  button.textContent = label;
  window.setTimeout(() => {
    button.textContent = "Copy";
  }, 1200);
}
