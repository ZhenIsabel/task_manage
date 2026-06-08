import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function createMemoryUni(initialStorage = {}) {
  const storage = new Map(Object.entries(initialStorage));
  return {
    getStorageSync(key) {
      return storage.get(key);
    },
    setStorageSync(key, value) {
      storage.set(key, value);
    },
    removeStorageSync(key) {
      storage.delete(key);
    },
    showToast() {},
    showModal() {},
    navigateBack() {},
    navigateTo() {},
    getSystemInfoSync() {
      return {};
    },
    request(options) {
      const current = globalThis.__REQUEST_TEST_STATE__ || {};
      const log = current.requestLog || (current.requestLog = []);
      log.push({
        method: options.method,
        url: options.url,
        data: clone(options.data),
        header: clone(options.header),
      });

      const ok = (statusCode, data) => {
        options.success && options.success({ statusCode, data });
      };
      const fail = (errMsg) => {
        options.fail && options.fail({ errMsg });
      };

      if (current.networkError) {
        fail(current.networkError);
        return;
      }

      const normalizedUrl = options.url.replace(/^https?:\/\/[^/]+/, '');
      if (options.method === 'GET' && normalizedUrl === '/api/health') {
        if (current.failHealth) {
          ok(503, { error: 'health failed' });
          return;
        }
        ok(200, { status: 'ok' });
        return;
      }

      if (options.method === 'POST' && normalizedUrl === '/api/users') {
        current.registerCalls = (current.registerCalls || 0) + 1;
        if (current.failRegister) {
          ok(400, { error: current.failRegister });
          return;
        }
        ok(current.registerStatusCode || 201, { user_id: 'u-1' });
        return;
      }

      if (options.method === 'GET' && normalizedUrl === '/api/tasks') {
        if (current.failTaskAuthOnce && !current.failTaskAuthConsumed) {
          current.failTaskAuthConsumed = true;
          ok(401, { error: 'unauthorized' });
          return;
        }
        ok(200, { tasks: clone(current.serverTasks || []) });
        return;
      }

      if (options.method === 'POST' && normalizedUrl === '/api/tasks') {
        current.postBodies = current.postBodies || [];
        current.postBodies.push(clone(options.data));
        ok(200, { success: true });
        return;
      }

      if (options.method === 'DELETE' && normalizedUrl.startsWith('/api/tasks/')) {
        ok(200, { success: true });
        return;
      }

      if (options.method === 'GET' && /\/api\/tasks\/[^/]+\/history$/.test(normalizedUrl)) {
        const taskId = normalizedUrl.split('/')[3];
        ok(200, { history: clone((current.serverHistoryByTask || {})[taskId] || {}) });
        return;
      }

      if (options.method === 'POST' && /\/api\/tasks\/[^/]+\/history$/.test(normalizedUrl)) {
        current.historyBodies = current.historyBodies || [];
        current.historyBodies.push(clone(options.data));
        ok(200, { success: true });
        return;
      }

      ok(404, { error: `Unhandled request: ${options.method} ${normalizedUrl}` });
    },
  };
}

async function withServer(aliases, run) {
  const server = await createServer({
    root: projectRoot,
    configFile: false,
    logLevel: 'error',
    server: { middlewareMode: true },
    plugins: [],
    resolve: { alias: aliases },
  });

  try {
    return await run(server);
  } finally {
    await server.close();
  }
}

async function loadDataManager() {
  const aliases = [
    {
      find: /\/src\/api\/config\.js$/,
      replacement: path.join(projectRoot, 'scripts/test-mocks/config.mock.mjs'),
    },
    {
      find: /\/src\/api\/task\.js$/,
      replacement: path.join(projectRoot, 'scripts/test-mocks/task.mock.mjs'),
    },
  ];

  return withServer(aliases, (server) =>
    server.ssrLoadModule(`/src/services/dataManager.js?t=${Date.now()}`)
  );
}

async function loadRequestModule() {
  return withServer([], (server) =>
    server.ssrLoadModule(`/src/api/request.js?t=${Date.now()}`)
  );
}

async function loadTaskApiModule() {
  return withServer([], (server) =>
    server.ssrLoadModule(`/src/api/task.js?t=${Date.now()}`)
  );
}

