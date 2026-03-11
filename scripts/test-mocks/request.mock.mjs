// 读取测试共享状态。
function state() {
  if (!globalThis.__SYNC_TEST_STATE__) {
    globalThis.__SYNC_TEST_STATE__ = {};
  }
  return globalThis.__SYNC_TEST_STATE__;
}

// 深拷贝请求和响应中的对象，避免后续被意外修改。
function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

// 构造统一的成功响应。
function ok(data) {
  return Promise.resolve({ success: true, data });
}

// 模拟 request，根据接口路径返回预设结果。
export default function request(method, url, body) {
  const current = state();
  current.requestLog = current.requestLog || [];
  // 保留原始请求日志，方便测试失败时排查。
  current.requestLog.push({
    method,
    url,
    body: clone(body),
  });

  if (method === 'GET' && url === '/api/tasks') {
    return ok({ tasks: clone(current.serverTasks || []) });
  }

  if (method === 'POST' && url === '/api/tasks') {
    current.postBodies = current.postBodies || [];
    current.postBodies.push(clone(body));
    return ok({});
  }

  if (method === 'DELETE' && url.startsWith('/api/tasks/')) {
    return ok({});
  }

  if (method === 'GET' && url.startsWith('/api/tasks/') && url.endsWith('/history')) {
    return ok({ history: {} });
  }

  if (method === 'POST' && url.startsWith('/api/tasks/') && url.endsWith('/history')) {
    current.historyBodies = current.historyBodies || [];
    current.historyBodies.push(clone(body));
    return ok({});
  }

  if (method === 'GET' && url === '/api/health') {
    return ok({});
  }

  return Promise.resolve({ success: false, error: `Unhandled request: ${method} ${url}` });
}
