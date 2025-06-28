<!-- client/git-integration/components/tabs/GitHistoryTab.vue -->
<template>
  <div class="relative flex h-full flex-col p-2">
    <!-- Commit List -->
    <div
      v-if="historyStore.gitLog.length === 0 && !historyStore.isLoading"
      class="py-4 text-center text-theme-text-muted"
    >
      No commit history found.
    </div>
    <div v-else class="min-h-0 flex-grow overflow-y-auto">
      <!-- Loading Skeleton -->
      <div v-if="historyStore.isLoading">
        <div
          v-for="i in 5"
          :key="i"
          class="mb-2 h-12 animate-pulse rounded bg-theme-border/50"
        ></div>
      </div>
      <!-- Actual Commit List -->
      <div v-else v-for="commit in historyStore.gitLog" :key="commit.hash">
        <div
          @click="historyStore.toggleCommitExpansion(commit.hash)"
          class="flex cursor-pointer items-center justify-between rounded p-2 hover:bg-theme-border"
        >
          <!-- Main commit info -->
          <div class="flex-grow pr-2">
            <div class="flex items-center space-x-2">
              <span
                v-if="!commit.is_pushed"
                class="rounded-full bg-yellow-500 px-2 py-0.5 text-xs font-bold text-white"
                title="This commit has not been pushed to the remote branch."
              >
                Unpushed
              </span>
              <div class="break-words text-sm font-semibold">
                {{ commit.message }}
              </div>
            </div>
            <div class="mt-1 text-xs text-theme-text-muted">
              <span>{{ commit.author_name }}</span> committed on
              <span>{{ new Date(commit.date).toLocaleString() }}</span>
            </div>
          </div>

          <!-- Right side with hash and chevron -->
          <div class="flex flex-shrink-0 items-center space-x-1 pl-2">
            <span class="font-mono text-xs">{{
              commit.hash.substring(0, 7)
            }}</span>
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
              <div class="ml-2 flex flex-shrink-0 items-center space-x-1">
                <!-- Open in editor button -->
                <button
                  v-if="file.path.endsWith('.md')"
                  @click="openNoteInEditor(file.path)"
                  class="p-1 text-theme-text-muted hover:text-theme-text"
                  title="Open File in Editor"
                >
                  <SvgIcon type="mdi" :path="mdilFile" :size="16" />
                </button>

                <!-- File status badge -->
                <span
                  class="ml-2 w-6 text-center font-bold"
                  :class="getCommitFileStatusClass(file.index_status)"
                  :title="getStatusLabel(file.index_status)"
                  >{{ file.index_status }}</span
                >

                <!-- View on GitHub button -->
                <a
                  v-if="historyStore.remoteBaseUrl"
                  :href="`${historyStore.remoteBaseUrl}/blob/${commit.hash}/${file.path}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  @click.stop
                  class="p-1 text-theme-text-muted hover:text-theme-text"
                  :title="`View '${file.path}' at this commit`"
                >
                  <SvgIcon type="mdi" :path="mdiOpenInNew" :size="14" />
                </a>

                <!-- Restore file button -->
                <button
                  @click.stop="handleRestoreFile(commit.hash, file.path)"
                  class="p-1 text-theme-text-muted hover:text-theme-text disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="isActionInProgress || isConflictRelated"
                  title="Restore this file to the version in this commit"
                >
                  <SvgIcon type="mdi" :path="mdiRestore" :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating Settings Button and Panel -->
    <div class="absolute bottom-4 right-4">
      <button
        @click="toggleSettingsPanel"
        class="flex h-8 w-8 items-center justify-center rounded-full bg-theme-background-elevated shadow-lg hover:bg-theme-border"
        title="Advanced Options"
      >
        <SvgIcon type="mdi" :path="mdiCog" :size="20" />
      </button>

      <OverlayPanel
        ref="settingsPanel"
        appendTo="body"
        :pt="{
          root: {
            class:
              'bg-theme-background-elevated border border-theme-border rounded-lg shadow-xl',
          },
          content: { class: 'p-0' },
        }"
      >
        <div class="w-64 p-3">
          <h4 class="mb-2 text-sm font-semibold text-theme-text">
            Advanced Actions
          </h4>
          <p class="mb-3 text-xs text-theme-text-muted">
            These are destructive operations. Use with caution.
          </p>
          <button
            v-if="statusStore.commitsAhead > 0 || statusStore.commitsBehind > 0"
            @click="handleReset"
            :disabled="isActionInProgress || isConflictRelated"
            class="w-full rounded border border-theme-danger p-2 text-sm font-semibold text-theme-danger hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Reset to Remote...
          </button>
          <p v-else class="text-xs text-theme-text-muted">
            No remote differences to reset.
          </p>
        </div>
      </OverlayPanel>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useHistoryStore } from "../../stores/historyStore";
import { useStatusStore } from "../../stores/statusStore";
import { usePanelUiStore } from "../../stores/panelUiStore";
import { useGitOperation } from "../../composables/useGitOperation";
import * as gitApi from "../../gitApi";
import { getCommitFileStatusClass, getStatusLabel } from "../../gitUtils";
import SvgIcon from "@jamescoyle/vue-icon";
import OverlayPanel from "primevue/overlaypanel";

import { mdilFile, mdilChevronDown, mdilChevronUp } from "@mdi/light-js";
import { mdiOpenInNew, mdiCog, mdiRestore } from "@mdi/js";

const historyStore = useHistoryStore();
const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();
const router = useRouter();

const { isLoading: isRestoring, execute: executeRestoreFile } = useGitOperation(
  "Restore File",
  gitApi.gitRestoreFile,
);
const { isLoading: isResetting, execute: executeResetToRemote } =
  useGitOperation("Reset to Remote", gitApi.gitResetToRemote);

const isActionInProgress = computed(
  () => isRestoring.value || isResetting.value,
);

const settingsPanel = ref();
const toggleSettingsPanel = (event) => {
  statusStore.fetchStatus();
  settingsPanel.value.toggle(event);
};

const isConflictRelated = computed(() => {
  const state = statusStore.repositoryState;
  if (!state) return false;
  return (
    state.includes("CONFLICT") ||
    state.includes("REBASING") ||
    state.includes("MERGING")
  );
});

function openNoteInEditor(path) {
  const title = path.replace(/\.md$/, "");
  router.push({
    name: "note",
    params: { title },
    query: { t: Date.now() },
  });
}

async function handleRestoreFile(commitHash, filepath) {
  const confirmed = await panelUiStore.showConfirmation({
    title: "Confirm File Restore",
    message: `This will overwrite your current version of '${filepath}' with the version from commit ${commitHash.substring(0, 7)}. This cannot be undone. Are you sure?`,
    confirmButtonText: "Yes, Restore File",
    confirmButtonStyle: "danger",
  });
  if (confirmed) {
    executeRestoreFile(commitHash, filepath).catch(() => {});
  }
}

async function handleReset() {
  const confirmed = await panelUiStore.showConfirmation({
    title: "Confirm Hard Reset",
    message:
      "This will permanently delete all unpushed commits and any uncommitted changes in your workspace. This action cannot be undone. Are you sure you want to match the remote state?",
    confirmButtonText: "Yes, Reset My Branch",
    confirmButtonStyle: "danger",
  });

  if (confirmed) {
    executeResetToRemote().catch(() => {});
  }
}
</script>
