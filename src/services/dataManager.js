/**
 * ä»»åŠ¡æ•°æ®ç®¡ç†ã€? * 1. è´Ÿè´£æœ¬åœ°å­˜å‚¨çš„è¯»å–ä¸Žå†™å…¥ã€? * 2. è´Ÿè´£ä¸ŽæœåŠ¡ç«¯ä»»åŠ¡æ•°æ®è¿›è¡ŒåŒæ­¥ã€? * 3. è´Ÿè´£è®°å½•ä»»åŠ¡å­—æ®µçš„åŽ†å²å˜æ›´ã€? */
import {
  getTasksFromServer,
  createOrUpdateTaskOnServer,
  deleteTaskOnServer,
  postTaskHistoryToServer,
  taskFromServer,
  taskToServer,
} from '../api/task.js';
import { getRemoteConfig } from '../api/config.js';

const STORAGE_KEY_TASKS = 'task_list';
const STORAGE_KEY_SYNC_STATUS = 'task_sync_status';
const STORAGE_KEY_TASK_HISTORY = 'task_history';

export function loadTasksFromStorage() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY_TASKS);
    if (!raw) return [];
    const list = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return Array.isArray(list) ? list : [];
  } catch (e) {
    console.warn('[dataManager] loadTasksFromStorage failed', e);
    return [];
  }
}

export function saveTasksToStorage(tasks) {
  try {
    uni.setStorageSync(STORAGE_KEY_TASKS, JSON.stringify(tasks || []));
  } catch (e) {
    console.warn('[dataManager] saveTasksToStorage failed', e);
    throw e;
  }
}

export function hasRemoteConfig() {
  const { api_base_url } = getRemoteConfig();
  return !!api_base_url;
}

function isTaskDirty(task) {
  return !!(task && task._syncDirty);
}

function updateStoredTask(taskId, updater) {
  const list = loadTasksFromStorage();
  const idx = list.findIndex((item) => item.id === taskId);
  if (idx < 0) return list;

  const next = updater({ ...list[idx] });
  if (!next) return list;
  list[idx] = next;
  saveTasksToStorage(list);
  return list;
}

function markTaskSyncState(taskId, dirty, extra = {}) {
  return updateStoredTask(taskId, (task) => ({
    ...task,
    ...extra,
    _syncDirty: dirty,
  }));
}

function fieldToServerValue(task, field) {
  const map = {
    text: () => (task.title != null ? String(task.title) : ''),
    notes: () => (task.note != null ? String(task.note) : ''),
    due_date: () => {
      const value = task.dueDate;
      if (!value) return '';
      if (typeof value === 'string') return value.split('T')[0] || value;
      return new Date(value).toISOString().split('T')[0];
    },
    urgency: () => (task.urgency === 'high' ? 'high' : 'low'),
    importance: () => (task.importance === 'high' ? 'high' : 'low'),
  };

  return (map[field] && map[field]()) || '';
}

function collectOverwriteHistoryRecords(localTasks, serverTasks) {
  const localById = new Map((localTasks || []).map((task) => [task.id, task]));
  const fields = ['text', 'notes', 'due_date', 'urgency', 'importance'];
  const timestamp = new Date().toISOString();
  const records = [];

  (serverTasks || []).forEach((serverTask) => {
    const localTask = localById.get(serverTask.id);
    if (!localTask) return;

    fields.forEach((field) => {
      const localValue = fieldToServerValue(localTask, field);
      const serverValue = fieldToServerValue(serverTask, field);
      if (localValue === serverValue) return;

      records.push({
        task_id: serverTask.id,
        field_name: field,
        field_value: serverValue,
        action: 'update',
        timestamp,
      });
    });
  });

  return records;
}

function saveTaskHistoryOnSave(taskId, newTask, prevTask, timestamp) {
  const fields = ['text', 'notes', 'due_date', 'urgency', 'importance'];
  const records = [];
  const isNewTask = !prevTask;

  for (const field of fields) {
    const newVal = fieldToServerValue(newTask, field);
    const prevVal = prevTask ? fieldToServerValue(prevTask, field) : '';
    if (prevVal !== newVal) {
      records.push({
        task_id: taskId,
        field_name: field,
        field_value: newVal,
        action: isNewTask ? 'create' : 'update',
        timestamp,
      });
    }
  }

  if (records.length === 0 && isNewTask) {
    for (const field of fields) {
      const newVal = fieldToServerValue(newTask, field);
      if (!newVal) continue;
      records.push({
        task_id: taskId,
        field_name: field,
        field_value: newVal,
        action: 'create',
        timestamp,
      });
    }
  }

  if (records.length > 0) {
    appendTaskHistoryRecords(records);
  }

  return records;
}

export function syncFromServer(localTasks) {
  return getTasksFromServer().then((res) => {
    if (!res.success) {
      return { success: false, merged: localTasks || [], error: res.error };
    }

    const serverTasks = res.tasks || [];
    const overwriteRecords = collectOverwriteHistoryRecords(localTasks || [], serverTasks);
    const byId = new Map();

    (localTasks || []).forEach((task) => byId.set(task.id, task));
    serverTasks.forEach((task) => byId.set(task.id, { ...task, _syncDirty: false }));

    const merged = Array.from(byId.values()).sort(
      (a, b) => (b.createdAt || '').localeCompare(a.createdAt || '')
    );

    saveTasksToStorage(merged);
    if (overwriteRecords.length > 0) {
      appendTaskHistoryRecords(overwriteRecords);
    }
    setLastSyncStatus('download', true, 'ÏÂÔØ³É¹¦£¬¹² ' + serverTasks.length + ' ÌõÈÎÎñ');
    return { success: true, merged };
  });
}

