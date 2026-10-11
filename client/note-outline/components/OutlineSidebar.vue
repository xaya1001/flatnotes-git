<template>
  <div data-right-tool-sidebar class="fixed right-0 top-0 z-40 h-full">
    <Sidebar
      v-model:visible="outlineStore.isSidebarVisible"
      position="right"
      :modal="false"
      :dismissable="false"
      :showCloseIcon="false"
      :pt="{
        mask: { class: 'pointer-events-none' },
        root: {
          'data-right-tool-sidebar': '',
          class:
            'pointer-events-auto h-full border-l border-theme-border bg-theme-background-elevated shadow-none flex flex-col w-full sm:w-96 md:w-[480px]',
        },
        content: { class: 'p-0 h-full flex-grow min-h-0' },
      }"
    >
      <div class="flex h-full flex-col">
        <div
          class="flex flex-shrink-0 items-center justify-between border-b border-theme-border p-3"
        >
          <div class="flex min-w-0 items-center space-x-2">
            <SvgIcon type="mdi" :path="mdiFormatListBulleted" :size="20" />
            <h2 class="truncate text-lg font-semibold">Outline</h2>
            <CopyNoteButton />
          </div>

          <div class="flex flex-shrink-0 items-center space-x-1">
            <button
              @click="outlineStore.togglePin()"
              class="rounded-full p-1 hover:bg-theme-border"
              :title="outlineStore.isPinned ? 'Unpin Panel' : 'Pin Panel'"
            >
              <SvgIcon
                type="mdi"
                :path="outlineStore.isPinned ? mdilPin : mdilPinOff"
                :size="20"
              />
            </button>
            <button
              @click="outlineStore.forceHideSidebar()"
              class="rounded-full p-1 hover:bg-theme-border"
              title="Close Panel"
            >
              <SvgIcon type="mdi" :path="mdiClose" :size="20" />
            </button>
          </div>
        </div>

        <div v-if="outlineStore.headings.length === 0" class="p-4 text-sm">
          <p class="text-theme-text-muted">No headings in this note.</p>
        </div>

        <nav v-else class="min-h-0 flex-grow overflow-y-auto py-2 text-sm">
          <button
            v-for="heading in outlineStore.headings"
            :key="heading.id"
            type="button"
            class="block w-full truncate px-3 py-1.5 text-left transition-colors hover:bg-theme-background"
            :class="
              heading.id === outlineStore.activeHeadingId
                ? 'font-semibold text-theme-brand'
                : 'text-theme-text'
            "
            :style="{
              paddingLeft: `${12 + (heading.level - outlineStore.minLevel) * 14}px`,
            }"
            :title="heading.text"
            @click="scrollToHeading(heading.id)"
          >
            {{ heading.text }}
          </button>
        </nav>
      </div>
    </Sidebar>
  </div>
</template>

<script setup>
import Sidebar from "primevue/sidebar";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilPin, mdilPinOff } from "@mdi/light-js";
import { mdiClose, mdiFormatListBulleted } from "@mdi/js";

import { useOutlineStore } from "../stores/outlineStore.js";
import CopyNoteButton from "./CopyNoteButton.vue";

const outlineStore = useOutlineStore();

function scrollToHeading(id) {
  const element = document.getElementById(id);
  if (!element) return;

  outlineStore.setActiveHeading(id);
  element.scrollIntoView({ behavior: "smooth", block: "start" });
}
</script>
