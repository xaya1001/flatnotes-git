<!-- client/git-integration/components/tabs/WorkspaceTab.vue -->
<template>
  <div class="flex h-full flex-col">
    <!-- Main Content Area (Scrollable) -->
    <div class="min-h-0 flex-grow overflow-y-auto p-2">
      <!-- Commit & Sync Area -->
      <div class="mb-4 flex-shrink-0 px-2">
        <div class="relative">
          <textarea
            v-model="statusStore.commitMessage"
            rows="3"
            class="w-full rounded border bg-theme-background p-2 pr-8 text-sm focus:border-theme-brand focus:ring-theme-brand"
          ></textarea>
          <button
            class="tooltip-trigger absolute right-2 top-2 p-1 text-theme-text-muted hover:text-theme-text"
            :data-tooltip="tooltipText"
            aria-label="Show commit message placeholders"
            tabindex="0"
          >
            <SvgIcon type="mdi" :path="mdiInformationOutline" :size="16" />
          </button>
        </div>
        <!-- Action Buttons Grid -->
        <div class="mt-2 grid grid-cols-2 gap-2">
          <!-- Row 1: Network Actions -->
          <button
            @click="executePull().catch(() => {})"
            :disabled="isPullDisabled"
            :title="pullButtonTitle"
            class="flex items-center justify-center rounded p-2 text-sm font-semibold transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50"
            :class="pullButtonStyle"
          >
            <SvgIcon
              v-if="isPulling"
              type="mdi"
              :path="mdilRefresh"
              :size="16"
              class="animate-spin"
            />
            <SvgIcon
              v-else-if="statusStore.commitsBehind > 0"
              type="mdi"
              :path="mdilArrowDown"
              :size="16"
              class="mr-1"
            />
            <span>{{ pullButtonText }}</span>
          </button>
          <button
            @click="executePush().catch(() => {})"
            :disabled="isPushDisabled"
            :title="pushButtonTitle"
            class="flex items-center justify-center rounded p-2 text-sm font-semibold transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50"
            :class="pushButtonStyle"
          >
            <SvgIcon
              v-if="isPushing"
              type="mdi"
              :path="mdilRefresh"
              :size="16"
              class="animate-spin"
            />
            <SvgIcon
              v-else-if="statusStore.commitsAhead > 0"
              type="mdi"
              :path="mdilArrowUp"
              :size="16"
              class="mr-1"
            />
            <span>{{ pushButtonText }}</span>
          </button>

          <!-- Row 2: Commit Actions -->
          <button
            @click="handleCommitStaged"
            :disabled="isCommitStagedDisabled"
            :title="commitStagedButtonTitle"
            class="flex items-center justify-center rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
          >
            <SvgIcon
              v-if="isCommitting"
              type="mdi"
              :path="mdilRefresh"
              :size="16"
              class="animate-spin"
            />
            <span>Commit Staged</span>
          </button>
          <button
            @click="handleSync"
            :disabled="isSyncDisabled"
            :title="syncButtonTitle"
            class="flex items-center justify-center rounded p-2 text-sm font-semibold text-white transition-colors duration-200 hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            :class="syncButtonStyle"
          >
            <SvgIcon
              v-if="isSyncing"
              type="mdi"
              :path="mdilRefresh"
              :size="16"
              class="animate-spin"
            />
            <span>Commit & Sync</span>
          </button>
        </div>
      </div>

      <!-- NEW: .gitignore Helper Message -->
      <div
        v-if="showGitignoreHelper"
        class="mx-2 mb-4 rounded-md border border-blue-500/30 bg-blue-500/10 p-3 text-sm"
      >
        <div class="flex items-start">
          <SvgIcon
            type="mdi"
            :path="mdiInformationOutline"
            :size="20"
            class="mr-2 mt-0.5 flex-shrink-0 text-blue-400"
          />
          <div>
            <h4 class="font-semibold text-theme-text">
              A .gitignore file is present
            </h4>
            <p class="mt-1 text-xs text-theme-text-muted">
              This file tells Git to ignore certain files, like the app's cache.
              It was automatically created to ensure a clean repository.
            </p>
            <p class="mt-2 text-xs text-theme-text-muted">
              It's recommended to
              <a
                href="#"
                @click.prevent="stageAndPrefillCommit"
                class="font-semibold text-theme-brand hover:underline"
                >stage and commit this file</a
              >
              to keep your workspace clean.
            </p>
          </div>
        </div>
      </div>

      <!-- File Lists -->
      <div class="px-2">
        <!-- Staged Files -->
        <div class="mb-4">
          <div class="mb-2 ml-1 flex items-center justify-between">
            <h3 class="text-sm font-semibold">
              Staged Changes ({{ statusStore.stagedFiles.length }})
            </h3>
            <button
              @click="executeUnstageAll().catch(() => {})"
              :disabled="isUnstageAllDisabled"
              title="Unstage All"
              class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:cursor-not-allowed disabled:opacity-50"
            >
              Unstage All
            </button>
          </div>
          <FileTable
            :files="statusStore.stagedFiles"
            :is-loading="isTableLoading"
            @open="handleOpenFile($event)"
            @action:primary="executeUnstageFile($event).catch(() => {})"
            action-primary-icon="unstage"
          />
        </div>

        <!-- Unstaged Files -->
        <div>
          <div class="mb-2 ml-1 flex items-center justify-between">
            <h3 class="text-sm font-semibold">
              Changes ({{ statusStore.unstagedFiles.length }})
            </h3>
            <button
              @click="executeStageAll().catch(() => {})"
              :disabled="isStageAllDisabled"
              title="Stage All"
              class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:cursor-not-allowed disabled:opacity-50"
            >
              Stage All
            </button>
          </div>
          <FileTable
            :files="statusStore.unstagedFiles"
            :is-loading="isTableLoading"
            @open="handleOpenFile($event)"
            @action:primary="executeStageFile($event).catch(() => {})"
            @action:secondary="handleDiscardFile($event)"
            action-primary-icon="stage"
            action-secondary-icon="discard"
          />
          <div
            v-if="statusStore.unstagedFiles.length > 0"
            class="mt-4 border-t border-theme-border pt-4"
          >
            <button
              @click="handleDiscardAll"
              :disabled="isActionInProgress"
              class="w-full rounded border border-theme-danger p-2 text-sm font-semibold text-theme-danger hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Discard All Unstaged Changes...
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer for Branch Management -->
    <div class="relative flex-shrink-0 border-t border-theme-border">
      <!-- Clickable Trigger Area -->
      <div
        @click="toggleBranchMenu"
        class="flex w-full cursor-pointer items-center justify-between px-4 py-2 hover:bg-theme-border"
        :class="{
          'cursor-not-allowed opacity-50': isBranchSwitchingDisabled,
        }"
        :title="branchSwitchingTitle"
      >
        <div class="flex items-center space-x-2 text-sm text-theme-text-muted">
          <SvgIcon type="mdi" :path="mdilSitemap" :size="16" />
          <span>{{ statusStore.branchName || "No Branch" }}</span>

          <button
            v-if="!statusStore.isTrackingUpstream"
            @click.stop="toggleUpstreamWarning"
            class="ml-2"
            title="Current branch is not tracking a remote branch. Click for details."
          >
            <SvgIcon
              type="mdi"
              :path="mdiAlertCircleOutline"
              :size="16"
              class="text-yellow-500"
            />
          </button>

          <div
            v-if="
              (statusStore.commitsBehind > 0 || statusStore.commitsAhead > 0) &&
              statusStore.isTrackingUpstream
            "
            class="flex items-center space-x-1"
          >
            <span
              v-if="statusStore.commitsBehind > 0"
              class="flex items-center"
              :title="`${statusStore.commitsBehind} commits to pull`"
            >
              <SvgIcon type="mdi" :path="mdilArrowDown" :size="14" />
              <span>{{ statusStore.commitsBehind }}</span>
            </span>
            <span
              v-if="statusStore.commitsAhead > 0"
              class="flex items-center"
              :title="`${statusStore.commitsAhead} commits to push`"
            >
              <SvgIcon type="mdi" :path="mdilArrowUp" :size="14" />
              <span>{{ statusStore.commitsAhead }}</span>
            </span>
          </div>
        </div>
        <div class="text-sm font-semibold text-theme-text-muted">
          <SvgIcon type="mdi" :path="mdilChevronUp" :size="20" />
        </div>
      </div>

      <OverlayPanel
        ref="upstreamWarningPanel"
        appendTo="body"
        :pt="{
          root: {
            class:
              'bg-theme-background-elevated border border-theme-border rounded-lg shadow-xl',
          },
          content: { class: 'p-4' },
        }"
      >
        <div class="max-w-xs text-sm">
          <h4 class="mb-2 font-semibold text-theme-text">
            Branch Not Tracking Remote
          </h4>
          <p class="text-theme-text-muted">
            Your current branch
            <code class="font-semibold">{{ statusStore.branchName }}</code> is
            not connected to a remote branch. Pull, Push, and Sync are disabled.
          </p>
          <p class="mt-3 text-xs text-theme-text-very-muted">
            To fix this, run the following command on your server: <br />
            <code class="font-mono mt-1 block rounded bg-theme-background p-1.5"
              >git push --set-upstream origin {{ statusStore.branchName }}</code
            >
          </p>
        </div>
      </OverlayPanel>

      <!-- Custom Branch Dropdown -->
      <div
        v-if="isBranchMenuVisible"
        class="absolute bottom-full mb-2 w-full p-2"
      >
        <div
          class="max-h-48 overflow-y-auto rounded-lg border border-theme-border bg-theme-background shadow-lg"
        >
          <ul>
            <li v-for="branch in branchData.branches" :key="branch.name">
              <button
                @click="handleBranchSelect(branch)"
                :disabled="branch.is_active"
                class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-60"
              >
                <SvgIcon
                  v-if="branch.is_active"
                  type="mdi"
                  :path="mdiCheck"
                  :size="16"
                  class="mr-2 text-theme-brand"
                />
                <span v-else class="mr-2 w-4"></span>
                <span>{{ branch.name }}</span>
              </button>
            </li>
            <li
              v-if="!branchData.branches || branchData.branches.length === 0"
              class="px-3 py-2 text-sm text-theme-text-muted"
            >
              No other branches found.
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import OverlayPanel from "primevue/overlaypanel";
import { useStatusStore } from "../../stores/statusStore";
import { usePanelUiStore } from "../../stores/panelUiStore";
import { useGitOperation } from "../../composables/useGitOperation";
import { useRouter } from "vue-router";
import * as gitApi from "../../gitApi";
import FileTable from "../shared/FileTable.vue";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdilSitemap,
  mdilChevronUp,
  mdilArrowUp,
  mdilArrowDown,
  mdilRefresh,
} from "@mdi/light-js";
import {
  mdiCheck,
  mdiAlertCircleOutline,
  mdiInformationOutline,
} from "@mdi/js";

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();
const router = useRouter();

