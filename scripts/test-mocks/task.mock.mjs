// 统一读取测试共享状态。
function state() {
  if (!globalThis.__SYNC_TEST_STATE__) {
    globalThis.__SYNC_TEST_STATE__ = {};
  }
  return globalThis.__SYNC_TEST_STATE__;
}

// 深拷贝测试数据，避免引用被后续步骤污染。
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

export function createOrUpdateTaskOnServer(task) {
  const current = state();
  current.uploadCalls = current.uploadCalls || [];
  // 记录每次上传入参，供测试断言检查。
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
  return Promise.resolve({ success: true });
}

export function postTaskHistoryToServer(taskId, records) {
  const current = state();
  current.historyCalls = current.historyCalls || [];
  current.historyCalls.push({
    taskId,
    records: clone(records || []),
  });
  return Promise.resolve({ success: true });
}

export function taskFromServer(task) {
  return clone(task);
}

export function taskToServer(task) {
  return clone(task);
}
