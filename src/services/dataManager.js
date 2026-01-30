/**
 * 数据管理器：参照 task_manage database_manager.py
 * - 本地持久化：uni 本地存储（替代 SQLite）
 * - 与服务器通信：拉取/上传/删除，与 server_example API 一致
 */
import { getRemoteConfig } from '../api/config.js';
import {
  getTasksFromServer,
  createOrUpdateTaskOnServer,
  deleteTaskOnServer,
  taskFromServer,
  taskToServer,
} from '../api/task.js';

const STORAGE_KEY_TASKS = 'task_list';
const STORAGE_KEY_SYNC_STATUS = 'task_sync_status';

/**
 * 从本地存储加载任务列表
 * @returns {Array}
 */
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

/**
 * 将任务列表写入本地存储
 * @param {Array} tasks
 */
export function saveTasksToStorage(tasks) {
  try {
    uni.setStorageSync(STORAGE_KEY_TASKS, JSON.stringify(tasks || []));
  } catch (e) {
    console.warn('[dataManager] saveTasksToStorage failed', e);
    throw e;
  }
}

/**
 * 是否已配置远程服务器
 */
export function hasRemoteConfig() {
  const { api_base_url } = getRemoteConfig();
  return !!api_base_url;
}

/**
 * 从服务器拉取任务并合并到本地（以服务器为准：服务器有则覆盖本地，本地多出的保留）
 * 与 database_manager.sync_from_server 行为一致
 * @param {Array} localTasks - 当前本地任务列表（可被修改）
 * @returns {Promise<{ success: boolean, merged: Array, error?: string }>}
 */
export function syncFromServer(localTasks) {
  return getTasksFromServer().then((res) => {
    if (!res.success) {
      return { success: false, merged: localTasks || [], error: res.error };
    }
    const serverTasks = res.tasks || [];
    const byId = new Map();
    (localTasks || []).forEach((t) => byId.set(t.id, t));
    serverTasks.forEach((t) => byId.set(t.id, t));
    const merged = Array.from(byId.values()).sort(
      (a, b) => (b.createdAt || '').localeCompare(a.createdAt || '')
    );
    saveTasksToStorage(merged);
    setLastSyncStatus('download', true, `已从服务器同步 ${serverTasks.length} 条任务`);
    return { success: true, merged };
  });
}

/**
 * 将本地未同步任务上传到服务器（逐条 POST）
 * 与 database_manager.sync_to_server 行为一致
 * @param {Array} localTasks
 * @returns {Promise<{ success: boolean, uploaded: number, error?: string }>}
 */
export function syncToServer(localTasks) {
  const list = localTasks || loadTasksFromStorage();
  let uploaded = 0;
  const run = (index) => {
    if (index >= list.length) {
      setLastSyncStatus('upload', true, `已同步 ${uploaded} 条任务到服务器`);
      return Promise.resolve({ success: true, uploaded });
    }
    const task = list[index];
    return createOrUpdateTaskOnServer(task).then((res) => {
      if (res.success) uploaded += 1;
      return run(index + 1);
    });
  };
  return run(0);
}

/**
 * 清空服务器任务并用本地任务覆盖上传
 * 与 database_manager.clear_server_and_upload 一致
 * @param {Array} localTasks
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export function clearServerAndUpload(localTasks) {
  return getTasksFromServer().then((res) => {
    if (!res.success) return { success: false, error: res.error };
    const serverTasks = res.tasks || [];
    const deleteOne = (index) => {
      if (index >= serverTasks.length) {
        return syncToServer(localTasks).then((r) => ({
          success: r.success,
          error: r.error,
        }));
      }
      const t = serverTasks[index];
      return deleteTaskOnServer(t.id).then(() => deleteOne(index + 1));
    };
    return deleteOne(0);
  });
}

/**
 * 保存任务：优先本地保存，成功后立即 resolve；远程同步在后台进行不阻塞。
 * @param {object} task - 前端任务对象（含 id, title, note, dueDate, importance, urgency, isCompleted, completedAt, createdAt）
 * @param {boolean} syncRemote - 是否在后台同步到服务器（不阻塞返回）
 * @returns {Promise<{ success: boolean, tasks: Array }>} 本地保存成功即 resolve；本地失败 reject
 */
export function saveTask(task, syncRemote = true) {
  const list = loadTasksFromStorage();
  const idx = list.findIndex((t) => t.id === task.id);
  const now = new Date().toISOString();
  const record = {
    ...task,
    createdAt: task.createdAt || now,
  };
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
  if (syncRemote && hasRemoteConfig()) {
    createOrUpdateTaskOnServer(record)
      .then((res) => {
        setLastSyncStatus('upload', res.success, res.error || '');
      })
      .catch(() => {
        setLastSyncStatus('upload', false, '同步失败');
      });
  }
  return Promise.resolve({ success: true, tasks: list });
}

/**
 * 删除任务（本地删除，并可选在服务器上删除）
 * @param {string} taskId
 * @param {boolean} syncRemote
 * @returns {Promise<{ success: boolean, tasks: Array, error?: string }>}
 */
export function deleteTask(taskId, syncRemote = true) {
  const list = loadTasksFromStorage().filter((t) => t.id !== taskId);
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

/**
 * 获取同步状态（最近一次同步记录）
 */
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
  taskFromServer,
  taskToServer,
};