const isBranchMenuVisible = ref(false);
const branchData = ref({ branches: [], current_branch: "" });
const upstreamWarningPanel = ref();

// --- Git Operation Composables ---
const { isLoading: isSyncing, execute: executeSync } = useGitOperation(
  "Commit & Sync",
  gitApi.gitSyncWorkspace,
);
const { isLoading: isPulling, execute: executePull } = useGitOperation(
  "Pull",
  gitApi.gitPull,
);
const { isLoading: isPushing, execute: executePush } = useGitOperation(
  "Push",
  gitApi.gitPush,
);
const { isLoading: isCommitting, execute: executeCommit } = useGitOperation(
  "Commit",
  gitApi.gitCommit,
);
const { isLoading: isStagingFile, execute: executeStageFile } = useGitOperation(
  "Stage File",
  gitApi.gitStageFile,
);
const { isLoading: isStagingAll, execute: executeStageAll } = useGitOperation(
  "Stage All",
  gitApi.gitAddAll,
);
const { isLoading: isUnstagingFile, execute: executeUnstageFile } =
  useGitOperation("Unstage File", gitApi.gitUnstageFile);
const { isLoading: isUnstagingAll, execute: executeUnstageAll } =
  useGitOperation("Unstage All", gitApi.gitUnstageAll);
