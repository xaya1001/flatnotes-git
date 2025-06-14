<template>
  <div>
    <!-- Commit Header (Clickable) -->
    <div
      @click="historyStore.toggleCommitExpansion(commit.hash)"
      class="flex cursor-pointer items-center justify-between rounded p-2 hover:bg-theme-border"
    >
      <div class="flex-grow pr-2">
        <div class="break-words text-sm font-semibold">
          {{ commit.message }}
        </div>
        <div class="mt-1 text-xs text-theme-text-muted">
          <span>{{ commit.author_name }}</span> committed on
          <span>{{ new Date(commit.date).toLocaleDateString() }}</span>
        </div>
      </div>
      <div class="flex flex-shrink-0 items-center pl-2">
        <span class="font-mono text-xs">{{ commit.hash.substring(0, 7) }}</span>
        <SvgIcon
          type="mdi"
          :path="
            historyStore.expandedCommit === commit.hash
              ? mdilChevronUp
              : mdilChevronDown
          "
          :size="20"
          class="ml-1 text-theme-text-muted"
        />
      </div>
    </div>
    <!-- Expanded File List -->
    <div
      v-if="historyStore.expandedCommit === commit.hash"
      class="ml-4 border-l-2 border-theme-border pl-2"
    >
      <div
        v-if="
          historyStore.isFilesLoading &&
          !historyStore.commitFilesCache[commit.hash]
        "
        class="py-2 text-sm text-theme-text-muted"
      >
        Loading files...
      </div>
      <div
        v-else-if="
          historyStore.commitFilesCache[commit.hash] &&
          historyStore.commitFilesCache[commit.hash].length === 0
        "
        class="py-2 text-sm text-theme-text-muted"
      >
        No files in this commit.
      </div>
      <div v-else>
        <div
          v-for="file in historyStore.commitFilesCache[commit.hash]"
          :key="file.path"
          class="flex items-center justify-between py-1 text-sm"
        >
          <span class="truncate pr-2">{{ file.path }}</span>
          <div class="ml-2 flex flex-shrink-0 items-center">
            <button
              v-if="file.path.endsWith('.md')"
              @click="historyStore.openNoteInEditor(file.path)"
              class="p-1 text-theme-text-muted hover:text-theme-text"
              title="Open File"
            >
              <SvgIcon type="mdi" :path="mdilFile" :size="16" />
            </button>
            <span
              class="ml-2 w-6 text-center font-bold"
              :class="getCommitFileStatusClass(file.index_status)"
              >{{ file.index_status }}</span
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useHistoryStore } from "../../stores/historyStore";
import { getCommitFileStatusClass } from "../../gitUtils";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilFile, mdilChevronDown, mdilChevronUp } from "@mdi/light-js";

defineProps({
  commit: Object,
});

const historyStore = useHistoryStore();
</script>
