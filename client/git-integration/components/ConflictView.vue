<!-- client/git-integration/components/ConflictView.vue -->
<template>
  <div class="flex h-full flex-col">
    <!-- Header -->
    <div
      class="flex-shrink-0 border-b-2 border-red-500/50 bg-red-900/10 p-3 text-center"
    >
      <div class="flex items-center justify-center space-x-2">
        <SvgIcon
          type="mdi"
          :path="mdiAlertOctagon"
          :size="24"
          class="text-theme-danger"
        />
        <h2 class="text-lg font-bold text-theme-danger">
          {{ headerTitle }}
        </h2>
      </div>
      <p class="mt-1 text-xs text-theme-text-muted">
        {{ headerSubtitle }}
      </p>
    </div>

    <!-- Warning for unstaged changes -->
    <div
      v-if="showUnstagedChangesWarning"
      class="m-2 rounded-md border border-yellow-500/50 bg-yellow-400/10 p-2 text-center text-xs text-yellow-300"
    >
      You have unstaged changes. Please stage them before continuing the
      operation.
    </div>

    <!-- Main Content Area (Scrollable) -->
    <div class="min-h-0 flex-grow overflow-y-auto p-2">
      <!-- Staged Resolutions -->
      <div class="mb-4">
        <h3 class="mb-2 ml-1 text-sm font-semibold">
          Staged Resolutions ({{ stagedResolutions.length }})
        </h3>
        <FileTable
          :files="stagedResolutions"
          :is-loading="statusStore.isLoading || isActionInProgress"
          @open="handleOpenFile($event)"
          @action:primary="executeUnstage($event)"
          action-primary-icon="unstage"
        />
      </div>

      <!-- Unresolved Conflicts & Changes -->
      <div>
        <h3 class="mb-2 ml-1 text-sm font-semibold">
          Unresolved Conflicts & Changes ({{ unresolvedFiles.length }})
        </h3>
        <FileTable
          :files="unresolvedFiles"
          :is-loading="statusStore.isLoading || isActionInProgress"
          @open="handleOpenFile($event)"
          @action:primary="executeStage($event)"
          action-primary-icon="stage"
        />
      </div>
    </div>

    <!-- Footer with Action Buttons -->
    <div class="flex-shrink-0 border-t border-theme-border p-3">
      <div class="grid grid-cols-2 gap-3">
        <button
          @click="handleContinue"
          :disabled="isContinueDisabled"
          class="flex items-center justify-center rounded bg-theme-success p-2 font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          :title="continueButtonTitle"
        >
          <SvgIcon
            v-if="isContinuing"
            type="mdi"
            :path="mdilRefresh"
            :size="20"
            class="mr-2 animate-spin"
          />
          <span>{{ continueButtonText }}</span>
        </button>
        <button
          @click="handleAbort"
          :disabled="isActionInProgress"
          :title="abortButtonTitle"
          class="flex items-center justify-center rounded bg-theme-danger p-2 font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SvgIcon
            v-if="isAborting"
            type="mdi"
            :path="mdilRefresh"
            :size="20"
            class="mr-2 animate-spin"
          />
          <span>{{ abortButtonText }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { mdiAlertOctagon } from "@mdi/js";
import { mdilRefresh } from "@mdi/light-js";
import SvgIcon from "@jamescoyle/vue-icon";

import { useStatusStore } from "../stores/statusStore";
import { usePanelUiStore } from "../stores/panelUiStore";
import { useGitOperation } from "../composables/useGitOperation";
import * as gitApi from "../gitApi";
import FileTable from "./shared/FileTable.vue";

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();
const router = useRouter();

// --- API Operation Composables ---
const { isLoading: isContinuing, execute: executeContinue } = useGitOperation(
  "Continue Operation",
  gitApi.gitConflictContinue,
);
const { isLoading: isAborting, execute: executeAbort } = useGitOperation(
  "Abort Operation",
  gitApi.gitConflictAbort,
);
const { isLoading: isStaging, execute: executeStage } = useGitOperation(
  "Stage File",
  gitApi.gitStageFile,
);
const { isLoading: isUnstaging, execute: executeUnstage } = useGitOperation(
  "Unstage File",
  gitApi.gitUnstageFile,
);

const isActionInProgress = computed(
  () =>
    isContinuing.value ||
    isAborting.value ||
    isStaging.value ||
    isUnstaging.value,
);

// --- Computed Properties for File Partitioning ---
const unresolvedFiles = computed(() =>
  statusStore.gitStatus.files.filter((f) => f.work_tree_status !== " "),
);

const stagedResolutions = computed(() =>
  statusStore.gitStatus.files.filter(
    (f) => f.index_status !== " " && f.work_tree_status === " ",
  ),
);

// --- Computed Properties for Dynamic UI Text & State ---
const conflictType = computed(() =>
  statusStore.repositoryState.startsWith("REBASING") ? "Rebase" : "Merge",
);

const headerTitle = computed(() => {
  if (
    statusStore.repositoryState === "REBASING_CONTINUE" ||
    statusStore.repositoryState === "MERGING"
  ) {
    return "All Conflicts Resolved";
  }
  return `Resolve Conflicts to Continue ${conflictType.value}`;
});

const headerSubtitle = computed(() => {
  if (
    statusStore.repositoryState === "REBASING_CONTINUE" ||
    statusStore.repositoryState === "MERGING"
  ) {
    return `Ready to continue the ${conflictType.value.toLowerCase()} operation.`;
  }
  return `A ${conflictType.value.toLowerCase()} is in progress. Stage your resolved files to proceed.`;
});

const continueButtonText = computed(() => `Continue ${conflictType.value}`);
const abortButtonText = computed(() => `Abort ${conflictType.value}`);

const showUnstagedChangesWarning = computed(() => {
  const state = statusStore.repositoryState;
  return (
    (state === "REBASING_CONTINUE" || state === "MERGING") &&
    unresolvedFiles.value.length > 0
  );
});

const isContinueDisabled = computed(() => {
  if (isActionInProgress.value) return true;
  const state = statusStore.repositoryState;
  if (state !== "REBASING_CONTINUE" && state !== "MERGING") return true;
  if (unresolvedFiles.value.length > 0) return true;
  return false;
});

const continueButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  const state = statusStore.repositoryState;
  if (state !== "REBASING_CONTINUE" && state !== "MERGING") {
    return "You must resolve all conflicts and stage the files before continuing.";
  }
  if (unresolvedFiles.value.length > 0) {
    return "You must stage all remaining changes before continuing.";
  }
  return `Continue the ${conflictType.value.toLowerCase()} operation`;
});

const abortButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  return `Abort the ${conflictType.value.toLowerCase()} and restore previous state`;
});

// --- Action Handlers ---
function handleOpenFile(path) {
  const title = path.replace(/\.md$/, "");
  router.push({
    name: "note",
    params: { title },
    query: { t: Date.now() },
  });
}

async function handleContinue() {
  const confirmed = await panelUiStore.showConfirmation({
    title: `Confirm Continue ${conflictType.value}`,
    message: `This will proceed with the ${conflictType.value.toLowerCase()} using your staged resolutions. Are you sure?`,
    confirmButtonText: "Yes, Continue",
    confirmButtonStyle: "success",
  });
  if (confirmed) {
    executeContinue().catch(() => {});
  }
}

async function handleAbort() {
  const confirmed = await panelUiStore.showConfirmation({
    title: `Confirm Abort ${conflictType.value}`,
    message: `This will cancel the ${conflictType.value.toLowerCase()} and return your repository to the state before the operation began. All your conflict resolutions will be lost. This cannot be undone.`,
    confirmButtonText: `Yes, Abort`,
    confirmButtonStyle: "danger",
  });
  if (confirmed) {
    executeAbort().catch(() => {});
  }
}
</script>