const { isLoading: isDiscardingFile, execute: executeDiscardFile } =
  useGitOperation("Discard File", gitApi.gitDiscardFile);
const { isLoading: isDiscardingAll, execute: executeDiscardAll } =
  useGitOperation("Discard All", gitApi.gitDiscardAll);
const { isLoading: isSwitchingBranch, execute: executeSwitchBranch } =
  useGitOperation("Switch Branch", gitApi.switchBranch);

// Aggregate loading states for disabling UI elements
const isActionInProgress = computed(
  () =>
    isSyncing.value ||
    isPulling.value ||
    isPushing.value ||
    isCommitting.value ||
    isStagingFile.value ||
    isStagingAll.value ||
    isUnstagingFile.value ||
    isUnstagingAll.value ||
    isDiscardingFile.value ||
    isDiscardingAll.value ||
    isSwitchingBranch.value,
);

const isTableLoading = computed(
  () =>
    statusStore.isLoading ||
    isStagingFile.value ||
    isUnstagingFile.value ||
    isDiscardingFile.value,
);

// --- Commit Message Templating & Default ---
const defaultMessageTemplate = "chore: sync {{num}} notes at {{datetime}}";
const tooltipText =
  "Available placeholders:\n{{num}}: Number of files changed\n{{date}}: YYYY-MM-DD\n{{datetime}}: YYYY-MM-DD HH:MM:SS";

