import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

// 深拷贝测试数据，避免后续断言受到引用修改的影响。
function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

// 构造最小可用的 uni 运行时，只保留同步测试需要的接口。
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
    getSystemInfoSync() {
      return {};
    },
  };
}
async function flushMicrotasks() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

async function withServer(aliases, run) {
  const server = await createServer({
    root: projectRoot,
    configFile: false,
    logLevel: 'error',
    server: { middlewareMode: true },
    plugins: [],
    resolve: {
      alias: aliases,
    },
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

async function loadTaskApi() {
  const aliases = [
    {
      find: /\/src\/api\/request\.js$/,
      replacement: path.join(projectRoot, 'scripts/test-mocks/request.mock.mjs'),
    },
  ];

  return withServer(aliases, (server) =>
    server.ssrLoadModule(`/src/api/task.js?t=${Date.now()}`)
  );
}

function resetTestState(overrides = {}) {
  globalThis.__SYNC_TEST_STATE__ = {
    remoteConfig: { api_base_url: 'http://test.local' },
    serverTasks: [],
    uploadCalls: [],
    deleteCalls: [],
    historyCalls: [],
    requestLog: [],
    postBodies: [],
    historyBodies: [],
    ...clone(overrides),
  };
}

async function testSyncToServerUploadsOnlyDirtyTasks() {
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
  assert.deepEqual(
    globalThis.__SYNC_TEST_STATE__.uploadCalls.map((item) => item.id),
    ['dirty-1', 'dirty-2']
  );
}

async function testSyncToServerFallsBackToAllTasksWhenNoDirtyFlagExists() {
  resetTestState();
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const localTasks = [
    { id: 'task-a', title: 'Task A', _syncDirty: false, createdAt: '2026-03-01T00:00:00.000Z' },
    { id: 'task-b', title: 'Task B', createdAt: '2026-03-02T00:00:00.000Z' },
  ];

  const result = await dataManager.syncToServer(localTasks);

  assert.equal(result.success, true);
  assert.equal(result.uploaded, 2);
  assert.deepEqual(
    globalThis.__SYNC_TEST_STATE__.uploadCalls.map((item) => item.id),
    ['task-a', 'task-b']
  );
}
async function testSyncFromServerPrefersServerVersionOnConflict() {
  resetTestState({
    serverTasks: [
      { id: 'same', title: 'Server Title', createdAt: '2026-03-03T00:00:00.000Z', color: 'blue' },
      { id: 'server-only', title: 'Server Only', createdAt: '2026-03-04T00:00:00.000Z' },
    ],
  });
  globalThis.uni = createMemoryUni();
  const dataManager = await loadDataManager();

  const localTasks = [
    { id: 'same', title: 'Local Title', createdAt: '2026-03-01T00:00:00.000Z', color: 'red' },
    { id: 'local-only', title: 'Local Only', createdAt: '2026-03-02T00:00:00.000Z' },
  ];

  const result = await dataManager.syncFromServer(localTasks);

  assert.equal(result.success, true);
  assert.equal(result.merged.length, 3);
  assert.equal(result.merged.find((item) => item.id === 'same').title, 'Server Title');
  assert.equal(result.merged.find((item) => item.id === 'same').color, 'blue');
  assert.equal(result.merged.find((item) => item.id === 'same')._syncDirty, false);
}

async function testSyncFromServerRecordsOverwriteHistory() {
  resetTestState({
    serverTasks: [
      {
        id: 'same',
        title: 'Server Title',
        note: 'Server Note',
        createdAt: '2026-03-03T00:00:00.000Z',
        importance: 'high',
        urgency: 'low',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_history: JSON.stringify([
      {
        task_id: 'same',
        field_name: 'text',
        field_value: 'Local Title',
        action: 'update',
        timestamp: '2026-03-02T00:00:00.000Z',
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const localTasks = [
    {
      id: 'same',
      title: 'Local Title',
      note: 'Local Note',
      createdAt: '2026-03-01T00:00:00.000Z',
      importance: 'low',
        urgency: 'low',
    },
  ];

  const result = await dataManager.syncFromServer(localTasks);
  const history = dataManager.loadTaskHistoryFromStorage();

  assert.equal(result.success, true);
  assert.ok(
    history.some((item) => item.task_id === 'same' && item.field_name === 'text' && item.field_value === 'Server Title')
  );
  assert.ok(
    history.some((item) => item.task_id === 'same' && item.field_name === 'notes' && item.field_value === 'Server Note')
  );
  assert.ok(
    history.some((item) => item.task_id === 'same' && item.field_name === 'importance' && item.field_value !== 'low')
  );
}

async function testSaveTaskOnlyMarksDirtyWithoutImmediateUpload() {
  resetTestState();
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
  await flushMicrotasks();

  const savedTask = result.tasks.find((item) => item.id === 'task-1');

  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls.length, 0);
  assert.equal(globalThis.__SYNC_TEST_STATE__.historyCalls.length, 0);
  assert.ok(savedTask.updatedAt);
  assert.notEqual(savedTask.updatedAt, '2026-03-01T00:00:00.000Z');
  assert.equal(savedTask._syncDirty, true);
}

async function testSavedDirtyTaskIsUploadedByManualSync() {
  resetTestState();
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'task-upload',
        title: 'Before edit',
        note: '',
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-01T00:00:00.000Z',
        dueDate: null,
        importance: 'low',
        urgency: 'low',
        _syncDirty: false,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  await dataManager.saveTask(
    {
      id: 'task-upload',
      title: 'After edit',
      note: 'Changed locally',
      createdAt: '2026-03-01T00:00:00.000Z',
      updatedAt: '2026-03-01T00:00:00.000Z',
      dueDate: null,
      importance: 'high',
      urgency: 'low',
    },
    false
  );

  const savedList = dataManager.loadTasksFromStorage();
  const uploadResult = await dataManager.syncToServer(savedList);
  const storedAfterUpload = dataManager.loadTasksFromStorage();
  const uploadedTask = storedAfterUpload.find((item) => item.id === 'task-upload');

  assert.equal(uploadResult.success, true);
  assert.equal(uploadResult.uploaded, 1);
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls.length, 1);
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls[0].id, 'task-upload');
  assert.equal(globalThis.__SYNC_TEST_STATE__.uploadCalls[0].title, 'After edit');
  assert.equal(uploadedTask._syncDirty, false);
}

async function testSyncFromServerDoesNotClearDirtyFlagForLocalOnlyTasks() {
  resetTestState({
    serverTasks: [
      {
        id: 'server-only',
        title: 'Server task',
        createdAt: '2026-03-03T00:00:00.000Z',
      },
    ],
  });
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'local-dirty',
        title: 'Local unsynced task',
        note: 'pending upload',
        createdAt: '2026-03-02T00:00:00.000Z',
        updatedAt: '2026-03-02T00:00:00.000Z',
        dueDate: null,
        importance: 'low',
        urgency: 'low',
        _syncDirty: true,
      },
    ]),
  });
  const dataManager = await loadDataManager();

  const localTasks = dataManager.loadTasksFromStorage();
  const result = await dataManager.syncFromServer(localTasks);
  const localDirtyTask = result.merged.find((item) => item.id === 'local-dirty');

  assert.equal(result.success, true);
  assert.ok(localDirtyTask);
  assert.equal(localDirtyTask._syncDirty, true);
}
async function testEditScreensDoNotForceImmediateRemoteSync() {
  const files = [
    'src/pages/edit.vue',
    'src/pages/index.vue',
    'src/pages/archive.vue',
  ];

  files.forEach((relativePath) => {
    const source = fs.readFileSync(path.join(projectRoot, relativePath), 'utf8');
    assert.doesNotMatch(source, /saveTask\([^\n]*,\s*true\)/);
    assert.doesNotMatch(source, /deleteTask\([^\n]*,\s*true\)/);
  });
}

async function testCreateOrUpdateTaskPreservesServerOnlyFields() {
  resetTestState({
    serverTasks: [
      {
        id: 'task-1',
        text: 'Server title',
        notes: 'Server note',
        due_date: '2026-03-02T00:00:00.000Z',
        importance: 'low',
        urgency: 'low',
        completed: false,
        completed_date: '',
        created_at: '2026-03-01T00:00:00.000Z',
        updated_at: '2026-03-01T00:00:00.000Z',
        position: { x: 120, y: 80 },
        directory: '/existing/path',
        color: '#00AAFF',
      },
    ],
  });
  const taskApi = await loadTaskApi();

  await taskApi.createOrUpdateTaskOnServer({
    id: 'task-1',
    title: 'Locally edited',
    note: 'Server note',
    dueDate: '2026-03-02T00:00:00.000Z',
    importance: 'high',
    urgency: 'low',
    isCompleted: false,
    completedAt: null,
    createdAt: '2026-03-01T00:00:00.000Z',
    updatedAt: '2026-03-09T10:00:00.000Z',
    position: { x: 200, y: 240 },
  });

  const payload = globalThis.__SYNC_TEST_STATE__.postBodies[0];
  assert.equal(payload.text, 'Locally edited');
  assert.notEqual(payload.importance, 'low');
  assert.equal(payload.updated_at, '2026-03-09T10:00:00.000Z');
  assert.equal(payload.directory, '/existing/path');
  assert.equal(payload.color, '#00AAFF');
}

async function testTaskFromServerAcceptsCompatibleFieldShapes() {
  resetTestState({
    serverTasks: [
      {
        id: 'compat-1',
        title: 'Edited from app',
        note: 'Changed note',
        dueDate: '2026-03-12T00:00:00.000Z',
        importance: 'high',
        urgency: '1',
        completed: 'false',
        completedAt: null,
        createdAt: '2026-03-01T00:00:00.000Z',
        updatedAt: '2026-03-11T10:00:00.000Z',
      },
      {
        id: 'compat-2',
        text: 'Done task',
        notes: 'Done note',
        due_date: '2026-03-13T00:00:00.000Z',
        importance: '?',
        urgency: '?',
        completed: '1',
        completed_date: '2026-03-11T11:00:00.000Z',
        created_at: '2026-03-02T00:00:00.000Z',
        updated_at: '2026-03-11T11:00:00.000Z',
      },
    ],
  });
  const taskApi = await loadTaskApi();

  const res = await taskApi.getTasksFromServer();
  const compat1 = res.tasks.find((item) => item.id === 'compat-1');
  const compat2 = res.tasks.find((item) => item.id === 'compat-2');

  assert.equal(res.success, true);
  assert.equal(compat1.title, 'Edited from app');
  assert.equal(compat1.note, 'Changed note');
  assert.equal(compat1.importance, 'high');
  assert.equal(compat1.urgency, 'high');
  assert.equal(compat1.isCompleted, false);
  assert.equal(compat1.updatedAt, '2026-03-11T10:00:00.000Z');
  assert.equal(compat2.isCompleted, true);
  assert.equal(compat2.completedAt, '2026-03-11T11:00:00.000Z');
}

function desktopShouldAdoptServerTask(localTask, serverTask) {
  if (!localTask) return true;
  return (serverTask.updated_at || '') > (localTask.updated_at || '');
}

async function testAppPayloadLetsDesktopBranchDetectRemoteUpdate() {
  resetTestState();
  globalThis.uni = createMemoryUni({
    task_list: JSON.stringify([
      {
        id: 'task-compat',
        title: 'Original',
        note: 'Note',
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
  const taskApi = await loadTaskApi();

  const saveResult = await dataManager.saveTask(
    {
      id: 'task-compat',
      title: 'Edited from app',
      note: 'Note',
      createdAt: '2026-03-01T00:00:00.000Z',
      updatedAt: '2026-03-01T00:00:00.000Z',
      dueDate: '2026-03-02T00:00:00.000Z',
      importance: 'low',
        urgency: 'low',
    },
    false
  );

  const savedTask = saveResult.tasks.find((item) => item.id === 'task-compat');
  const payload = taskApi.taskToServer(savedTask);
  const desktopLocalTask = {
    id: 'task-compat',
    text: 'Original',
    updated_at: '2026-03-01T00:00:00.000Z',
  };

  assert.equal(payload.text, 'Edited from app');
  assert.ok(payload.updated_at);
  assert.equal(desktopShouldAdoptServerTask(desktopLocalTask, payload), true);
}

const tests = [
  ['syncToServer uploads only dirty tasks', testSyncToServerUploadsOnlyDirtyTasks],
  ['syncToServer falls back to all tasks when no dirty flag exists', testSyncToServerFallsBackToAllTasksWhenNoDirtyFlagExists],
  ['syncFromServer prefers server version during conflicts', testSyncFromServerPrefersServerVersionOnConflict],
  ['syncFromServer records overwrite history when server wins conflicts', testSyncFromServerRecordsOverwriteHistory],
  ['saveTask only marks dirty without immediate upload', testSaveTaskOnlyMarksDirtyWithoutImmediateUpload],
  ['saved dirty task is uploaded by manual sync', testSavedDirtyTaskIsUploadedByManualSync],
  ['syncFromServer does not clear dirty flag for local-only tasks', testSyncFromServerDoesNotClearDirtyFlagForLocalOnlyTasks],
  ['edit screens do not force immediate remote sync', testEditScreensDoNotForceImmediateRemoteSync],
  ['createOrUpdateTaskOnServer preserves server-only fields', testCreateOrUpdateTaskPreservesServerOnlyFields],
  ['taskFromServer accepts compatible field shapes', testTaskFromServerAcceptsCompatibleFieldShapes],
  ['app payload lets desktop branch detect remote updates', testAppPayloadLetsDesktopBranchDetectRemoteUpdate],
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
