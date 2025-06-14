<!-- client/git-integration/components/tabs/WorkspaceTab.vue -->
<template>
  <div class="flex h-full flex-col">
    <!-- Main Content Area (Scrollable) -->
    <div class="min-h-0 flex-grow overflow-y-auto p-2">
      <!-- Commit & Sync Area -->
      <div class="mb-4 flex-shrink-0 px-2">
        <textarea
          v-model="statusStore.commitMessage"
          placeholder="Commit Message (use {{date}} and {{numFiles}})"
          rows="3"
          class="w-full rounded border bg-theme-background p-2 text-sm focus:border-theme-brand focus:ring-theme-brand"
        ></textarea>
        <!-- Action Buttons Grid -->
        <div class="mt-2 grid grid-cols-2 gap-2">
          <!-- Row 1: Network Actions -->
          <button
            @click="actionsStore.handlePull"
            :disabled="actionsStore.isActionLoading"
            class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
          >
            Pull
          </button>
          <button
            @click="actionsStore.handlePush"
            :disabled="actionsStore.isActionLoading"
            class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
          >
            Push
          </button>

          <!-- Row 2: Commit Actions -->
          <button
            @click="actionsStore.handleCommit"
            :disabled="
              actionsStore.isActionLoading ||
              statusStore.stagedFiles.length === 0 ||
              !statusStore.commitMessage.trim()
            "
            class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
          >
            Commit Staged
          </button>
          <button
            @click="actionsStore.handleSync"
            :disabled="
              actionsStore.isActionLoading ||
              (statusStore.stagedFiles.length === 0 &&
                statusStore.unstagedFiles.length === 0)
            "
            class="rounded bg-theme-brand p-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Commit & Sync
          </button>
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
              @click="actionsStore.handleUnstageAll"
              :disabled="
                actionsStore.isActionLoading ||
                statusStore.stagedFiles.length === 0
              "
              class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
            >
              Unstage All
            </button>
          </div>
          <FileTable
            :files="statusStore.stagedFiles"
            :is-loading="statusStore.isLoading"
            @open="statusStore.openNoteInEditor($event)"
            @action:primary="actionsStore.handleUnstageFile($event)"
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
              @click="actionsStore.handleStageAll"
              :disabled="
                actionsStore.isActionLoading ||
                statusStore.unstagedFiles.length === 0
              "
              class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
            >
              Stage All
            </button>
          </div>
          <FileTable
            :files="statusStore.unstagedFiles"
            :is-loading="statusStore.isLoading"
            @open="statusStore.openNoteInEditor($event)"
            @action:primary="actionsStore.handleStageFile($event)"
            @action:secondary="actionsStore.handleDiscardFile($event)"
            action-primary-icon="stage"
            action-secondary-icon="discard"
          />
          <div
            v-if="statusStore.unstagedFiles.length > 0"
            class="mt-4 border-t border-theme-border pt-4"
          >
            <button
              @click="actionsStore.handleDiscardAll"
              :disabled="
                actionsStore.isActionLoading ||
                statusStore.unstagedFiles.length === 0
              "
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
          'cursor-not-allowed opacity-50': actionsStore.isActionLoading,
        }"
      >
        <div class="flex items-center space-x-2 text-sm text-theme-text-muted">
          <SvgIcon type="mdi" :path="mdilSitemap" :size="16" />
          <span>{{ statusStore.branchName || "No Branch" }}</span>
        </div>
        <div class="text-sm font-semibold text-theme-text-muted">
          <SvgIcon type="mdi" :path="mdilChevronUp" :size="20" />
        </div>
      </div>

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
import { ref, onMounted, onUnmounted } from "vue";
import { useStatusStore } from "../../stores/statusStore";
import { useActionsStore } from "../../stores/actionsStore";
import FileTable from "../shared/FileTable.vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilSitemap, mdilChevronUp } from "@mdi/light-js";
import { mdiCheck } from "@mdi/js";

const statusStore = useStatusStore();
const actionsStore = useActionsStore();

const isBranchMenuVisible = ref(false);
const branchData = ref({ branches: [], current_branch: "" });

const handleBranchSelect = (branch) => {
  if (!branch.is_active) {
    actionsStore.switchBranch(branch.name);
  }
  isBranchMenuVisible.value = false;
};

const toggleBranchMenu = async () => {
  if (actionsStore.isActionLoading) return;

  if (isBranchMenuVisible.value) {
    isBranchMenuVisible.value = false;
    return;
  }

  branchData.value = await actionsStore.getBranches();
  isBranchMenuVisible.value = true;
};

// Click-away to close menu
const handleClickOutside = (event) => {
  if (isBranchMenuVisible.value) {
    // A simple check to see if the click was inside this component.
    // This could be made more robust with a ref on the component root.
    if (!event.target.closest(".relative")) {
      isBranchMenuVisible.value = false;
    }
  }
};

onMounted(() => {
  window.addEventListener("click", handleClickOutside, true);
});

onUnmounted(() => {
  window.removeEventListener("click", handleClickOutside, true);
});
</script>