// Initialize commit message if it's empty
if (!statusStore.commitMessage.trim()) {
  statusStore.commitMessage = defaultMessageTemplate;
}

function processCommitMessage(rawMessage, num) {
  const message =
    rawMessage.trim() === "" ? defaultMessageTemplate : rawMessage;

  const now = new Date();
  const date = now.toISOString().split("T")[0];
  const time = now.toTimeString().split(" ")[0]; // HH:MM:SS
  const datetime = `${date} ${time}`;

  return message
    .replace(/{{datetime}}/g, datetime)
    .replace(/{{date}}/g, date)
    .replace(/{{num}}/g, num);
}

// --- Action Handlers ---
function handleOpenFile(path) {
  const title = path.replace(/\.md$/, "");
  router.push({
    name: "note",
    params: { title },
    query: { t: Date.now() },
  });
}

async function handleSync() {
  const num = statusStore.stagedFiles.length + statusStore.unstagedFiles.length;
  const processedMessage = processCommitMessage(statusStore.commitMessage, num);
  try {
    await executeSync(processedMessage);
    statusStore.commitMessage = defaultMessageTemplate; // Clear on success
  } catch (e) {
    // Error is handled globally by the composable
  }
}

async function handleCommitStaged() {
  const num = statusStore.stagedFiles.length;
  const processedMessage = processCommitMessage(statusStore.commitMessage, num);
  try {
    await executeCommit(processedMessage);
    statusStore.commitMessage = defaultMessageTemplate;
  } catch (e) {
    // Error is handled globally by the composable
  }
}

async function handleDiscardFile(filepath) {
  const confirmed = await panelUiStore.showConfirmation({
    title: "Confirm Discard",
    message: `Discard changes to '${filepath}'? This cannot be undone.`,
    confirmButtonText: "Discard",
  });
  if (confirmed) {
    executeDiscardFile(filepath).catch(() => {});
  }
}

async function handleDiscardAll() {
  const confirmed = await panelUiStore.showConfirmation({
    title: "Confirm Discard All",
    message: `Discard ALL unstaged changes? This will delete new files and cannot be undone.`,
    confirmButtonText: "Discard All",
  });
  if (confirmed) {
    executeDiscardAll().catch(() => {});
  }
}

// --- .gitignore Helper ---
const gitignoreFile = computed(() => {
  return statusStore.gitStatus.files.find((f) => f.path === ".gitignore");
});

const showGitignoreHelper = computed(() => {
  return gitignoreFile.value && gitignoreFile.value.work_tree_status !== " ";
});

async function stageAndPrefillCommit() {
  await executeStageFile(".gitignore").catch(() => {});
  statusStore.commitMessage = "chore: Initialize .gitignore";
}

// --- Computed Properties for Button States & Titles ---
const noStagedFiles = computed(() => statusStore.stagedFiles.length === 0);
const noUnstagedFiles = computed(() => statusStore.unstagedFiles.length === 0);
const noLocalChanges = computed(
  () => noStagedFiles.value && noUnstagedFiles.value,
);
const noCommitMessage = computed(() => statusStore.commitMessage.trim() === "");
const isNotTracking = computed(() => !statusStore.isTrackingUpstream);
const hasUncommittedChanges = computed(
  () => !noStagedFiles.value || !noUnstagedFiles.value,
);

// --- Dynamic Button Text ---
const pullButtonText = computed(() => {
  if (isPulling.value) return "Pulling...";
  return statusStore.commitsBehind > 0
    ? `Pull ${statusStore.commitsBehind}`
    : "Pull";
});

const pushButtonText = computed(() => {
  if (isPushing.value) return "Pushing...";
  return statusStore.commitsAhead > 0
    ? `Push ${statusStore.commitsAhead}`
    : "Push";
});

// --- Dynamic Button Styles ---
const pullButtonStyle = computed(() => {
  if (statusStore.commitsBehind > 0) {
    return "bg-theme-brand text-white hover:opacity-90";
  }
  return "bg-theme-background hover:bg-theme-border";
});

const pushButtonStyle = computed(() => {
  if (statusStore.commitsAhead > 0 && statusStore.commitsBehind === 0) {
    return "bg-theme-brand text-white hover:opacity-90";
  }
  return "bg-theme-background hover:bg-theme-border";
});

