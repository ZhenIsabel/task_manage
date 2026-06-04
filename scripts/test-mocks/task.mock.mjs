function state() {
  if (!globalThis.__SYNC_TEST_STATE__) {
    globalThis.__SYNC_TEST_STATE__ = {};
  }
  return globalThis.__SYNC_TEST_STATE__;
}

function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

export function getTasksFromServer() {
  const current = state();
  if (current.failGetTasks) {
    return Promise.resolve({ success: false, error: current.failGetTasks });
  }

  return Promise.resolve({
    success: true,
    tasks: clone(current.serverTasks || []),
  });
}

export function healthCheck() {
  const current = state();
  current.healthChecks = (current.healthChecks || 0) + 1;
  if (current.failHealth) {
    return Promise.resolve({ success: false, error: current.failHealth });
  }
  return Promise.resolve({ success: true, data: { status: 'ok' } });
}

export function getTaskHistoryFromServer(taskId) {
  const current = state();
  current.historyFetchCalls = current.historyFetchCalls || [];
  current.historyFetchCalls.push(taskId);
  return Promise.resolve({
    success: true,
    history: clone((current.serverHistoryByTask || {})[taskId] || {}),
  });
}

export function createOrUpdateTaskOnServer(task) {
  const current = state();
  current.uploadCalls = current.uploadCalls || [];
  current.uploadCalls.push(clone(task));

  if (current.failUpload) {
    return Promise.resolve({ success: false, error: current.failUpload });
  }

  return Promise.resolve({ success: true });
}

export function deleteTaskOnServer(taskId) {
  const current = state();
  current.deleteCalls = current.deleteCalls || [];
  current.deleteCalls.push(taskId);
  if (current.failDelete) {
    return Promise.resolve({ success: false, error: current.failDelete });
  }
  return Promise.resolve({ success: true });
}

export function postTaskHistoryToServer(taskId, records) {
  const current = state();
  current.historyCalls = current.historyCalls || [];
  current.historyCalls.push({ taskId, records: clone(records || []) });
  return Promise.resolve({ success: true });
}

export function taskFromServer(task) {
  return clone(task);
}

export function taskToServer(task) {
  return clone(task);
}
