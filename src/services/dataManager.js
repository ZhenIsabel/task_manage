/**
 * 任务数据管理工具
 * 1. 负责本地存储的读取与写入
 * 2. 负责与服务端任务数据进行同步
 * 3. 负责记录任务字段的历史变更
 * 4. 负责暂存远程冲突并等待用户确认
 **/
import {
  getTasksFromServer,
  getTaskHistoryFromServer,
  createOrUpdateTaskOnServer,
  deleteTaskOnServer,
  postTaskHistoryToServer,
  taskFromServer,
  taskToServer,
  healthCheck,
} from '../api/task.js';
import { getRemoteConfig } from '../api/config.js';

const STORAGE_KEY_TASKS = 'task_list';
const STORAGE_KEY_SYNC_STATUS = 'task_sync_status';
const STORAGE_KEY_TASK_HISTORY = 'task_history';
const STORAGE_KEY_PENDING_REMOTE_CHANGES = 'task_pending_remote_changes';

const HISTORY_FIELDS = ['text', 'notes', 'due_date', 'urgency', 'importance'];
const HIGH_LABEL = '高';
const LOW_LABEL = '低';

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

function sortTasks(tasks) {
  return [...(tasks || [])].sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
}

export function hasRemoteConfig() {
  const cfg = getRemoteConfig();
  const enabled = typeof cfg.enabled === 'boolean' ? cfg.enabled : !!cfg.api_base_url;
  return !!(enabled && cfg.api_base_url && cfg.api_token && cfg.username);
}

function isTaskDirty(task) {
  return !!(task && task._syncDirty);
}

function isTaskDeleted(task) {
  return !!(task && task.deleted);
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
    urgency: () => (task.urgency === 'high' ? HIGH_LABEL : LOW_LABEL),
    importance: () => (task.importance === 'high' ? HIGH_LABEL : LOW_LABEL),
  };

  return (map[field] && map[field]()) || '';
}

export function parseSyncTime(value) {
  if (!value) return null;
  if (value instanceof Date) {
    const time = value.getTime();
    return Number.isNaN(time) ? null : time;
  }

  const raw = String(value).trim();
  if (!raw) return null;
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const time = Date.parse(normalized);
  return Number.isNaN(time) ? null : time;
}

function isRemoteTimeNewer(remoteUpdatedAt, localUpdatedAt) {
  if (!localUpdatedAt) return !!remoteUpdatedAt;
  if (!remoteUpdatedAt) return false;

  const remoteTime = parseSyncTime(remoteUpdatedAt);
  const localTime = parseSyncTime(localUpdatedAt);
  if (remoteTime != null && localTime != null) return remoteTime > localTime;

  return String(remoteUpdatedAt) > String(localUpdatedAt);
}