const syncButtonStyle = computed(() => {
  if (statusStore.commitsBehind > 0 || statusStore.commitsAhead > 0) {
    return "bg-gray-500";
  }
  return "bg-theme-brand";
});

// --- Button Disabled States & Titles ---
const isPullDisabled = computed(
  () =>
    isActionInProgress.value ||
    isNotTracking.value ||
    hasUncommittedChanges.value,
);
const pullButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  if (isNotTracking.value)
    return "Current branch is not tracking a remote branch.";
  if (hasUncommittedChanges.value)
    return "Commit or discard your local changes before pulling.";
  if (statusStore.commitsBehind === 0) return "No incoming changes to pull.";
  return `Pull ${statusStore.commitsBehind} commits from remote`;
});

const isPushDisabled = computed(
  () =>
    isActionInProgress.value ||
    isNotTracking.value ||
    statusStore.commitsAhead === 0,
);
const pushButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  if (isNotTracking.value)
    return "Current branch is not tracking a remote branch.";
  if (statusStore.commitsAhead === 0) return "No local commits to push.";
  return `Push ${statusStore.commitsAhead} commits to remote`;
});

const isCommitStagedDisabled = computed(
  () =>
    isActionInProgress.value || noStagedFiles.value || noCommitMessage.value,
);
const commitStagedButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  if (noStagedFiles.value) return "No changes staged to commit.";
  if (noCommitMessage.value) return "Enter a commit message.";
  return "Commit staged changes";
});

const isSyncDisabled = computed(
  () => isActionInProgress.value || noLocalChanges.value || isNotTracking.value,
);
const syncButtonTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  if (statusStore.commitsBehind > 0)
    return "Please pull remote changes before syncing.";
  if (statusStore.commitsAhead > 0)
    return "You have unpushed commits. Please push them or sync again.";
  if (noLocalChanges.value) return "No local changes to sync.";
  if (isNotTracking.value)
    return "Current branch is not tracking a remote branch.";
  return "Commit all changes and sync with remote";
});

const isUnstageAllDisabled = computed(
  () => isActionInProgress.value || noStagedFiles.value,
);

const isStageAllDisabled = computed(
  () => isActionInProgress.value || noUnstagedFiles.value,
);

const isBranchSwitchingDisabled = computed(() => {
  return isActionInProgress.value || hasUncommittedChanges.value;
});

const branchSwitchingTitle = computed(() => {
  if (isActionInProgress.value) return "Action in progress...";
  if (hasUncommittedChanges.value)
    return "Commit or discard your changes before switching branches.";
  return "Switch branch";
});

const toggleUpstreamWarning = (event) => {
  upstreamWarningPanel.value.toggle(event);
};

const handleBranchSelect = async (branch) => {
  if (!branch.is_active) {
    executeSwitchBranch(branch.name).catch(() => {});
  }
  isBranchMenuVisible.value = false;
};

const toggleBranchMenu = async () => {
  if (isBranchSwitchingDisabled.value) return;
  if (isBranchMenuVisible.value) {
    isBranchMenuVisible.value = false;
    return;
  }
  // No need for a separate loading state, just fetch on open.
  try {
    branchData.value = await gitApi.getBranches();
    isBranchMenuVisible.value = true;
  } catch (e) {
    // Error is handled by the global toast handler.
    console.error("Failed to fetch branches:", e);
  }
};

const handleClickOutside = (event) => {
  if (isBranchMenuVisible.value) {
    const trigger = event.target.closest(".relative");
    if (!trigger) {
      isBranchMenuVisible.value = false;
    }
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside, true);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside, true);
});
</script>

<style scoped>
.tooltip-trigger:hover::after,
.tooltip-trigger:focus::after {
  content: attr(data-tooltip);
  position: absolute;

  /* Positioning Logic */
  top: 100%;
  right: 0;
  margin-top: 4px;

  /* Styling */
  background-color: rgb(var(--theme-background-elevated));
  color: rgb(var(--theme-text));
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-line;
  text-align: left;
  z-index: 10;
  width: max-content;
  max-width: 270px;
  box-shadow:
    0 4px 6px -1px rgb(0 0 0 / 0.1),
    0 2px 4px -2px rgb(0 0 0 / 0.1);

  /* Animation */
  opacity: 1;
  pointer-events: none; /* Prevent the tooltip from interfering with mouse events */
}
</style>