async function loadTaskHistoryModule() {
  return withServer([], (server) =>
    server.ssrLoadModule(`/src/utils/taskHistory.js?t=${Date.now()}`)
  );
}

function resetSyncState(overrides = {}) {
  globalThis.__SYNC_TEST_STATE__ = {
    remoteConfig: {
      enabled: true,
      api_base_url: 'http://test.local',
      api_token: 'token-1',
      username: 'tester',
    },
    serverTasks: [],
    uploadCalls: [],
    deleteCalls: [],
    historyCalls: [],
    historyFetchCalls: [],
    serverHistoryByTask: {},
    healthChecks: 0,
    ...clone(overrides),
  };
}

function resetRequestState(overrides = {}) {
  globalThis.__REQUEST_TEST_STATE__ = {
    serverTasks: [],
    requestLog: [],
    registerCalls: 0,
    postBodies: [],
    historyBodies: [],
    serverHistoryByTask: {},
    ...clone(overrides),
  };
}

async function testHasRemoteConfigRequiresUsernameAndToken() {
  resetSyncState({ remoteConfig: { enabled: true, api_base_url: 'http://test.local', api_token: '', username: '' } });
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  assert.equal(dataManager.hasRemoteConfig(), false);
}

async function testBootstrapRemoteSyncChecksHealthBeforePull() {
  resetSyncState({
    serverTasks: [
      {
        id: 'remote-1',
        title: 'Remote Task',
        createdAt: '2026-03-02T00:00:00.000Z',
        updatedAt: '2026-03-02T00:00:00.000Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const result = await dataManager.bootstrapRemoteSync();
  const tasks = dataManager.loadTasksFromStorage();

  assert.equal(result.success, true);
  assert.equal(result.pendingChanges.length, 0);
  assert.equal(globalThis.__SYNC_TEST_STATE__.healthChecks, 1);
  assert.equal(tasks.length, 1);
  assert.equal(tasks[0].id, 'remote-1');
}

async function testBootstrapRemoteSyncStopsWhenHealthFails() {
  resetSyncState({ failHealth: 'health failed' });
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const result = await dataManager.bootstrapRemoteSync();

  assert.equal(result.success, false);
  assert.match(result.error || '', /health/i);
}

async function testSyncFromServerCreatesPendingConflictInsteadOfOverwritingLocal() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote Title',
        note: 'Remote note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-03T00:00:00.000Z',
        importance: 'high',
        urgency: 'low',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local Title',
        note: 'Local note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-02T00:00:00.000Z',
        importance: 'low',
        urgency: 'low',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const localTasks = dataManager.loadTasksFromStorage();
  const result = await dataManager.syncFromServer(localTasks);
  const stored = dataManager.loadTasksFromStorage();
  const pending = dataManager.getPendingRemoteTaskChanges();

  assert.equal(result.success, true);
  assert.equal(result.pendingChanges.length, 1);
  assert.equal(stored[0].title, 'Local Title');
  assert.equal(pending[0].id, 'same');
  assert.equal(pending[0].remoteTask.title, 'Remote Title');
}

async function testResolvePendingConflictAcceptingRemoteOverwritesLocalAndStoresHistory() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote Title',
        note: 'Remote note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-03T00:00:00.000Z',
        importance: 'high',
        urgency: 'low',
      },
    ],
    serverHistoryByTask: {
      same: {
        text: [
          { value: 'Remote Title', action: 'update', timestamp: '2026-03-03T00:00:00.000Z' },
        ],
      },
    },
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local Title',
        note: 'Local note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-02T00:00:00.000Z',
        importance: 'low',
        urgency: 'low',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const resolution = await dataManager.resolvePendingRemoteTaskChanges(['same'], []);
  const stored = dataManager.loadTasksFromStorage();
  const history = dataManager.loadTaskHistoryFromStorage();

  assert.equal(resolution.success, true);
  assert.equal(dataManager.getPendingRemoteTaskChanges().length, 0);
  assert.equal(stored[0].title, 'Remote Title');
  assert.ok(history.some((item) => item.task_id === 'same' && item.field_name === 'text' && item.field_value === 'Remote Title'));
}

