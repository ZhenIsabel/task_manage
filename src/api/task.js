/**
 * ?? API ???????????????????????
 */
import request from './request.js';

// ??????????????/?????????????????
const HIGH_LABEL = '\u9ad8';
const LOW_LABEL = '\u4f4e';

const HIGH_VALUES = new Set([HIGH_LABEL, 'high', 'HIGH', 'High', 1, '1', true, 'true']);
const COMPLETED_VALUES = new Set([true, 'true', 1, '1']);

const importanceToServer = (value) => (value === 'high' ? HIGH_LABEL : LOW_LABEL);
const urgencyToServer = (value) => (value === 'high' ? HIGH_LABEL : LOW_LABEL);
const importanceFromServer = (value) => (HIGH_VALUES.has(value) ? 'high' : 'low');
const urgencyFromServer = (value) => (HIGH_VALUES.has(value) ? 'high' : 'low');

function completedFromServer(value) {
  return COMPLETED_VALUES.has(value);
}

const SERVER_MAPPED_FIELDS = new Set([
  'id',
  'text',
  'notes',
  'due_date',
  'importance',
  'urgency',
  'completed',
  'completed_date',
  'created_at',
  'updated_at',
  'position',
]);

function extractServerExtras(serverTask) {
  if (!serverTask || typeof serverTask !== 'object') return null;

  const extras = {};
  Object.keys(serverTask).forEach((key) => {
    if (SERVER_MAPPED_FIELDS.has(key)) return;
    extras[key] = serverTask[key];
  });

  return Object.keys(extras).length ? extras : null;
}

export function taskToServer(task) {
  const base = task && typeof task._serverRaw === 'object' && task._serverRaw
    ? { ...task._serverRaw }
    : {};
  const basePosition = base.position && typeof base.position === 'object' ? base.position : {};
  const taskPosition = task.position && typeof task.position === 'object' ? task.position : {};

  return {
    ...base,
    id: task.id,
    text: task.title ?? '',
    notes: task.note ?? '',
    due_date: task.dueDate
      ? typeof task.dueDate === 'string'
        ? task.dueDate
        : new Date(task.dueDate).toISOString()
      : '',
    importance: importanceToServer(task.importance || 'low'),
    urgency: urgencyToServer(task.urgency || 'low'),
    completed: !!task.isCompleted,
    completed_date: task.completedAt || '',
    created_at: task.createdAt || base.created_at || new Date().toISOString(),
    updated_at: task.updatedAt || base.updated_at || new Date().toISOString(),
    position: {
      ...basePosition,
      x: taskPosition.x ?? basePosition.x ?? 100,
      y: taskPosition.y ?? basePosition.y ?? 100,
    },
  };
}

export function taskFromServer(serverTask) {
  if (!serverTask) return null;
  const position = serverTask.position || { x: 100, y: 100 };

  return {
    id: serverTask.id,
    title: serverTask.text ?? serverTask.title ?? '',
    note: serverTask.notes ?? serverTask.note ?? '',
    dueDate: serverTask.due_date || serverTask.dueDate || null,
    importance: importanceFromServer(serverTask.importance || LOW_LABEL),
    urgency: urgencyFromServer(serverTask.urgency || LOW_LABEL),
    isCompleted: completedFromServer(serverTask.completed),
    completedAt: serverTask.completed_date || serverTask.completedAt || null,
    createdAt:
      serverTask.created_at ||
      serverTask.createdAt ||
      serverTask.updated_at ||
      serverTask.updatedAt ||
      new Date().toISOString(),
    updatedAt:
      serverTask.updated_at ||
      serverTask.updatedAt ||
      serverTask.created_at ||
      serverTask.createdAt ||
      new Date().toISOString(),
    position: {
      x: position.x ?? 100,
      y: position.y ?? 100,
    },
    _serverRaw: extractServerExtras(serverTask),
  };
}

export function getTasksFromServer() {
  return request('GET', '/api/tasks').then((res) => {
    if (!res.success) {
      return { success: false, error: res.error, tasks: [] };
    }

    const list = (res.data && res.data.tasks) || [];
    return {
      success: true,
      tasks: list.map(taskFromServer).filter(Boolean),
    };
  });
}

function getRawTaskFromServer(taskId) {
  if (!taskId) return Promise.resolve(null);

  return request('GET', '/api/tasks')
    .then((res) => {
      if (!res.success) return null;
      const list = (res.data && res.data.tasks) || [];
      return list.find((item) => item && item.id === taskId) || null;
    })
    .catch(() => null);
}

export function createOrUpdateTaskOnServer(task) {
  const hasServerRaw = !!(task && task._serverRaw && typeof task._serverRaw === 'object');
  const prepareTask = hasServerRaw
    ? Promise.resolve(task)
    : getRawTaskFromServer(task && task.id).then((serverTask) => {
      if (!serverTask) return task;
      return {
        ...task,
        _serverRaw: extractServerExtras(serverTask),
      };
    });

  return prepareTask.then((payloadTask) => {
    const body = taskToServer(payloadTask);
    return request('POST', '/api/tasks', body).then((res) => {
      if (res.success) return { success: true };
      return { success: false, error: res.error };
    });
  });
}

export function deleteTaskOnServer(taskId) {
  return request('DELETE', "/api/tasks/" + taskId).then((res) => {
    if (res.success) return { success: true };
    return { success: false, error: res.error };
  });
}

export function healthCheck() {
  return request('GET', '/api/health');
}

export function getTaskHistoryFromServer(taskId) {
  return request('GET', "/api/tasks/" + taskId + '/history').then((res) => {
    if (!res.success) {
      return { success: false, error: res.error, history: {} };
    }

    const history = (res.data && res.data.history) || {};
    return { success: true, history };
  });
}

export function postTaskHistoryToServer(taskId, records) {
  const body = {
    history: (records || []).map((record) => ({
      field_name: record.field_name,
      field_value: record.field_value,
      action: record.action || 'update',
      timestamp: record.timestamp || new Date().toISOString(),
    })),
  };

  return request('POST', "/api/tasks/" + taskId + '/history', body).then((res) => {
    if (res.success) return { success: true };
    return { success: false, error: res.error };
  });
}