export function syncToServer(localTasks) {
  const allTasks = localTasks || loadTasksFromStorage();
  const dirtyTasks = allTasks.filter(isTaskDirty);
  const list = dirtyTasks.length > 0 ? dirtyTasks : allTasks;
  let uploaded = 0;

  const run = (index) => {
    if (index >= list.length) {
      setLastSyncStatus('upload', true, 'ÉÏ´«³É¹¦£¬¹² ' + uploaded + ' ÌõÈÎÎñ');
      return Promise.resolve({ success: true, uploaded });
    }

    const task = list[index];
    return createOrUpdateTaskOnServer(task).then((res) => {
      if (res.success) {
        uploaded += 1;
        markTaskSyncState(task.id, false);
      }
      return run(index + 1);
    });
  };

  return run(0);
}

export function clearServerAndUpload(localTasks) {
  return getTasksFromServer().then((res) => {
    if (!res.success) return { success: false, error: res.error };

    const serverTasks = res.tasks || [];
    const deleteOne = (index) => {
      if (index >= serverTasks.length) {
        const toUpload = (localTasks || loadTasksFromStorage()).map((task) => ({
          ...task,
          _syncDirty: true,
        }));
        return syncToServer(toUpload).then((result) => ({
          success: result.success,
          error: result.error,
        }));
      }

      const task = serverTasks[index];
      return deleteTaskOnServer(task.id).then(() => deleteOne(index + 1));
    };

    return deleteOne(0);
  });
}

export function loadTaskHistoryFromStorage() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY_TASK_HISTORY);
    if (!raw) return [];
    const list = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return Array.isArray(list) ? list : [];
  } catch (e) {
    console.warn('[dataManager] loadTaskHistoryFromStorage failed', e);
    return [];
  }
}

export function appendTaskHistoryRecords(records) {
  const list = loadTaskHistoryFromStorage();
  const toAdd = (records || []).map((record) => ({
    task_id: record.task_id,
    field_name: record.field_name,
    field_value: String(record.field_value ?? ''),
    action: record.action || 'update',
    timestamp: record.timestamp || new Date().toISOString(),
  }));

  list.push(...toAdd);
  try {
    uni.setStorageSync(STORAGE_KEY_TASK_HISTORY, JSON.stringify(list));
  } catch (e) {
    console.warn('[dataManager] appendTaskHistoryRecords failed', e);
  }
}

export function getTaskHistory(taskId) {
  const list = loadTaskHistoryFromStorage();
  const fieldHistory = {};

  list
    .filter((record) => record.task_id === taskId)
    .sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''))
    .forEach((record) => {
      const fieldName = record.field_name || 'text';
      if (!fieldHistory[fieldName]) fieldHistory[fieldName] = [];
      fieldHistory[fieldName].push({
        value: record.field_value,
        timestamp: record.timestamp,
        action: record.action,
      });
    });

  return fieldHistory;
}

export function saveTask(task, syncRemote = false) {
  const list = loadTasksFromStorage();
  const idx = list.findIndex((item) => item.id === task.id);
  const now = new Date().toISOString();
  const prevTask = idx >= 0 ? list[idx] : null;
  const record = {
    ...task,
    createdAt: task.createdAt || now,
    updatedAt: now,
    _syncDirty: true,
  };

  const historyRecords = saveTaskHistoryOnSave(task.id, record, prevTask, now);

  if (idx >= 0) {
    list[idx] = record;
  } else {
    list.push(record);
  }

  try {
    saveTasksToStorage(list);
  } catch (e) {
    return Promise.reject(e);
  }

  console.log('[dataManager.saveTask] local save result', {
    taskId: record.id,
    title: record.title,
    updatedAt: record.updatedAt,
    syncDirty: record._syncDirty,
    storedTask: list.find((item) => item.id === record.id) || null,
  });

  if (syncRemote && hasRemoteConfig()) {
    createOrUpdateTaskOnServer(record)
      .then((res) => {
        setLastSyncStatus('upload', res.success, res.error || '');
        if (res.success && historyRecords.length > 0) {
          postTaskHistoryToServer(task.id, historyRecords).catch(() => {});
        }
        if (res.success) {
          markTaskSyncState(task.id, false);
        }
      })
      .catch(() => {
        setLastSyncStatus('upload', false, 'ä¸Šä¼ å¤±è´¥ï¼Œè¯·ç¨åŽé‡è¯•');
      });
  }

  return Promise.resolve({ success: true, tasks: list });
}

export function deleteTask(taskId, syncRemote = false) {
  const list = loadTasksFromStorage().filter((task) => task.id !== taskId);
  saveTasksToStorage(list);

  if (syncRemote && hasRemoteConfig()) {
    return deleteTaskOnServer(taskId).then((res) => ({
      success: true,
      tasks: list,
      syncSuccess: res.success,
      syncError: res.error,
    }));
  }

  return Promise.resolve({ success: true, tasks: list });
}

export function getLastSyncStatus() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY_SYNC_STATUS);
    if (!raw) return null;
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch (e) {
    return null;
  }
}

function setLastSyncStatus(type, status, message) {
  try {
    uni.setStorageSync(
      STORAGE_KEY_SYNC_STATUS,
      JSON.stringify({
        sync_type: type,
        status: status ? 'success' : 'fail',
        message,
        last_sync_at: new Date().toISOString(),
      })
    );
  } catch (e) {
    console.warn('[dataManager] setLastSyncStatus failed', e);
  }
}

export default {
  loadTasksFromStorage,
  saveTasksToStorage,
  hasRemoteConfig,
  syncFromServer,
  syncToServer,
  clearServerAndUpload,
  saveTask,
  deleteTask,
  getLastSyncStatus,
  loadTaskHistoryFromStorage,
  appendTaskHistoryRecords,
  getTaskHistory,
  taskFromServer,
  taskToServer,
};