async function testResolvePendingConflictAcceptingLocalReuploadsLocalTask() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote Title',
        note: 'Remote note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-03T00:00:00.000Z',
        importance: 'high',
        urgency: 'low',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local Title',
        note: 'Local note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-02T00:00:00.000Z',
        importance: 'low',
        urgency: 'low',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const resolution = await dataManager.resolvePendingRemoteTaskChanges([], ['same']);
  const stored = dataManager.loadTasksFromStorage();

  assert.equal(resolution.success, true);
  assert.equal(stored[0].title, 'Local Title');
  assert.equal(stored[0]._syncDirty, false);
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls.length, 1);
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls[0].title, 'Local Title');
}

async function testSyncToServerUploadsOnlyDirtyTasks() {
  resetSyncState();
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const localTasks = [
    { id: 'dirty-1', title: 'Dirty 1', _syncDirty: true, createdAt: '2026-03-01T00:00:00.000Z' },
    { id: 'clean-1', title: 'Clean 1', _syncDirty: false, createdAt: '2026-03-02T00:00:00.000Z' },
    { id: 'dirty-2', title: 'Dirty 2', _syncDirty: true, createdAt: '2026-03-03T00:00:00.000Z' },
  ];

  const result = await dataManager.syncToServer(localTasks);

  assert.equal(result.success, true);
  assert.equal(result.uploaded, 2);
  assert.deepEqual(globalThis.__SYNC_TEST_STATE__.uploadCalls.map((item) => item.id), ['dirty-1', 'dirty-2']);
}

async function testSyncToServerNoOpsWhenNoDirtyTasks() {
  resetSyncState();
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const result = await dataManager.syncToServer([
    { id: 'clean-1', title: 'Clean 1', _syncDirty: false, createdAt: '2026-03-01T00:00:00.000Z' },
    { id: 'clean-2', title: 'Clean 2', _syncDirty: false, createdAt: '2026-03-02T00:00:00.000Z' },
  ]);

  assert.equal(result.success, true);
  assert.equal(result.uploaded, 0);
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls.length, 0);
}

async function testDeleteTaskCreatesTombstoneWithoutImmediateRemoteDelete() {
  resetSyncState();
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'task-delete',
        title: 'Delete me',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-01T00:00:00.000Z',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.deleteTask('task-delete', false);
  const stored = dataManager.loadTasksFromStorage();

  assert.equal(result.success, true);
  assert.equal(result.tasks.some((task) => task.id === 'task-delete'), false);
  assert.equal(globalThis.__SYNC_TEST_STATE__.deleteCalls.length, 0);
  assert.equal(stored.length, 1);
  assert.equal(stored[0].id, 'task-delete');
  assert.equal(stored[0].deleted, true);
  assert.equal(stored[0]._syncDirty, true);
  assert.ok(stored[0].updatedAt);
}

async function testSyncToServerDeletesDirtyTombstoneAndKeepsItOnFailure() {
  resetSyncState({ failDelete: 'delete failed' });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'task-delete',
        title: 'Delete me',
        deleted: true,
        updatedAt: '2026-03-02T00:00:00.000Z',
        _syncDirty: true,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const failed = await dataManager.syncToServer(dataManager.loadTasksFromStorage());
  const afterFailed = dataManager.loadTasksFromStorage()[0];

  assert.equal(failed.success, false);
  assert.deepEqual(globalThis.__SYNC_TEST_STATE__.deleteCalls, ['task-delete']);
  assert.equal(afterFailed.deleted, true);
  assert.equal(afterFailed._syncDirty, true);

  resetSyncState();
  const retried = await dataManager.syncToServer(dataManager.loadTasksFromStorage());
  const afterRetried = dataManager.loadTasksFromStorage()[0];

  assert.equal(retried.success, true);
  assert.equal(retried.uploaded, 1);
  assert.equal(afterRetried.deleted, true);
  assert.equal(afterRetried._syncDirty, false);
}

