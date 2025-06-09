<template>
  <div class="flex h-full flex-col p-2">
    <!-- Commit & Sync Area (Fixed Size) -->
    <div class="mb-4 flex-shrink-0">
      <textarea
        v-model="store.commitMessage"
        placeholder="Commit Message"
        rows="3"
        class="w-full rounded border bg-theme-background p-2 text-sm focus:border-theme-brand focus:ring-theme-brand"
      ></textarea>
      <div class="mt-1 flex space-x-2">
        <button
          @click="store.handleCommit"
          :disabled="
            store.isActionLoading ||
            store.stagedFiles.length === 0 ||
            !store.commitMessage.trim()
          "
          class="w-1/2 rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
        >
          Commit Staged
        </button>
        <button
          @click="store.handleSync"
          :disabled="
            store.isActionLoading ||
            (store.stagedFiles.length === 0 && store.unstagedFiles.length === 0)
          "
          class="w-1/2 rounded bg-theme-brand p-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Commit & Sync
        </button>
      </div>
    </div>

    <!-- Scrollable content area -->
    <div class="min-h-0 flex-grow overflow-y-auto">
      <!-- Staged Files -->
      <div class="mb-4">
        <div class="mb-2 ml-1 flex items-center justify-between">
          <h3 class="text-sm font-semibold">
            Staged Changes ({{ store.stagedFiles.length }})
          </h3>
          <button
            @click="store.handleUnstageAll"
            :disabled="store.isActionLoading || store.stagedFiles.length === 0"
            class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
          >
            Unstage All
          </button>
        </div>
        <div v-if="store.stagedFiles.length > 0">
          <DataTable
            :value="store.stagedFiles"
            size="small"
            :loading="store.isActionLoading"
            :tableStyle="{ 'table-layout': 'fixed', width: '100%' }"
          >
            <Column
              field="path"
              header="File"
              style="width: 60%"
              bodyStyle="word-break: break-all;"
            ></Column>
            <Column header="Status" style="width: 20%">
              <template #body="slotProps">
                <span
                  class="rounded-full p-1 px-2 text-xs font-medium"
                  :class="getFileStatusClass(slotProps.data.index_status, '')"
                >
                  {{ getStatusLabel(slotProps.data.index_status) }}
                </span>
              </template>
            </Column>
            <Column header="Actions" style="width: 20%" bodyClass="text-center">
              <template #body="slotProps">
                <div class="flex items-center justify-center space-x-2">
                  <button
                    v-if="slotProps.data.path.endsWith('.md')"
                    @click="store.openNoteInEditor(slotProps.data.path)"
                    class="p-1 text-theme-text-muted hover:text-theme-text"
                    title="Open File"
                  >
                    <SvgIcon type="mdi" :path="mdilFile" :size="16" />
                  </button>
                  <button
                    @click="store.handleUnstageFile(slotProps.data.path)"
                    :disabled="store.isActionLoading"
                    class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text"
                    title="Unstage"
                  >
                    −
                  </button>
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
        <p v-else class="py-4 text-center text-sm text-theme-text-muted">
          No staged changes.
        </p>
      </div>

      <!-- Unstaged Files -->
      <div>
        <div class="mb-2 ml-1 flex items-center justify-between">
          <h3 class="text-sm font-semibold">
            Changes ({{ store.unstagedFiles.length }})
          </h3>
          <button
            @click="store.handleStageAll"
            :disabled="
              store.isActionLoading || store.unstagedFiles.length === 0
            "
            class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
          >
            Stage All
          </button>
        </div>
        <div v-if="store.unstagedFiles.length > 0">
          <DataTable
            :value="store.unstagedFiles"
            size="small"
            :loading="store.isActionLoading"
            :tableStyle="{ 'table-layout': 'fixed', width: '100%' }"
          >
            <Column
              field="path"
              header="File"
              style="width: 60%"
              bodyStyle="word-break: break-all;"
            ></Column>
            <Column header="Status" style="width: 20%">
              <template #body="slotProps">
                <span
                  class="rounded-full p-1 px-2 text-xs font-medium"
                  :class="
                    getFileStatusClass('', slotProps.data.work_tree_status)
                  "
                >
                  {{ getStatusLabel(slotProps.data.work_tree_status) }}
                </span>
              </template>
            </Column>
            <Column header="Actions" style="width: 20%" bodyClass="text-center">
              <template #body="slotProps">
                <div class="flex items-center justify-center space-x-2">
                  <button
                    v-if="slotProps.data.path.endsWith('.md')"
                    @click="store.openNoteInEditor(slotProps.data.path)"
                    class="p-1 text-theme-text-muted hover:text-theme-text"
                    title="Open File"
                  >
                    <SvgIcon type="mdi" :path="mdilFile" :size="16" />
                  </button>
                  <button
                    @click="store.handleStageFile(slotProps.data.path)"
                    :disabled="store.isActionLoading"
                    class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text"
                    title="Stage"
                  >
                    +
                  </button>
                  <button
                    @click="store.handleDiscardFile(slotProps.data.path)"
                    :disabled="store.isActionLoading"
                    class="p-1"
                    title="Discard Changes"
                  >
                    <SvgIcon
                      type="mdi"
                      :path="mdiClose"
                      :size="16"
                      class="text-theme-danger"
                    />
                  </button>
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
        <p v-else class="py-4 text-center text-sm text-theme-text-muted">
          No unstaged changes.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilFile } from "@mdi/light-js";
import { mdiClose } from "@mdi/js";
import { useGitStore } from "../../gitStore";
import { getStatusLabel, getFileStatusClass } from "../../gitUtils";

const store = useGitStore();
</script>
