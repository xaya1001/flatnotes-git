import * as constants from './constants.js';

import { Note, SearchResult } from './classes.js';

import axios from 'axios';
import { getStoredToken } from './tokenStorage.js';
import { getToastOptions } from './helpers.js';
import router from './router.js';

const api = axios.create();

api.interceptors.request.use(
  // If the request is not for the token endpoint, add the token to the headers.
  function (config) {
    if (config.url !== 'api/token') {
      const token = getStoredToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  function (error) {
    return Promise.reject(error);
  }
);

export function apiErrorHandler(error, toast) {
  if (error.response?.status === 401) {
    const redirectPath = router.currentRoute.value.fullPath;
    router.push({
      name: 'login',
      query: { [constants.params.redirect]: redirectPath }
    });
  } else {
    console.error(error);
    toast.add(
      getToastOptions(
        'Unknown error communicating with the server. Please try again.',
        'Unknown Error',
        'error'
      )
    );
  }
}

export async function getConfig() {
  try {
    const response = await api.get('api/config');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function getToken(username, password, totp) {
  try {
    const response = await api.post('api/token', {
      username: username,
      password: totp ? password + totp : password
    });
    return response.data.access_token;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getNotes(term, sort, order, limit) {
  try {
    const response = await api.get('api/search', {
      params: {
        term: term,
        sort: sort,
        order: order,
        limit: limit
      }
    });
    return response.data.map((note) => new SearchResult(note));
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function createNote(title, content) {
  try {
    const response = await api.post('api/notes', {
      title: title,
      content: content
    });
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getNote(title) {
  try {
    const response = await api.get(`api/notes/${encodeURIComponent(title)}`);
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function updateNote(title, newTitle, newContent) {
  try {
    const response = await api.patch(`api/notes/${encodeURIComponent(title)}`, {
      newTitle: newTitle,
      newContent: newContent
    });
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function deleteNote(title) {
  try {
    await api.delete(`api/notes/${encodeURIComponent(title)}`);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getTags() {
  try {
    const response = await api.get('api/tags');
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function createAttachment(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('api/attachments', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

// --- BEGIN GIT INTEGRATION API CALLS ---

export async function getGitStatus() {
  try {
    const response = await api.get('api/git/status');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitAddAll() {
  try {
    const response = await api.post('api/git/add_all');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitUnstageAll() {
  try {
    const response = await api.post('api/git/unstage_all');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitCommit(message) {
  try {
    const response = await api.post('api/git/commit', { message });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function getGitLog(limit = 10, page = 1) {
  try {
    const response = await api.get('api/git/log', {
      params: { limit, page }
    });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitPull(params = {}) {
  try {
    const response = await api.post('api/git/pull', null, { params });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitPush(params = {}) {
  try {
    const response = await api.post('api/git/push', null, { params });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitStageFile(filepath) {
  try {
    const response = await api.post('api/git/stage_file', { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitUnstageFile(filepath) {
  try {
    const response = await api.post('api/git/unstage_file', { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitDiscardFile(filepath) {
  try {
    const response = await api.post('api/git/discard_file', { filepath });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitDiscardAll() {
  try {
    const response = await api.post('api/git/discard_all');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function getGitStatusSummary() {
  try {
    const response = await api.get('api/git/status-summary');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function gitSyncWorkspace(message) {
  try {
    const response = await api.post('api/git/sync', { message });
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function getAutoSyncState() {
  try {
    const response = await api.get('api/git/auto-sync/state');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function pauseAutoSync() {
  try {
    const response = await api.post('api/git/auto-sync/pause');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function resumeAutoSync() {
  try {
    const response = await api.post('api/git/auto-sync/resume');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}

export async function getGitActivityLog() {
  try {
    const response = await api.get('api/git/activity-log');
    return response.data;
  } catch (error) {
    return Promise.reject(error);
  }
}
// --- END GIT INTEGRATION API CALLS ---
