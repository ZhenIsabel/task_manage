/**
 * 任务 API：与服务器通信，字段与 task_manage server_example / database_manager 对齐
 * 前端字段：title, note, dueDate, importance, urgency, isCompleted, completedAt, createdAt
 * 服务端字段：text, notes, due_date, importance, urgency, completed, completed_date, created_at, updated_at, position
 */
import request from './request.js';

// 重要/紧急：前端 low|high <-> 服务端 低|高
const importanceToServer = (v) => (v === 'high' ? '高' : '低');
const importanceFromServer = (v) => (v === '高' ? 'high' : 'low');
const urgencyToServer = (v) => (v === 'high' ? '高' : '低');
const urgencyFromServer = (v) => (v === '高' ? 'high' : 'low');

/**
 * 前端任务 -> 服务端请求体
 */
export function taskToServer(task) {
  const position = task.position || { x: 100, y: 100 };
  return {
    id: task.id,
    text: task.title ?? '',
    notes: task.note ?? '',
    due_date: task.dueDate ? (typeof task.dueDate === 'string' ? task.dueDate : new Date(task.dueDate).toISOString()) : '',
    importance: importanceToServer(task.importance || 'low'),
    urgency: urgencyToServer(task.urgency || 'low'),
    completed: !!task.isCompleted,
    completed_date: task.completedAt || '',
    created_at: task.createdAt || new Date().toISOString(),
    position: { x: position.x ?? 100, y: position.y ?? 100 },
  };
}

/**
 * 服务端任务 -> 前端任务
 */
export function taskFromServer(serverTask) {
  if (!serverTask) return null;
  const position = serverTask.position || { x: 100, y: 100 };
  return {
    id: serverTask.id,
    title: serverTask.text ?? '',
    note: serverTask.notes ?? '',
    dueDate: serverTask.due_date || null,
    importance: importanceFromServer(serverTask.importance || '低'),
    urgency: urgencyFromServer(serverTask.urgency || '低'),
    isCompleted: !!serverTask.completed,
    completedAt: serverTask.completed_date || null,
    createdAt: serverTask.created_at || serverTask.updated_at || new Date().toISOString(),
    position: { x: position.x ?? 100, y: position.y ?? 100 },
  };
}

/**
 * 获取服务器任务列表
 * @returns {Promise<{ success: boolean, tasks?: array, error?: string }>}
 */
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

/**
 * 创建或更新任务到服务器
 * @param {object} task - 前端任务对象
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export function createOrUpdateTaskOnServer(task) {
  const body = taskToServer(task);
  return request('POST', '/api/tasks', body).then((res) => {
    if (res.success) return { success: true };
    return { success: false, error: res.error };
  });
}

/**
 * 在服务器上删除任务
 * @param {string} taskId
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export function deleteTaskOnServer(taskId) {
  return request('DELETE', `/api/tasks/${taskId}`).then((res) => {
    if (res.success) return { success: true };
    return { success: false, error: res.error };
  });
}

/**
 * 健康检查
 * @returns {Promise<{ success: boolean, data?: object }>}
 */
export function healthCheck() {
  return request('GET', '/api/health');
}
