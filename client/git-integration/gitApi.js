// client/git-integration/gitApi.js
import { api } from "../api.js";

// --- BEGIN GIT INTEGRATION API CALLS ---
export async function getGitStatus() {
  try {
    const response = await api.get("api/git/status");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitAddAll() {
  try {
    const response = await api.post("api/git/add_all");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitUnstageAll() {
  try {
    const response = await api.post("api/git/unstage_all");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitCommit(message) {
  try {
    const response = await api.post("api/git/commit", { message });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function getGitLog(limit = 10, page = 1) {
  try {
    const response = await api.get("api/git/log", {
      params: { limit, page },
    });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitPull(params = {}) {
  try {
    const response = await api.post("api/git/pull", null, { params });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitPush(params = {}) {
  try {
    const response = await api.post("api/git/push", null, { params });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitStageFile(filepath) {
  try {
    const response = await api.post("api/git/stage_file", { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitUnstageFile(filepath) {
  try {
    const response = await api.post("api/git/unstage_file", { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitDiscardFile(filepath) {
  try {
    const response = await api.post("api/git/discard_file", { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitDiscardAll() {
  try {
    const response = await api.post("api/git/discard_all");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function getGitStatusSummary() {
  try {
    const response = await api.get("api/git/status-summary");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function gitSyncWorkspace(message) {
  try {
    const response = await api.post("api/git/sync", { message });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function getAutoSyncState() {
  try {
    const response = await api.get("api/git/auto-sync/state");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function pauseAutoSync() {
  try {
    const response = await api.post("api/git/auto-sync/pause");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function resumeAutoSync() {
  try {
    const response = await api.post("api/git/auto-sync/resume");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function getGitActivityLog() {
  try {
    const response = await api.get("api/git/activity-log");
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
export async function getGitCommitFiles(commitHash) {
  try {
    const response = await api.get(`api/git/commits/${commitHash}/files`);
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
// --- END GIT INTEGRATION API CALLS ---
