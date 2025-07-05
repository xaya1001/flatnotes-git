<template>
  <!-- Confirm Deletion Modal -->
  <ConfirmModal
    v-model="isDeleteModalVisible"
    title="Confirm Deletion"
    :message="`Are you sure you want to delete the note '${note.title}'?`"
    confirmButtonText="Delete"
    confirmButtonStyle="danger"
    @confirm="deleteConfirmedHandler"
  />

  <!-- Save Changes Modal -->
  <ConfirmModal
    v-model="isSaveChangesModalVisible"
    title="Save Changes"
    message="Do you want to save your changes?"
    confirmButtonText="Save"
    confirmButtonStyle="success"
    rejectButtonText="Discard"
    rejectButtonStyle="danger"
    @confirm="saveHandler((close = true))"
    @reject="closeNote"
  />

  <!-- Draft Modal -->
  <ConfirmModal
    v-model="isDraftModalVisible"
    title="Draft Detected"
    message="There is an unsaved draft of this note stored in this browser. Do you want to resume the draft version or delete it?"
    confirmButtonText="Resume Draft"
    confirmButtonStyle="cta"
    rejectButtonText="Delete Draft"
    rejectButtonStyle="danger"
    @confirm="setEditMode()"
    @reject="
      clearDraft();
      setEditMode();
    "
  />

  <LoadingIndicator ref="loadingIndicator">
    <!-- Header -->
    <div
      class="fixed left-0 right-0 top-20 z-10 h-16 border-b border-theme-border bg-theme-background"
    >
      <div class="container mx-auto flex h-full items-center px-2">
        <!-- Title -->
        <div class="grow truncate text-3xl leading-[1.6em]">
          <span v-show="!editMode" :title="note.title">{{ note.title }}</span>
          <input
            v-show="editMode"
            v-model.trim="newTitle"
            class="w-full bg-theme-background outline-none"
            placeholder="Title"
          />
        </div>

        <!-- Buttons -->
        <div class="flex shrink-0 self-center print:hidden">
          <!-- Delete Button -->
          <CustomButton
            v-show="canModify && !isNewNote"
            label="Delete"
            :iconPath="mdilDelete"
            @click="deleteHandler"
          />
          <!-- Save Button -->
          <CustomButton
            v-show="editMode"
            label="Save"
            :iconPath="mdilContentSave"
            @click="saveHandler((close = false))"
            class="relative ml-1"
          >
            <!-- Unsaved Changes Indicator -->
            <div
              v-show="unsavedChanges"
              class="absolute right-1 h-1.5 w-1.5 rounded-full bg-theme-brand"
            ></div>
          </CustomButton>
          <!-- Edit Toggle -->
          <Toggle
            v-if="canModify"
            label="Edit"
            :isOn="editMode"
            class="ml-1"
            @click="toggleEditModeHandler"
          />
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="pt-36">
      <MilkdownProvider>
        <div class="px-1 pt-4">
          <MilkdownViewer
            v-if="!editMode && note.content !== undefined"
            :key="note.title"
            :initialValue="note.content || ''"
            class="pb-4"
          />
          <MilkdownEditor
            v-if="editMode"
            ref="milkdownEditor"
            :key="`editor-${note.title}`"
            :initialValue="getInitialEditorValue()"
            :addImageBlobHook="addImageBlobHook"
            @change="startContentChangedTimeout"
            @keydown="keydownHandler"
          />
        </div>
      </MilkdownProvider>
    </div>
  </LoadingIndicator>
</template>

<script setup>
import { mdiNoteOffOutline } from "@mdi/js";
import { mdilContentSave, mdilDelete } from "@mdi/light-js";
import Mousetrap from "mousetrap";
import { useToast } from "primevue/usetoast";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Compressor from "compressorjs";

import {
  apiErrorHandler,
  createAttachment,
  createNote,
  deleteNote,
  getNote,
  updateNote,
} from "../api.js";
import { Note } from "../classes.js";
import ConfirmModal from "../components/ConfirmModal.vue";
import CustomButton from "../components/CustomButton.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import Toggle from "../components/Toggle.vue";
import { MilkdownProvider } from "@milkdown/vue";
import MilkdownEditor from "../components/milkdown/MilkdownEditor.vue";
import MilkdownViewer from "../components/milkdown/MilkdownViewer.vue";

import { authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { getToastOptions } from "../helpers.js";
import eventBus from "../git-integration/services/eventBus";

const props = defineProps({
  title: String,
});

const canModify = computed(
  () => globalStore.config.value.authType != authTypes.readOnly,
);
let contentChangedTimeout = null;
const editMode = ref(false);
const globalStore = useGlobalStore();
const isSaveChangesModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const isDraftModalVisible = ref(false);
const isNewNote = computed(() => !props.title);
const loadingIndicator = ref();
const note = ref({});
const reservedFilenameCharacters = /[<>:"/\\|?*]/;
const router = useRouter();
const newTitle = ref();
const toast = useToast();
const milkdownEditor = ref(null);
const unsavedChanges = ref(false);

function init() {
  // Return if we already have the note e.g. When we rename a note, the route prop would change but we’d already have the note.
  if (props.title && props.title == note.value.title) {
    return;
  }

  loadingIndicator.value.setLoading();
  if (props.title) {
    getNote(props.title)
      .then((data) => {
        note.value = data;
        loadingIndicator.value.setLoaded();
      })
      .catch((error) => {
        if (error.response?.status === 404) {
          loadingIndicator.value.setFailed("Note not found", mdiNoteOffOutline);
        } else {
          loadingIndicator.value.setFailed();
          apiErrorHandler(error, toast);
        }
        console.error("Note.vue: Failed to load note.", error);
      });
  } else {
    newTitle.value = "";
    note.value = new Note({ content: "" });
    editMode.value = false;
    nextTick(() => {
      editHandler();
      loadingIndicator.value.setLoaded();
    });
  }
}

// Note Editing
function toggleEditModeHandler() {
  if (editMode.value) {
    closeHandler();
  } else {
    editHandler();
  }
}

function editHandler() {
  const draftContent = loadDraft();
  if (draftContent) {
    isDraftModalVisible.value = true;
  } else {
    setEditMode();
  }
}

function setEditMode() {
  newTitle.value = note.value.title;
  unsavedChanges.value = false;
  editMode.value = true;
}

function getInitialEditorValue() {
  const draftContent = loadDraft();
  const initialValue = draftContent ? draftContent : note.value.content;

  return initialValue;
}

// Note Deletion
function deleteHandler() {
  isDeleteModalVisible.value = true;
}

function deleteConfirmedHandler() {
  deleteNote(note.value.title)
    .then(() => {
      toast.add(getToastOptions("Note deleted ✓", "Success", "success"));
      eventBus.emit("note:deleted", { title: note.value.title });
      router.push({ name: "home" });
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
    });
}

// Note Saving
function saveHandler(close = false) {
  // Empty Title Validation
  if (!newTitle.value) {
    toast.add(
      getToastOptions("Cannot save note without a title.", "Invalid", "error"),
    );
    return;
  }

  // Invalid Character Validation
  if (reservedFilenameCharacters.test(newTitle.value)) {
    badFilenameToast("Title");
    return;
  }
  if (!milkdownEditor.value) {
    console.error(
      "Note.vue: Save handler called but editor ref is not available.",
    );
    return;
  }
  // Save Note
  let newContent = milkdownEditor.value.getMarkdown();
  if (isNewNote.value) {
    saveNew(newTitle.value, newContent, close);
  } else {
    saveExisting(newTitle.value, newContent, close);
  }
}

function saveNew(newTitle, newContent, close = false) {
  createNote(newTitle, newContent)
    .then((data) => {
      clearDraft();
      note.value = data;
      router
        .push({
          name: "note",
          params: { title: note.value.title },
        })
        .then(() => {
          // Wait for the route to be updated before setting edit mode to false
          // as the route is used to determine the action.
          noteSaveSuccess(close);
        });
    })
    .catch(noteSaveFailure);
}

function saveExisting(newTitle, newContent, close = false) {
  // Return if no changes
  const titleChanged = newTitle !== note.value.title;
  const contentChanged = newContent !== note.value.content;
  if (!titleChanged && !contentChanged) {
    noteSaveSuccess(close);
    return;
  }

  updateNote(note.value.title, newTitle, newContent)
    .then((data) => {
      clearDraft();
      note.value = data;
      if (titleChanged) {
        router.replace({ name: "note", params: { title: note.value.title } });
      } else {
      }
      noteSaveSuccess(close);
    })
    .catch(noteSaveFailure);
}

function noteSaveFailure(error) {
  console.error("Note.vue: Note save failed.", error);
  if (error.response?.status === 409) {
    toast.add(
      getToastOptions(
        "A note with this title already exists. Please try again with a new title.",
        "Duplicate",
        "error",
      ),
    );
  } else if (error.response?.status === 413) {
    entityTooLargeToast("note");
  } else {
    apiErrorHandler(error, toast);
  }
}

function noteSaveSuccess(close = false) {
  unsavedChanges.value = false;
  if (close) {
    closeNote();
  }
  setBeforeUnloadConfirmation(false);
  toast.add(getToastOptions("Note saved successfully ✓", "Success", "success"));
  eventBus.emit("note:saved", { title: note.value.title });
}

// Note Closure
function closeHandler() {
  if (isContentChanged()) {
    isSaveChangesModalVisible.value = true;
  } else {
    closeNote();
  }
}

function closeNote() {
  clearDraft();
  editMode.value = false;
  if (isNewNote.value) {
    router.push({ name: "home" });
  }
}

// Image Upload
function uploadAndInsert(fileToUpload, callback) {
  // Upload the image then use the callback to insert the URL into the editor
  postAttachment(fileToUpload).then(function (data) {
    if (data) {
      callback(data.url, data.filename);
    }
  });
}

function postAttachment(fileToUpload) {
  if (!fileToUpload) {
    toast.add(
      getToastOptions("No file provided for upload.", "Error", "error"),
    );
    return Promise.reject("No file provided");
  }

  // Invalid Character Validation
  if (reservedFilenameCharacters.test(fileToUpload.name)) {
    badFilenameToast("Filename");
    return Promise.reject("Invalid filename");
  }

  // Uploading Toast
  toast.add(getToastOptions("Uploading attachment..."));

  // Upload the attachment
  return createAttachment(fileToUpload)
    .then((data) => {
      // Success Toast
      toast.add(
        getToastOptions(
          "Attachment uploaded successfully ✓",
          "Success",
          "success",
        ),
      );
      return data;
    })
    .catch((error) => {
      if (error.response?.status === 409) {
        // Note: The current implementation will append a datetime to the filename if it already exists.
        // Error Toast
        toast.add(
          getToastOptions(
            "An attachment with this filename already exists.",
            "Duplicate",
            "error",
          ),
        );
      } else if (error.response?.status == 413) {
        entityTooLargeToast("attachment");
      } else {
        console.error("Attachment upload error:", error);
        toast.add(
          getToastOptions(
            error.response?.data?.detail || "Failed to upload attachment.",
            "Upload Error",
            "error",
          ),
        );
      }
      return Promise.reject(error);
    });
}

function addImageBlobHook(file, callback) {
  if (!file) return;

  const config = globalStore.config.value;

  if (config && config.frontendImageCompressionEnabled) {
    const options = {
      quality: config.frontendImageCompressionQuality,
      maxWidth: config.frontendImageMaxWidth,
      mimeType: file.type,
      success(compressedResult) {
        toast.add(
          getToastOptions(
            `Image compressed: ${Math.round(file.size / 1024)}KB -> ${Math.round(compressedResult.size / 1024)}KB`,
            "Info",
            "info",
          ),
        );
        uploadAndInsert(compressedResult, callback);
      },
      error(err) {
        console.error("Image compression failed:", err.message);
        toast.add(
          getToastOptions(
            "Image compression failed, uploading original file.",
            "Warning",
            "warn",
          ),
        );
        uploadAndInsert(file, callback);
      },
    };
    new Compressor(file, options);
  } else {
    uploadAndInsert(file, callback);
  }
}

// Content Change Watcher
function startContentChangedTimeout() {
  clearContentChangedTimeout();
  contentChangedTimeout = setTimeout(contentChangedHandler, 1000);
}

function clearContentChangedTimeout() {
  if (contentChangedTimeout != null) {
    clearTimeout(contentChangedTimeout);
  }
}

function contentChangedHandler() {
  if (isContentChanged()) {
    unsavedChanges.value = true;
    setBeforeUnloadConfirmation(true);
    saveDraft();
  } else {
    unsavedChanges.value = false;
    setBeforeUnloadConfirmation(false);
    clearDraft();
  }
}

// Drafts
function saveDraft() {
  if (milkdownEditor.value) {
    const content = milkdownEditor.value.getMarkdown();
    if (content) {
      localStorage.setItem(note.value.title, content);
    }
  }
}

function clearDraft() {
  localStorage.removeItem(note.value.title);
}

function loadDraft() {
  return localStorage.getItem(note.value.title);
}

// Keyboard Shortcuts
// 'e' to edit
Mousetrap.bind("e", () => {
  if (editMode.value === false && canModify.value) {
    editHandler();
  }
});

function keydownHandler(event) {
  // Ctrl + Enter to save
  if ((event.ctrlKey || event.metaKey) && event.key == "Enter") {
    saveHandler((close = false));
  }
  // Escape to exit edit mode
  if (event.key == "Escape") {
    closeHandler();
  }
}

// Helpers
function entityTooLargeToast(entityName) {
  toast.add(
    getToastOptions(
      `This ${entityName} is too large. Please try again with a smaller ${entityName} or adjust your server configuration.`,
      "Failure",
      "error",
    ),
  );
}

function badFilenameToast(entityName) {
  toast.add(
    getToastOptions(
      'Due to filename restrictions, the following characters are not allowed: <>:"/\\|?*',
      `Invalid ${entityName}`,
      "error",
    ),
  );
}

function setBeforeUnloadConfirmation(enable = true) {
  if (enable) {
    window.onbeforeunload = () => {
      return true;
    };
  } else {
    window.onbeforeunload = null;
  }
}
function isContentChanged() {
  if (!milkdownEditor.value) return false;
  return (
    newTitle.value != note.value.title ||
    milkdownEditor.value.getMarkdown() != note.value.content
  );
}

watch(() => props.title, init);
onMounted(() => {
  init();
});
</script>
