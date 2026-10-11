<template>
  <button
    type="button"
    class="rounded-full p-1 text-theme-text hover:bg-theme-border"
    :title="buttonTitle"
    @click="copyNote"
  >
    <SvgIcon type="mdi" :path="mdiContentCopy" :size="20" />
  </button>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";
import { mdiContentCopy } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";

import { apiErrorHandler, getNote } from "../../api.js";
import { getToastOptions } from "../../helpers.js";

const route = useRoute();
const toast = useToast();
const isCopying = ref(false);

const buttonTitle = computed(() => {
  return isCopying.value ? "Copying note..." : "Copy note markdown";
});

async function copyNote() {
  if (isCopying.value || !route.params.title) return;

  isCopying.value = true;
  try {
    const note = await getNote(route.params.title);
    await writeClipboardText(note.content || "");
    toast.add(getToastOptions("Note copied", "Copied", "success"));
  } catch (error) {
    if (error.response) {
      apiErrorHandler(error, toast);
      return;
    }
    console.error("Failed to copy note content:", error);
    toast.add(
      getToastOptions(
        "Could not copy this note. Please try again.",
        "Copy Failed",
        "error",
      ),
    );
  } finally {
    isCopying.value = false;
  }
}

async function writeClipboardText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();

  try {
    if (!document.execCommand("copy")) {
      throw new Error("Fallback copy command returned false.");
    }
  } finally {
    document.body.removeChild(textarea);
  }
}
</script>
