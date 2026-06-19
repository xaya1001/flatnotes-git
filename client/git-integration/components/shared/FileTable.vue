<!-- client/git-integration/components/shared/FileTable.vue -->
<template>
  <div>
    <div v-if="files.length > 0">
      <DataTable
        :value="files"
        size="small"
        :loading="isLoading"
        :tableStyle="{ 'table-layout': 'auto', width: '100%' }"
      >
        <Column field="path" header="File" style="width: 70%">
          <template #body="slotProps">
            <span class="break-all">{{ slotProps.data.path }}</span>
          </template>
        </Column>
        <Column header="Status" style="width: 10%" bodyClass="text-center">
          <template #body="slotProps">
            <span
              class="font-mono text-sm font-bold"
              :class="
                getFileStatusClass(
                  slotProps.data.index_status,
                  slotProps.data.work_tree_status,
                )
              "
              :title="getStatusLabel(statusToShow(slotProps.data))"
            >
              {{ statusToShow(slotProps.data) }}
            </span>
          </template>
        </Column>
        <Column header="Actions" style="width: 20%" bodyClass="text-right">
          <template #body="slotProps">
            <div class="flex items-center justify-end space-x-1">
              <button
                v-if="slotProps.data.path.endsWith('.md')"
                @click="$emit('open', slotProps.data.path)"
                class="p-1 text-theme-text-muted hover:text-theme-text"
                title="Open File"
              >
                <SvgIcon type="mdi" :path="mdilFile" :size="16" />
              </button>
              <button
                v-if="actionPrimaryIcon"
                @click="$emit('action:primary', slotProps.data.path)"
                class="p-1 text-theme-text-muted hover:text-theme-text"
                :title="primaryActionTitle"
              >
                <SvgIcon type="mdi" :path="primaryActionIconPath" :size="18" />
              </button>
              <button
                v-if="actionSecondaryIcon"
                @click="$emit('action:secondary', slotProps.data.path)"
                class="p-1 text-theme-danger hover:opacity-75"
                :title="secondaryActionTitle"
              >
                <SvgIcon type="mdi" :path="mdiClose" :size="16" />
              </button>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
    <p v-else class="py-4 text-center text-sm text-theme-text-muted">
      No changes.
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilFile, mdilPlus, mdilMinus } from "@mdi/light-js";
import { mdiClose } from "@mdi/js";
import { getStatusLabel, getFileStatusClass } from "../../gitUtils";

const props = defineProps({
  files: Array,
  isLoading: Boolean,
  actionPrimaryIcon: { type: String, default: null },
  actionSecondaryIcon: { type: String, default: null },
});

defineEmits(["open", "action:primary", "action:secondary"]);

// This function determines which status character to display.
// For unstaged changes (action is 'stage'), we MUST show work_tree_status.
// For staged changes (action is 'unstage'), we MUST show index_status.
const statusToShow = (file) => {
  if (props.actionPrimaryIcon === "stage") {
    // This is the 'Changes' (unstaged) table
    return file.work_tree_status;
  }
  if (props.actionPrimaryIcon === "unstage") {
    // This is the 'Staged Changes' table
    return file.index_status;
  }
  // Fallback for any other case
  return file.work_tree_status || file.index_status;
};

const primaryActionIconPath = computed(() => {
  if (props.actionPrimaryIcon === "stage") return mdilPlus;
  if (props.actionPrimaryIcon === "unstage") return mdilMinus;
  return null;
});

const primaryActionTitle = computed(() => {
  if (props.actionPrimaryIcon === "stage") return "Stage";
  if (props.actionPrimaryIcon === "unstage") return "Unstage";
  return "";
});

const secondaryActionTitle = computed(() => {
  if (props.actionSecondaryIcon === "discard") return "Discard Changes";
  return "";
});
</script>