async function testSyncFromServerPreservesExistingPendingWithoutOverwriting() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote newer title',
        updatedAt: '2026-03-04T00:00:00.000Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local title',
        updatedAt: '2026-03-02T00:00:00.000Z',
        _syncDirty: false,
      },
    ]),
    task_pending_remote_changes: JSON.stringify([
      {
        id: 'same',
        title: 'Existing conflict',
        localTask: { id: 'same', title: 'Local title' },
        remoteTask: { id: 'same', title: 'Previous remote title' },
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const stored = dataManager.loadTasksFromStorage();
  const pending = dataManager.getPendingRemoteTaskChanges();

  assert.equal(result.success, true);
  assert.equal(result.pendingChanges.length, 1);
  assert.equal(stored[0].title, 'Local title');
  assert.equal(pending[0].remoteTask.title, 'Previous remote title');
}

async function testSyncToServerSkipsPendingConflictTasks() {
  resetSyncState();
  globalThis.uni = createMemoryUni({
    task_pending_remote_changes: JSON.stringify([
      { id: 'pending-1', localTask: { id: 'pending-1' }, remoteTask: { id: 'pending-1' } },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.syncToServer([
    { id: 'pending-1', title: 'Pending', _syncDirty: true, updatedAt: '2026-03-03T00:00:00.000Z' },
    { id: 'dirty-1', title: 'Dirty', _syncDirty: true, updatedAt: '2026-03-03T00:00:00.000Z' },
  ]);

  assert.equal(result.success, true);
  assert.equal(result.uploaded, 1);
  assert.deepEqual(globalThis.__SYNC_TEST_STATE__.uploadCalls.map((item) => item.id), ['dirty-1']);
}

async function testSyncFromServerAppliesRemoteDeletedForCleanLocalTask() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote deleted',
        deleted: true,
        updatedAt: '2026-03-03T00:00:00.000Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local task',
        deleted: false,
        updatedAt: '2026-03-02T00:00:00.000Z',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const stored = dataManager.loadTasksFromStorage();

  assert.equal(result.success, true);
  assert.equal(result.pendingChanges.length, 0);
  assert.equal(stored[0].deleted, true);
  assert.equal(stored[0]._syncDirty, false);
}

async function testSyncFromServerCreatesConflictForRemoteDeletedDirtyLocalTask() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote deleted',
        deleted: true,
        updatedAt: '2026-03-03T00:00:00.000Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Locally edited',
        deleted: false,
        updatedAt: '2026-03-02T00:00:00.000Z',
        _syncDirty: true,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const stored = dataManager.loadTasksFromStorage();
  const pending = dataManager.getPendingRemoteTaskChanges();

  assert.equal(result.success, true);
  assert.equal(result.pendingChanges.length, 1);
  assert.equal(stored[0].deleted, false);
  assert.equal(pending[0].remoteTask.deleted, true);
}

async function testSyncFromServerTreatsMissingCleanLocalTaskAsRemoteDelete() {
  resetSyncState({ serverTasks: [] });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'missing',
        title: 'Missing remotely',
        deleted: false,
        updatedAt: '2026-03-02T00:00:00.000Z',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.syncFromServer(dataManager.loadTasksFromStorage());
  const stored = dataManager.loadTasksFromStorage();

  assert.equal(stored[0].deleted, true);
  assert.equal(stored[0]._syncDirty, false);
}

async function testSyncFromServerComparesTimezoneAwareTimestamps() {
  resetSyncState({
    serverTasks: [
      {
        id: 'same',
        title: 'Remote later',
        updatedAt: '2026-04-14T15:00:00Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'same',
        title: 'Local earlier',
        updatedAt: '2026-04-14T20:00:00+08:00',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.syncFromServer(dataManager.loadTasksFromStorage());

  assert.equal(result.pendingChanges.length, 1);
  assert.equal(dataManager.getPendingRemoteTaskChanges()[0].remoteTask.title, 'Remote later');
}

async function testSyncToServerUploadsDirtyTaskHistory() {
  resetSyncState();
  globalThis.uni = createMemoryUni({
    task_history: JSON.stringify([
      {
        task_id: 'dirty-1',
        field_name: 'text',
        field_value: 'Dirty title',
        action: 'update',
        timestamp: '2026-03-03T00:00:00.000Z',
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.syncToServer([
    { id: 'dirty-1', title: 'Dirty title', _syncDirty: true, updatedAt: '2026-03-03T00:00:00.000Z' },
  ]);

  assert.deepEqual(globalThis.__SYNC_TEST_STATE__.uploadCalls[0].history, {
    text: [{ value: 'Dirty title', action: 'update', timestamp: '2026-03-03T00:00:00.000Z' }],
  });
}

async function testSyncToServerUploadsNonDisplayTaskHistoryFields() {
  resetSyncState();
  globalThis.uni = createMemoryUni({
    task_history: JSON.stringify([
      {
        task_id: 'dirty-1',
        field_name: 'color',
        field_value: '#ef4444',
        action: 'update',
        timestamp: '2026-03-03T00:00:00.000Z',
      },
      {
        task_id: 'dirty-1',
        field_name: 'position',
        field_value: '{"x":120,"y":240}',
        action: 'update',
        timestamp: '2026-03-03T00:01:00.000Z',
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.syncToServer([
    { id: 'dirty-1', title: 'Dirty title', _syncDirty: true, updatedAt: '2026-03-03T00:00:00.000Z' },
  ]);

  assert.deepEqual(globalThis.__SYNC_TEST_STATE__.uploadCalls[0].history, {
    color: [{ value: '#ef4444', action: 'update', timestamp: '2026-03-03T00:00:00.000Z' }],
    position: [{ value: '{"x":120,"y":240}', action: 'update', timestamp: '2026-03-03T00:01:00.000Z' }],
  });
}

async function testSaveTaskOnlyMarksDirtyWithoutImmediateUpload() {
  resetSyncState();
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'task-1',
        title: 'Old title',
        note: 'Old note',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-01T00:00:00.000Z',
        dueDate: '2026-03-02T00:00:00.000Z',
        importance: 'low',
        urgency: 'low',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const result = await dataManager.saveTask(
    {
      id: 'task-1',
      title: 'New title',
      note: 'Old note',
      createdAt: '2026-03-01T00:00:00.000Z',
      updatedAt: '2026-03-01T00:00:00.000Z',
      dueDate: '2026-03-02T00:00:00.000Z',
      importance: 'high',
      urgency: 'low',
    },
    false
  );

  const savedTask = result.tasks.find((item) => item.id === 'task-1');

  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls.length, 0);
  assert.equal(savedTask._syncDirty, true);
  assert.ok(savedTask.updatedAt);

  const history = dataManager.loadTaskHistoryFromStorage();
  assert.ok(history.some((item) => item.task_id === 'task-1' && item.field_name === 'importance' && item.field_value === '高'));
}

async function testTaskApiMapsDeletedAndHistoryPayload() {
  resetRequestState();
  globalThis.uni = createMemoryUni({
    task_remote_config: JSON.stringify({
      enabled: true,
      api_base_url: 'http://test.local',
      api_token: 'token-1',
      username: 'tester',
    }),
  });
  const taskApi = await loadTaskApiModule();

  const local = taskApi.taskFromServer({
    id: 'deleted-1',
    text: 'Deleted remote',
    deleted: true,
    updated_at: '2026-03-03T00:00:00.000Z',
  });
  const server = taskApi.taskToServer({
    id: 'deleted-1',
    title: 'Deleted remote',
    deleted: true,
    updatedAt: '2026-03-03T00:00:00.000Z',
    history: {
      text: [{ value: 'Deleted remote', action: 'update', timestamp: '2026-03-03T00:00:00.000Z' }],
    },
  });

  assert.equal(local.deleted, true);
  assert.equal(server.deleted, true);
  assert.deepEqual(server.history, {
    text: [{ value: 'Deleted remote', action: 'update', timestamp: '2026-03-03T00:00:00.000Z' }],
  });
}

async function testDetailHistoryDisplaySupportsLegacyAndServerImportanceValues() {
  const { mergeDisplayHistory, buildHistoryTimeline } = await loadTaskHistoryModule();
  const timeline = buildHistoryTimeline(mergeDisplayHistory({
    importance: [
      { value: 'high', action: 'create', timestamp: '2026-05-01T08:00:00.000Z' },
      { value: '低', action: 'update', timestamp: '2026-05-01T08:05:00.000Z' },
    ],
    urgency: [
      { value: '高', action: 'create', timestamp: '2026-05-01T08:00:00.000Z' },
      { value: 'low', action: 'update', timestamp: '2026-05-01T08:05:00.000Z' },
    ],
  }, {}));
  const details = timeline.flatMap((event) => event.details || []);

  assert.deepEqual(details.filter((detail) => detail.field === '重要程度'), [
    { field: '重要程度', oldVal: '重要', newVal: '一般' },
    { field: '重要程度', oldVal: '', newVal: '重要' },
  ]);
  assert.deepEqual(details.filter((detail) => detail.field === '紧急程度'), [
    { field: '紧急程度', oldVal: '紧急', newVal: '不急' },
    { field: '紧急程度', oldVal: '', newVal: '紧急' },
  ]);
}

async function testTaskHistoryTimelineShowsOnlyDisplayFields() {
  const { mergeDisplayHistory, buildHistoryTimeline } = await loadTaskHistoryModule();

  const merged = mergeDisplayHistory(
    {
      text: [{ value: '准备方案', action: 'create', timestamp: '2026-05-01T08:00:00.000Z' }],
      notes: [{ value: '同步备注', action: 'update', timestamp: '2026-05-01T08:05:00.000Z' }],
      color: [{ value: '#ef4444', action: 'update', timestamp: '2026-05-01T08:10:00.000Z' }],
      position: [{ value: { x: 120, y: 240 }, action: 'update', timestamp: '2026-05-01T08:10:00.000Z' }],
    },
    {
      due_date: [{ value: '2026-05-09', action: 'update', timestamp: '2026-05-01T08:15:00.000Z' }],
      urgency: [{ value: '高', action: 'update', timestamp: '2026-05-01T08:20:00.000Z' }],
      color: [{ value: '#10b981', action: 'update', timestamp: '2026-05-01T08:25:00.000Z' }],
    }
  );
  const timeline = buildHistoryTimeline(merged);
  const displayedFields = timeline.flatMap((event) => (event.details || []).map((detail) => detail.field));

  assert.deepEqual(
    new Set(displayedFields),
    new Set(['任务内容', '备注', '截止日期', '紧急程度'])
  );
  assert.ok(!displayedFields.includes('color'));
  assert.ok(!displayedFields.includes('position'));
}

async function testTaskHistoryTimelineDedupesIdenticalLocalAndServerRecords() {
  const { mergeDisplayHistory, buildHistoryTimeline } = await loadTaskHistoryModule();
  const sameRecord = { value: '准备方案', action: 'update', timestamp: '2026-05-01T08:00:00.000Z' };

  const merged = mergeDisplayHistory(
    { text: [sameRecord] },
    { text: [{ ...sameRecord }] }
  );
  const timeline = buildHistoryTimeline(merged);
  const details = timeline.flatMap((event) => event.details || []);

  assert.equal(timeline.length, 1);
  assert.equal(details.length, 1);
  assert.deepEqual(details[0], {
    field: '任务内容',
    oldVal: '',
    newVal: '准备方案',
  });
}

async function testTaskHistoryTimelineSkipsDetailsWhenFormattedValuesMatch() {
  const { mergeDisplayHistory, buildHistoryTimeline } = await loadTaskHistoryModule();

  const merged = mergeDisplayHistory(
    {
      importance: [
        { value: 'high', action: 'update', timestamp: '2026-05-01T08:00:00.000Z' },
        { value: '高', action: 'update', timestamp: '2026-05-01T08:05:00.000Z' },
        { value: true, action: 'update', timestamp: '2026-05-01T08:10:00.000Z' },
      ],
      notes: [{ value: '补充说明', action: 'update', timestamp: '2026-05-01T08:05:00.000Z' }],
      due_date: [
        { value: '2026-05-09', action: 'update', timestamp: '2026-05-01T08:15:00.000Z' },
        { value: '2026-05-09T00:00:00.000Z', action: 'update', timestamp: '2026-05-01T08:20:00.000Z' },
      ],
    },
    {}
  );
  const timeline = buildHistoryTimeline(merged);
  const sameTimestampEvent = timeline.find((event) => event.timestamp === '2026-05-01T08:05:00.000Z');

  assert.ok(sameTimestampEvent);
  assert.deepEqual(sameTimestampEvent.details, [
    { field: '备注', oldVal: '', newVal: '补充说明' },
  ]);
  const allDetails = timeline.flatMap((event) => event.details || []);
  assert.equal(allDetails.filter((detail) => detail.field === '重要程度').length, 1);
  assert.equal(allDetails.filter((detail) => detail.field === '截止日期').length, 1);
  assert.ok(!allDetails.some((detail) => detail.oldVal === detail.newVal));
}

async function testTaskHistoryTimelineDoesNotCreateEmptyEventsAfterFiltering() {
  const { mergeDisplayHistory, buildHistoryTimeline } = await loadTaskHistoryModule();

  const merged = mergeDisplayHistory(
    {
      text: [{ value: '准备方案', action: 'create', timestamp: '2026-05-01T08:00:00.000Z' }],
      color: [{ value: '#ef4444', action: 'update', timestamp: '2026-05-01T08:10:00.000Z' }],
      position: [{ value: { x: 120, y: 240 }, action: 'update', timestamp: '2026-05-01T08:10:00.000Z' }],
      importance: [{ value: 'high', action: 'update', timestamp: '2026-05-01T08:20:00.000Z' }],
    },
    {
      importance: [{ value: '高', action: 'update', timestamp: '2026-05-01T08:25:00.000Z' }],
    }
  );
  const timeline = buildHistoryTimeline(merged);
  const timestamps = timeline.map((event) => event.timestamp);

  assert.deepEqual(new Set(timestamps), new Set([
    '2026-05-01T08:00:00.000Z',
    '2026-05-01T08:20:00.000Z',
  ]));
  assert.ok(timeline.every((event) => (event.details || []).length > 0));
}

async function testArchiveTaskRowsOpenDetailAndRestoreTapStaysLocal() {
  const source = fs.readFileSync(path.join(projectRoot, 'src/pages/archive.vue'), 'utf8');

  assert.match(source, /class="glass-card archive-item"[^>]*@tap="goDetail\(task\)"/);
  assert.match(source, /class="btn-restore"[^>]*@tap\.stop="handleRestore\(task\.id\)"/);
  assert.match(source, /function goDetail\(task\)/);
  assert.match(source, /\/pages\/detail\?id=/);
}

async function testCompletedDetailUsesRestoreActionInsteadOfEditOrDelete() {
  const source = fs.readFileSync(path.join(projectRoot, 'src/pages/detail.vue'), 'utf8');

  assert.match(source, /const isCompletedTask = computed\(\(\) => !!task\.isCompleted\)/);
  assert.match(source, /@tap="handleHeaderAction"/);
  assert.match(source, /:type="isCompletedTask \? 'redo' : 'compose'"/);
  assert.match(source, /function restoreTask\(\)/);
  assert.match(source, /saveTask\(updated,\s*false\)/);
  assert.doesNotMatch(source, /deleteTask\(/);
}

async function testEditScreensDoNotForceImmediateRemoteSync() {
  const files = ['src/pages/edit.vue', 'src/pages/index.vue', 'src/pages/archive.vue'];

  files.forEach((relativePath) => {
    const source = fs.readFileSync(path.join(projectRoot, relativePath), 'utf8');
    assert.doesNotMatch(source, /saveTask\([^\n]*,\s*true\)/);
    assert.doesNotMatch(source, /deleteTask\([^\n]*,\s*true\)/);
  });
}

async function testIndexRefreshesPendingConflictCountFromReactiveState() {
  const source = fs.readFileSync(path.join(projectRoot, 'src/pages/index.vue'), 'utf8');

  assert.match(source, /const pendingConflictCount = ref\(0\)/);
  assert.match(source, /function refreshPendingConflictCount\(\)/);
  assert.match(source, /pendingConflictCount\.value = dataManager\.getPendingRemoteTaskChanges\(\)\.length/);
  assert.doesNotMatch(source, /const pendingConflictCount = computed\(\(\) => dataManager\.getPendingRemoteTaskChanges\(\)\.length\)/);
}

async function testRequestAutoRegistersAfter401() {
  resetRequestState({
    failTaskAuthOnce: true,
    serverTasks: [
      {
        id: 'remote-1',
        text: 'Remote title',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_remote_config: JSON.stringify({
      enabled: true,
      api_base_url: 'http://test.local',
      api_token: 'token-1',
      username: 'tester',
    }),
  });
  const requestModule = await loadRequestModule();
  requestModule.resetRemoteAuthState();

  const result = await requestModule.request('GET', '/api/tasks');

  assert.equal(result.success, true);
  assert.equal(((result.data || {}).tasks || []).length, 1);
  assert.equal(globalThis.__REQUEST_TEST_STATE__.registerCalls, 1);
  assert.deepEqual(
    globalThis.__REQUEST_TEST_STATE__.requestLog.map((item) => `${item.method} ${item.url.replace(/^https?:\/\/[^/]+/, '')}`),
    ['GET /api/tasks', 'POST /api/users', 'GET /api/tasks']
  );
}

const tests = [
  ['hasRemoteConfig requires username and token', testHasRemoteConfigRequiresUsernameAndToken],
  ['bootstrapRemoteSync checks health before pull', testBootstrapRemoteSyncChecksHealthBeforePull],
  ['bootstrapRemoteSync stops when health fails', testBootstrapRemoteSyncStopsWhenHealthFails],
  ['syncFromServer creates pending conflict instead of overwriting local', testSyncFromServerCreatesPendingConflictInsteadOfOverwritingLocal],
  ['resolvePendingRemoteTaskChanges accepting remote overwrites local and stores history', testResolvePendingConflictAcceptingRemoteOverwritesLocalAndStoresHistory],
  ['resolvePendingRemoteTaskChanges accepting local reuploads local task', testResolvePendingConflictAcceptingLocalReuploadsLocalTask],
  ['syncToServer uploads only dirty tasks', testSyncToServerUploadsOnlyDirtyTasks],
  ['syncToServer no-ops when no dirty tasks', testSyncToServerNoOpsWhenNoDirtyTasks],
  ['deleteTask creates tombstone without immediate remote delete', testDeleteTaskCreatesTombstoneWithoutImmediateRemoteDelete],
  ['syncToServer deletes dirty tombstone and keeps it on failure', testSyncToServerDeletesDirtyTombstoneAndKeepsItOnFailure],
  ['syncFromServer preserves existing pending without overwriting', testSyncFromServerPreservesExistingPendingWithoutOverwriting],
  ['syncToServer skips pending conflict tasks', testSyncToServerSkipsPendingConflictTasks],
  ['syncFromServer applies remote deleted for clean local task', testSyncFromServerAppliesRemoteDeletedForCleanLocalTask],
  ['syncFromServer creates conflict for remote deleted dirty local task', testSyncFromServerCreatesConflictForRemoteDeletedDirtyLocalTask],
  ['syncFromServer treats missing clean local task as remote delete', testSyncFromServerTreatsMissingCleanLocalTaskAsRemoteDelete],
  ['syncFromServer compares timezone-aware timestamps', testSyncFromServerComparesTimezoneAwareTimestamps],
  ['syncToServer uploads dirty task history', testSyncToServerUploadsDirtyTaskHistory],
  ['syncToServer uploads non-display task history fields', testSyncToServerUploadsNonDisplayTaskHistoryFields],
  ['saveTask only marks dirty without immediate upload', testSaveTaskOnlyMarksDirtyWithoutImmediateUpload],
  ['task API maps deleted and history payload', testTaskApiMapsDeletedAndHistoryPayload],
  ['detail history display supports legacy and server importance values', testDetailHistoryDisplaySupportsLegacyAndServerImportanceValues],
  ['task history timeline shows only display fields', testTaskHistoryTimelineShowsOnlyDisplayFields],
  ['task history timeline dedupes identical local and server records', testTaskHistoryTimelineDedupesIdenticalLocalAndServerRecords],
  ['task history timeline skips details when formatted values match', testTaskHistoryTimelineSkipsDetailsWhenFormattedValuesMatch],
  ['task history timeline does not create empty events after filtering', testTaskHistoryTimelineDoesNotCreateEmptyEventsAfterFiltering],
  ['archive task rows open detail and restore tap stays local', testArchiveTaskRowsOpenDetailAndRestoreTapStaysLocal],
  ['completed detail uses restore action instead of edit or delete', testCompletedDetailUsesRestoreActionInsteadOfEditOrDelete],
  ['edit screens do not force immediate remote sync', testEditScreensDoNotForceImmediateRemoteSync],
  ['index refreshes pending conflict count from reactive state', testIndexRefreshesPendingConflictCountFromReactiveState],
  ['request auto-registers after 401', testRequestAutoRegistersAfter401],
];

async function main() {
  const failures = [];

  for (const [name, testFn] of tests) {
    try {
      await testFn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push({ name, error });
      console.error(`FAIL ${name}`);
      console.error(error);
    }
  }

  if (failures.length > 0) {
    process.exitCode = 1;
    return;
  }

  console.log(`Passed ${tests.length} sync tests.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
