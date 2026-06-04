import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

async function withServer(run) {
  const server = await createServer({
    root: projectRoot,
    configFile: false,
    logLevel: 'error',
    server: { middlewareMode: true },
    plugins: [],
  });

  try {
    return await run(server);
  } finally {
    await server.close();
  }
}

async function loadArchiveSearchModule() {
  return withServer((server) =>
    server.ssrLoadModule(`/src/utils/archiveSearch.js?t=${Date.now()}`)
  );
}

async function testFiltersCompletedTitlesByAllSpaceSeparatedKeywords() {
  const { filterArchivedTasks } = await loadArchiveSearchModule();
  const tasks = [
    { id: '1', title: '准备项目汇报PPT', isCompleted: true },
    { id: '2', title: '准备周报', isCompleted: true },
    { id: '3', title: '项目复盘', isCompleted: true },
    { id: '4', title: '准备项目计划', isCompleted: false },
    { id: '5', title: '已删除项目汇报PPT', isCompleted: true, deleted: true },
  ];

  const result = filterArchivedTasks(tasks, '项目 PPT');

  assert.deepEqual(result.map((task) => task.id), ['1']);
}

async function testBlankSearchReturnsAllCompletedTasks() {
  const { filterArchivedTasks } = await loadArchiveSearchModule();
  const tasks = [
    { id: '1', title: 'Alpha', isCompleted: true },
    { id: '2', title: 'Beta', isCompleted: false },
    { id: '3', title: 'Gamma', isCompleted: true, deleted: true },
    { id: '4', title: 'Delta', isCompleted: true },
  ];

  const result = filterArchivedTasks(tasks, '   ');

  assert.deepEqual(result.map((task) => task.id), ['1', '4']);
}

const tests = [
  ['filters completed titles by all space-separated keywords', testFiltersCompletedTitlesByAllSpaceSeparatedKeywords],
  ['blank search returns all completed tasks', testBlankSearchReturnsAllCompletedTasks],
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

  console.log(`Passed ${tests.length} archive search tests.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