function collectOverwriteHistoryRecords(localTasks, serverTasks) {
  const localById = new Map((localTasks || []).map((task) => [task.id, task]));
  const timestamp = new Date().toISOString();
  const records = [];

  (serverTasks || []).forEach((serverTask) => {
    const localTask = localById.get(serverTask.id);
    if (!localTask) return;

    HISTORY_FIELDS.forEach((field) => {
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
  const records = [];
  const isNewTask = !prevTask;

  for (const field of HISTORY_FIELDS) {
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
    for (const field of HISTORY_FIELDS) {
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

function flattenFieldHistory(taskId, historyByField) {
  const records = [];

  Object.entries(historyByField || {}).forEach(([fieldName, list]) => {
    (list || []).forEach((record) => {
      records.push({
        task_id: taskId,
        field_name: fieldName,
        field_value: String(record?.value ?? record?.field_value ?? ''),
        action: record?.action || 'update',
        timestamp: record?.timestamp || '',
      });
    });
  });

  return records;
}

function hasLocalTaskHistory(taskId) {
  const list = loadTaskHistoryFromStorage();
  return list.some((record) => record.task_id === taskId);
}

function shouldFetchTaskHistory(localTask, serverTask) {
  if (!serverTask || !serverTask.id) return false;
  if (!localTask) return true;
  if (!hasLocalTaskHistory(serverTask.id)) return true;

  const localUpdatedAt = localTask.updatedAt || '';
  const serverUpdatedAt = serverTask.updatedAt || '';
  if (!localUpdatedAt || !serverUpdatedAt) return true;
  return isRemoteTimeNewer(serverUpdatedAt, localUpdatedAt);
}

async function fetchServerHistoryRecords(localTasks, serverTasks) {
  const localById = new Map((localTasks || []).map((task) => [task.id, task]));
  const tasksToFetch = (serverTasks || []).filter((task) => shouldFetchTaskHistory(localById.get(task.id), task));

  const results = await Promise.all(
    tasksToFetch.map((task) =>
      getTaskHistoryFromServer(task.id)
        .then((res) => (res.success ? flattenFieldHistory(task.id, res.history) : []))
        .catch(() => [])
    )
  );

  return results.flat();
}

function buildHistoryRecordKey(record) {
  return [
    record.task_id || '',
    record.field_name || '',
    String(record.field_value ?? ''),
    record.action || 'update',
    record.timestamp || '',
  ].join('::');
}

function buildTaskComparisonSnapshot(task) {
  if (!task) return null;
  return {
    title: String(task.title || ''),
    note: String(task.note || ''),
    dueDate: task.dueDate || '',
    importance: task.importance === 'high' ? 'high' : 'low',
    urgency: task.urgency === 'high' ? 'high' : 'low',
    isCompleted: !!task.isCompleted,
    completedAt: task.completedAt || '',
    deleted: !!task.deleted,
  };
}

function taskContentChanged(localTask, remoteTask) {
  return JSON.stringify(buildTaskComparisonSnapshot(localTask)) !== JSON.stringify(buildTaskComparisonSnapshot(remoteTask));
}

function savePendingRemoteTaskChanges(changes) {
  try {
    uni.setStorageSync(STORAGE_KEY_PENDING_REMOTE_CHANGES, JSON.stringify(changes || []));
  } catch (e) {
    console.warn('[dataManager] savePendingRemoteTaskChanges failed', e);
  }
}

function mergePendingRemoteTaskChanges(existing, incoming) {
  const byId = new Map();
  (existing || []).forEach((change) => {
    if (change && change.id) byId.set(change.id, change);
  });
  (incoming || []).forEach((change) => {
    if (change && change.id) byId.set(change.id, change);
  });
  return Array.from(byId.values());
}

export function getPendingRemoteTaskChanges() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY_PENDING_REMOTE_CHANGES);
    if (!raw) return [];
    const list = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return Array.isArray(list) ? list : [];
  } catch (e) {
    console.warn('[dataManager] getPendingRemoteTaskChanges failed', e);
    return [];
  }
}

export function hasPendingRemoteTaskChanges() {
  return getPendingRemoteTaskChanges().length > 0;
}

export function clearPendingRemoteTaskChanges() {
  savePendingRemoteTaskChanges([]);
}

function buildPendingRemoteTaskChange(localTask, remoteTask) {
  return {
    id: remoteTask.id,
    title: remoteTask.title || localTask?.title || '',
    changeType: remoteTask.deleted ? 'delete' : 'update',
    localTask,
    remoteTask,
  };
}

function buildTaskHistoryPayload(taskId) {
  const byField = {};
  loadTaskHistoryFromStorage()
    .filter((record) => record.task_id === taskId)
    .forEach((record) => {
      const fieldName = record.field_name || 'text';
      if (!byField[fieldName]) byField[fieldName] = [];
      byField[fieldName].push({
        value: String(record.field_value ?? ''),
        timestamp: record.timestamp || '',
        action: record.action || 'update',
      });
    });
  return Object.keys(byField).length ? byField : null;
}

function visibleTasks(tasks) {
  return (tasks || []).filter((task) => !isTaskDeleted(task));
}

export async function bootstrapRemoteSync() {
  if (!hasRemoteConfig()) {
    return { success: false, error: '远程配置不完整', merged: loadTasksFromStorage(), pendingChanges: getPendingRemoteTaskChanges() };
  }

  const health = await healthCheck();
  if (!health.success) {
    setLastSyncStatus('health', false, health.error || '健康检查失败');
    return { success: false, error: health.error || '健康检查失败', merged: loadTasksFromStorage(), pendingChanges: getPendingRemoteTaskChanges() };
  }

  setLastSyncStatus('health', true, '远程服务可用');
  return syncFromServer(loadTasksFromStorage());
}

export async function syncFromServer(localTasks) {
  const currentLocalTasks = Array.isArray(localTasks) ? localTasks : loadTasksFromStorage();
  const existingPending = getPendingRemoteTaskChanges();
  if (existingPending.length > 0) {
    return { success: true, merged: currentLocalTasks, pendingChanges: existingPending };
  }

  const res = await getTasksFromServer();
  if (!res.success) {
    setLastSyncStatus('download', false, res.error || '拉取失败');
    return { success: false, merged: currentLocalTasks, error: res.error, pendingChanges: getPendingRemoteTaskChanges() };
  }

  const serverTasks = res.tasks || [];
  const byId = new Map((currentLocalTasks || []).map((task) => [task.id, { ...task }]));
  const pendingChanges = [];
  const appliedRemoteTasks = [];

  const serverIds = new Set(serverTasks.map((task) => task.id).filter(Boolean));

  serverTasks.forEach((remoteTask) => {
    const localTask = byId.get(remoteTask.id);
    if (!localTask) {
      const inserted = { ...remoteTask, _syncDirty: false };
      byId.set(remoteTask.id, inserted);
      appliedRemoteTasks.push(inserted);
      return;
    }

    const remoteUpdatedAt = remoteTask.updatedAt || '';
    const localUpdatedAt = localTask.updatedAt || '';
    const remoteIsNewer = isRemoteTimeNewer(remoteUpdatedAt, localUpdatedAt);
    const contentChanged = taskContentChanged(localTask, remoteTask);

    if (localTask.deleted && localTask._syncDirty && !remoteTask.deleted) {
      return;
    }

    if (remoteTask.deleted) {
      if (isTaskDirty(localTask) && !localTask.deleted) {
        pendingChanges.push(buildPendingRemoteTaskChange(localTask, remoteTask));
        return;
      }
      const applied = { ...localTask, ...remoteTask, deleted: true, _syncDirty: false };
      byId.set(remoteTask.id, applied);
      appliedRemoteTasks.push(applied);
      return;
    }

    if (remoteIsNewer && contentChanged) {
      pendingChanges.push(buildPendingRemoteTaskChange(localTask, remoteTask));
      return;
    }

    if (remoteIsNewer && !contentChanged) {
      byId.set(remoteTask.id, { ...remoteTask, _syncDirty: false });
      appliedRemoteTasks.push(remoteTask);
    }
  });

  currentLocalTasks.forEach((localTask) => {
    if (!localTask || !localTask.id || localTask.deleted || serverIds.has(localTask.id)) return;
    const remoteDeletedTask = {
      ...localTask,
      deleted: true,
      updatedAt: new Date().toISOString(),
    };

    if (isTaskDirty(localTask)) {
      pendingChanges.push(buildPendingRemoteTaskChange(localTask, remoteDeletedTask));
      return;
    }

    const applied = { ...localTask, deleted: true, _syncDirty: false, updatedAt: remoteDeletedTask.updatedAt };
    byId.set(localTask.id, applied);
    appliedRemoteTasks.push(applied);
  });

  const merged = sortTasks(Array.from(byId.values()));
  saveTasksToStorage(merged);
  const mergedPending = mergePendingRemoteTaskChanges(existingPending, pendingChanges);
  savePendingRemoteTaskChanges(mergedPending);

  const serverHistoryRecords = await fetchServerHistoryRecords(currentLocalTasks, appliedRemoteTasks);
  appendTaskHistoryRecords(serverHistoryRecords);
  setLastSyncStatus('download', true, mergedPending.length > 0 ? `发现 ${mergedPending.length} 条待确认冲突` : `成功下载 ${serverTasks.length} 个任务`);

  return { success: true, merged, pendingChanges: mergedPending };
}

export async function syncToServer(localTasks) {
  const allTasks = localTasks || loadTasksFromStorage();
  const pendingIds = new Set(getPendingRemoteTaskChanges().map((change) => change.id));
  const list = allTasks.filter((task) => isTaskDirty(task) && !pendingIds.has(task.id));
  let uploaded = 0;
  let firstError = '';

  if (list.length === 0) {
    setLastSyncStatus('upload', true, '没有待上传任务');
    return { success: true, uploaded: 0 };
  }

  for (const task of list) {
    const res = task.deleted
      ? await deleteTaskOnServer(task.id)
      : await createOrUpdateTaskOnServer({
        ...task,
        history: buildTaskHistoryPayload(task.id) || undefined,
      });
    if (res.success) {
      uploaded += 1;
      markTaskSyncState(task.id, false);
      continue;
    }
    if (!firstError) {
      firstError = res.error || '上传失败';
    }
  }

  if (firstError) {
    setLastSyncStatus('upload', false, firstError);
    return { success: false, uploaded, error: firstError };
  }

  setLastSyncStatus('upload', true, `成功上传${uploaded}个任务`);
  return { success: true, uploaded };
}

export async function resolvePendingRemoteTaskChanges(acceptRemoteIds = [], acceptLocalIds = []) {
  const currentPending = getPendingRemoteTaskChanges();
  const remoteSet = new Set(acceptRemoteIds || []);
  const localSet = new Set(acceptLocalIds || []);
  const originalTasks = loadTasksFromStorage();
  const byId = new Map(originalTasks.map((task) => [task.id, { ...task }]));
  const remaining = [];
  const remoteAppliedTasks = [];

  currentPending.forEach((change) => {
    if (remoteSet.has(change.id)) {
      const remoteTask = taskFromServer(change.remoteTask);
      if (remoteTask) {
        const applied = { ...remoteTask, _syncDirty: false };
        byId.set(change.id, applied);
        remoteAppliedTasks.push(applied);
      }
      return;
    }

    if (localSet.has(change.id)) {
      const localTask = byId.get(change.id);
      if (localTask) {
        byId.set(change.id, { ...localTask, deleted: false, _syncDirty: true });
      }
      return;
    }

    remaining.push(change);
  });

  const merged = sortTasks(Array.from(byId.values()));
  saveTasksToStorage(merged);
  savePendingRemoteTaskChanges(remaining);

  const overwriteRecords = collectOverwriteHistoryRecords(originalTasks, remoteAppliedTasks);
  appendTaskHistoryRecords(overwriteRecords);
  const fetchedRemoteHistory = await fetchServerHistoryRecords(originalTasks, remoteAppliedTasks);
  appendTaskHistoryRecords(fetchedRemoteHistory);

  if (localSet.size > 0 && hasRemoteConfig()) {
    const tasksToUpload = merged.filter((task) => localSet.has(task.id));
    const uploadResult = await syncToServer(tasksToUpload);
    if (!uploadResult.success) {
      return { success: false, error: uploadResult.error, merged, pendingChanges: remaining };
    }
  }

  return { success: true, merged: loadTasksFromStorage(), pendingChanges: remaining };
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
  const seen = new Set(list.map(buildHistoryRecordKey));
  const toAdd = (records || [])
    .filter((record) => record && record.task_id)
    .map((record) => ({
      task_id: record.task_id,
      field_name: record.field_name,
      field_value: String(record.field_value ?? ''),
      action: record.action || 'update',
      timestamp: record.timestamp || new Date().toISOString(),
    }))
    .filter((record) => {
      const key = buildHistoryRecordKey(record);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  if (toAdd.length === 0) return;

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

  const sorted = sortTasks(list);

  try {
    saveTasksToStorage(sorted);
  } catch (e) {
    return Promise.reject(e);
  }

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
        setLastSyncStatus('upload', false, '上传失败，请稍后重试');
      });
  }

  return Promise.resolve({ success: true, tasks: sorted });
}

export function deleteTask(taskId, syncRemote = false) {
  const now = new Date().toISOString();
  const list = loadTasksFromStorage();
  const idx = list.findIndex((task) => task.id === taskId);
  if (idx < 0) {
    return Promise.resolve({ success: true, tasks: visibleTasks(list) });
  }

  list[idx] = {
    ...list[idx],
    deleted: true,
    updatedAt: now,
    _syncDirty: true,
  };
  saveTasksToStorage(list);

  if (syncRemote && hasRemoteConfig()) {
    return deleteTaskOnServer(taskId).then((res) => ({
      success: true,
      tasks: visibleTasks(list),
      syncSuccess: res.success,
      syncError: res.error,
    }));
  }

  return Promise.resolve({ success: true, tasks: visibleTasks(list) });
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
  bootstrapRemoteSync,
  syncFromServer,
  syncToServer,
  resolvePendingRemoteTaskChanges,
  getPendingRemoteTaskChanges,
  hasPendingRemoteTaskChanges,
  clearPendingRemoteTaskChanges,
  clearServerAndUpload,
  saveTask,
  deleteTask,
  getLastSyncStatus,
  loadTaskHistoryFromStorage,
  appendTaskHistoryRecords,
  getTaskHistory,
  parseSyncTime,
  taskFromServer,
  taskToServer,
};
