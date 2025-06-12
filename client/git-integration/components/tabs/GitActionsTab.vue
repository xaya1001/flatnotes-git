<!-- client/git-integration/components/tabs/GitActionsTab.vue -->
<template>
  <div class="flex h-full flex-col p-4">
    <div class="min-h-0 flex-grow overflow-y-auto">
      <!-- Standard Actions -->
      <div class="grid grid-cols-2 gap-3">
        <button
          @click="actionsStore.handlePull"
          :disabled="actionsStore.isActionLoading"
          class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:opacity-50"
        >
          Pull
        </button>
        <button
          @click="actionsStore.handlePush"
          :disabled="actionsStore.isActionLoading"
          class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:opacity-50"
        >
          Push
        </button>
      </div>
      <hr class="my-4 border-theme-border" />
      <!-- Automation Status -->
      <div>
        <h4 class="mb-2 text-sm font-semibold">Automation Status</h4>
        <div
          class="rounded-md bg-theme-background p-3 text-sm text-theme-text-muted"
        >
          <div class="flex items-center justify-between">
            <span>Automatic Sync</span>
            <Toggle
              v-if="globalConfig.flatnotesGitAutoSyncInterval > 0"
              :isOn="!actionsStore.isAutoSyncPaused"
              :label="actionsStore.isAutoSyncPaused ? 'Paused' : 'Enabled'"
              @click="actionsStore.toggleAutoSyncPause"
              :disabled="actionsStore.isActionLoading"
            />
            <span
              v-else
              class="rounded-full bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-800 dark:bg-gray-700 dark:text-gray-300"
              >Disabled</span
            >
          </div>
          <div
            v-if="globalConfig.flatnotesGitAutoSyncInterval > 0"
            class="mt-2 text-xs"
          >
            Syncs automatically every
            <strong>{{ globalConfig.flatnotesGitAutoSyncInterval }}</strong>
            minutes.
            <span
              v-if="actionsStore.isAutoSyncPaused"
              class="font-semibold text-yellow-600 dark:text-yellow-400"
              >(Currently Paused)</span
            >
          </div>
          <div v-else class="mt-2 text-xs">
            Set
            <code class="text-xs">FLATNOTES_GIT_AUTO_SYNC_INTERVAL</code> to
            enable.
          </div>
        </div>
      </div>
      <hr class="my-4 border-theme-border" />
      <!-- Danger Zone -->
      <div>
        <h4 class="mb-1 text-sm font-semibold text-theme-danger">
          Danger Zone
        </h4>
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
</template>
<script setup>
import { computed } from "vue";
import Toggle from "../../../components/Toggle.vue";
import { useActionsStore } from "../../stores/actionsStore";
import { useStatusStore } from "../../stores/statusStore";
import { useGlobalStore } from "../../../globalStore";

const actionsStore = useActionsStore();
const statusStore = useStatusStore();
const globalStore = useGlobalStore();
const globalConfig = computed(() => globalStore.config.value);
</script>
