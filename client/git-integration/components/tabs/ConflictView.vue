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
          :is-loading="statusStore.isLoading"
          @open="statusStore.openNoteInEditor($event)"
          @action:primary="actionsStore.handleUnstageFile($event)"
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
          :is-loading="statusStore.isLoading"
          @open="statusStore.openNoteInEditor($event)"
          @action:primary="actionsStore.handleStageFile($event)"
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
          class="rounded bg-theme-success p-2 font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          :title="continueButtonTitle"
        >
          {{ continueButtonText }}
        </button>
        <button
          @click="handleAbort"
          :disabled="actionsStore.isActionLoading"
          :title="abortButtonTitle"
          class="rounded bg-theme-danger p-2 font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ abortButtonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { mdiAlertOctagon } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { useConflictStore } from "../../stores/conflictStore";
import { useActionsStore } from "../../stores/actionsStore";
import { useStatusStore } from "../../stores/statusStore";
import { usePanelUiStore } from "../../stores/panelUiStore";
import FileTable from "../shared/FileTable.vue";

const conflictStore = useConflictStore();
const actionsStore = useActionsStore();
const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();

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
  if (actionsStore.isActionLoading) return true;
  const state = statusStore.repositoryState;
  if (state !== "REBASING_CONTINUE" && state !== "MERGING") return true;
  if (unresolvedFiles.value.length > 0) return true;
  return false;
});

const continueButtonTitle = computed(() => {
  if (actionsStore.isActionLoading) return "Action in progress...";
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
  if (actionsStore.isActionLoading) return "Action in progress...";
  return `Abort the ${conflictType.value.toLowerCase()} and restore previous state`;
});

// --- Action Handlers ---
async function handleContinue() {
  const confirmed = await panelUiStore.showConfirmation({
    title: `Confirm Continue ${conflictType.value}`,
    message: `This will proceed with the ${conflictType.value.toLowerCase()} using your staged resolutions. Are you sure?`,
    confirmButtonText: "Yes, Continue",
    confirmButtonStyle: "success",
  });
  if (confirmed) {
    conflictStore.handleContinue();
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
    conflictStore.handleAbort();
  }
}
</script>
