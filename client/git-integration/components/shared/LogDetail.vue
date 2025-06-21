<!-- client/git-integration/components/shared/LogDetail.vue -->
<template>
  <div
    v-if="details"
    class="mt-1 overflow-hidden whitespace-pre-wrap rounded-md bg-theme-background p-2 text-xs"
  >
    <!-- Commit Details -->
    <div
      v-if="commitData"
      class="mb-2 border-b border-theme-border/50 pb-2 last:mb-0 last:border-b-0 last:pb-0"
    >
      <h5 class="mb-1 font-semibold text-theme-text-muted">Commit</h5>
      <p v-if="commitData.hash">
        <span class="font-semibold">Hash:</span>
        <span class="font-mono text-blue-400">{{
          commitData.hash.substring(0, 7)
        }}</span>
      </p>
      <p v-if="commitData.message">
        <span class="font-semibold">Message:</span>
        "{{ commitData.message }}"
      </p>
      <div
        v-if="commitData.files_changed && commitData.files_changed.length > 0"
        class="mt-1"
      >
        <p class="font-semibold">
          Files ({{ commitData.files_changed.length }}):
        </p>
        <ul class="ml-2">
          <li
            v-for="file in commitData.files_changed"
            :key="file.path"
            class="flex items-center"
          >
            <span
              class="mr-2 w-4 text-center font-bold"
              :class="getCommitFileStatusClass(file.status)"
              >{{ file.status }}</span
            >
            <span>{{ file.path }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Pull Details -->
    <div
      v-if="pullData"
      class="mb-2 border-b border-theme-border/50 pb-2 last:mb-0 last:border-b-0 last:pb-0"
    >
      <h5 class="mb-1 font-semibold text-theme-text-muted">Pull</h5>
      <p>
        <span class="font-semibold">Commits Received:</span>
        {{ pullData.commits_received || 0 }}
      </p>
      <div
        v-if="pullData.files_updated && pullData.files_updated.length > 0"
        class="mt-1"
      >
        <p class="font-semibold">
          Files Updated ({{ pullData.files_updated.length }}):
        </p>
        <ul class="ml-2">
          <li
            v-for="file in pullData.files_updated"
            :key="file.path"
            class="flex items-center"
          >
            <span
              class="mr-2 w-4 text-center font-bold"
              :class="getCommitFileStatusClass(file.status)"
              >{{ file.status }}</span
            >
            <span>{{ file.path }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Push Details -->
    <div
      v-if="pushData"
      class="mb-2 border-b border-theme-border/50 pb-2 last:mb-0 last:border-b-0 last:pb-0"
    >
      <h5 class="mb-1 font-semibold text-theme-text-muted">Push</h5>
      <p>
        <span class="font-semibold">Commits Pushed:</span>
        {{ pushData.commits_pushed || 0 }}
      </p>
      <div
        v-if="pushData.files_changed && pushData.files_changed.length > 0"
        class="mt-1"
      >
        <p class="font-semibold">
          Files Changed ({{ pushData.files_changed.length }}):
        </p>
        <ul class="ml-2">
          <li
            v-for="file in pushData.files_changed"
            :key="file.path"
            class="flex items-center"
          >
            <span
              class="mr-2 w-4 text-center font-bold"
              :class="getCommitFileStatusClass(file.status)"
              >{{ file.status }}</span
            >
            <span>{{ file.path }}</span>
          </li>
        </ul>
      </div>
      <div v-if="pushData.commits && pushData.commits.length > 0" class="mt-1">
        <p class="font-semibold">Commits:</p>
        <ul class="ml-2">
          <li v-for="commit in pushData.commits" :key="commit.hash">
            <span class="font-mono text-blue-400">{{
              commit.hash.substring(0, 7)
            }}</span>
            - "{{ commit.message }}"
          </li>
        </ul>
      </div>
    </div>

    <!-- Generic Details (Fallback for simple strings or other objects) -->
    <pre
      v-if="isFallback"
      class="overflow-hidden whitespace-pre-wrap rounded-md bg-theme-background p-2 text-xs"
      >{{ details }}</pre
    >
  </div>
</template>

<script setup>
import { computed } from "vue";
import { getCommitFileStatusClass } from "../../gitUtils";

const props = defineProps({
  details: [Object, String],
});

// Computed properties to find the relevant data, whether it's nested or not.
const commitData = computed(() => {
  if (!props.details || typeof props.details !== "object") return null;
  return props.details.commit || (props.details.hash ? props.details : null);
});

const pullData = computed(() => {
  if (!props.details || typeof props.details !== "object") return null;
  return (
    props.details.pull ||
    (props.details.hasOwnProperty("commits_received") ? props.details : null)
  );
});

const pushData = computed(() => {
  if (!props.details || typeof props.details !== "object") return null;
  return (
    props.details.push ||
    (props.details.hasOwnProperty("commits_pushed") ? props.details : null)
  );
});

const isFallback = computed(() => {
  if (typeof props.details === "string") {
    return true;
  }
  if (typeof props.details === "object" && props.details !== null) {
    // Show fallback if it's not a known structured object
    return !commitData.value && !pullData.value && !pushData.value;
  }
  return false;
});
</script>
