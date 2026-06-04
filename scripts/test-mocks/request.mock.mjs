function state() {
  if (!globalThis.__REQUEST_TEST_STATE__) {
    globalThis.__REQUEST_TEST_STATE__ = {};
  }
  return globalThis.__REQUEST_TEST_STATE__;
}

function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function ok(statusCode, data) {
  return Promise.resolve({ success: true, statusCode, data: clone(data) });
}

function fail(statusCode, error, data = null) {
  return Promise.resolve({ success: false, statusCode, error, data: clone(data) });
}

export default function request(method, url, body) {
  const current = state();
  current.requestLog = current.requestLog || [];
  current.requestLog.push({ method, url, body: clone(body) });

  if (method === 'GET' && url === '/api/health') {
    if (current.failHealth) {
      return fail(503, 'health failed', { error: 'health failed' });
    }
    return ok(200, { status: 'ok' });
  }

  if (method === 'POST' && url === '/api/users') {
    current.registerCalls = (current.registerCalls || 0) + 1;
    if (current.failRegister) {
      return fail(400, current.failRegister, { error: current.failRegister });
    }
    return ok(current.registerStatusCode || 201, { user_id: 'u-1' });
  }

  if (method === 'GET' && url === '/api/tasks') {
    if (current.failTaskAuthOnce && !current.failTaskAuthConsumed) {
      current.failTaskAuthConsumed = true;
      return fail(401, 'unauthorized', { error: 'unauthorized' });
    }
    return ok(200, { tasks: clone(current.serverTasks || []) });
  }

  if (method === 'POST' && url === '/api/tasks') {
    current.postBodies = current.postBodies || [];
    current.postBodies.push(clone(body));
    return ok(200, { success: true });
  }

  if (method === 'DELETE' && url.startsWith('/api/tasks/')) {
    return ok(200, { success: true });
  }

  if (method === 'GET' && url.startsWith('/api/tasks/') && url.endsWith('/history')) {
    const taskId = url.split('/')[3];
    return ok(200, { history: clone((current.serverHistoryByTask || {})[taskId] || {}) });
  }

  if (method === 'POST' && url.startsWith('/api/tasks/') && url.endsWith('/history')) {
    current.historyBodies = current.historyBodies || [];
    current.historyBodies.push(clone(body));
    return ok(200, { success: true });
  }

  return fail(404, `Unhandled request: ${method} ${url}`, { error: `Unhandled request: ${method} ${url}` });
}
