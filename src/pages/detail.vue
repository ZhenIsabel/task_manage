<template>
  <view class="detail-page page-with-nav">
    <view class="form-content-wrap">
      <scroll-view scroll-y class="form-content" :show-scrollbar="false">
        <view class="form-content-inner">
          <view class="nav-header">
            <view class="glass-btn" @tap="goBack">
              <uni-icons type="back" size="24" color="#1f2937" />
            </view>
            <text class="nav-title">任务详情</text>
            <view
              class="glass-btn primary-theme"
              :class="{ 'restore-theme': isCompletedTask }"
              @tap="handleHeaderAction"
            >
              <uni-icons
                :type="isCompletedTask ? 'redo' : 'compose'"
                size="24"
                :color="isCompletedTask ? '#15803d' : '#4f46e5'"
              />
            </view>
          </view>

          <view class="glass-card main-info-card">
            <view class="status-row">
              <view class="status-badge" :class="task.isCompleted ? 'completed' : 'pending'">
                <uni-icons :type="task.isCompleted ? 'checkbox-filled' : 'circle'" size="16" color="inherit" />
                <text>{{ task.isCompleted ? '已完成' : '进行中' }}</text>
              </view>
              <text class="date-text" v-if="task.dueDate">截止: {{ formatDate(task.dueDate) }}</text>
            </view>

            <text class="task-title">{{ task.title }}</text>

            <view class="tags-row">
              <view class="tag" :class="task.importance === 'high' ? 'tag-red' : 'tag-gray'">
                {{ task.importance === 'high' ? '重要' : '一般' }}
              </view>
              <view class="tag" :class="task.urgency === 'high' ? 'tag-orange' : 'tag-gray'">
                {{ task.urgency === 'high' ? '紧急' : '不急' }}
              </view>
            </view>

            <view class="divider" v-if="task.note"></view>

            <view class="note-section" v-if="task.note">
              <text class="label">备注</text>
              <text class="note-text">{{ task.note }}</text>
            </view>
          </view>

          <view class="history-section">
            <view class="section-header">
              <uni-icons type="paperplane" size="16" color="#6b7280" />
              <text class="section-title">流转记录</text>
            </view>

            <view class="timeline" v-if="historyList.length > 0">
              <view
                v-for="(log, index) in historyList"
                :key="log.id || index"
                class="timeline-item"
                :class="{ 'is-expanded': log.expanded }"
                @tap="toggleHistory(index)"
              >
                <view class="timeline-left">
                  <view class="dot" :class="getActionColor(log.type)"></view>
                  <view class="line" v-if="index !== historyList.length - 1"></view>
                </view>

                <view class="timeline-content glass-card-mini">
                  <view class="history-summary">
                    <view class="history-info">
                      <text class="history-time">{{ formatTime(log.timestamp) }}</text>
                      <text class="history-action">{{ log.summary }}</text>
                    </view>
                    <uni-icons
                      :type="log.expanded ? 'top' : 'bottom'"
                      size="12"
                      color="#9ca3af"
                      v-if="log.details && log.details.length > 0"
                    />
                  </view>

                  <view class="history-details" v-if="log.expanded && log.details && log.details.length > 0">
                    <view v-for="(detail, detailIndex) in log.details" :key="detailIndex" class="detail-row">
                      <text class="field-name">{{ detail.field }}:</text>
                      <text class="old-val">{{ detail.oldVal || '空' }}</text>
                      <uni-icons type="arrowright" size="12" color="#9ca3af" class="arrow-icon" />
                      <text class="new-val">{{ detail.newVal || '空' }}</text>
                    </view>
                  </view>
                </view>
              </view>
            </view>
            <view v-else class="history-empty">
              <text class="history-empty-text">暂无流转记录</text>
            </view>
          </view>

          <view class="bottom-spacer" />
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import dataManager from '@/services/dataManager.js';
import { getTaskHistoryFromServer } from '@/api/task.js';

const taskId = ref('');
const task = reactive({
  id: '',
  title: '',
  note: '',
  isCompleted: false,
  importance: 'low',
  urgency: 'low',
  dueDate: null,
});
const historyList = ref([]);
const isCompletedTask = computed(() => !!task.isCompleted);

const FIELD_DISPLAY = {
  text: '任务内容',
  notes: '备注',
  due_date: '截止日期',
  urgency: '紧急程度',
  importance: '重要程度',
};

const HIGH_HISTORY_VALUES = new Set(['高', 'high', 'HIGH', 'High']);
const LOW_HISTORY_VALUES = new Set(['低', 'low', 'LOW', 'Low']);

function formatFieldValue(field, value) {
  if (!value) return '';
  if (field === 'urgency') {
    if (HIGH_HISTORY_VALUES.has(value)) return '紧急';
    if (LOW_HISTORY_VALUES.has(value)) return '不急';
  }
  if (field === 'importance') {
    if (HIGH_HISTORY_VALUES.has(value)) return '重要';
    if (LOW_HISTORY_VALUES.has(value)) return '一般';
  }
  return value;
}

function mergeFieldHistory(localHistory, serverHistory) {
  const byField = {};
  const push = (fieldName, item) => {
    if (!byField[fieldName]) byField[fieldName] = [];
    byField[fieldName].push(item);
  };

  Object.entries(localHistory || {}).forEach(([fieldName, list]) => {
    (list || []).forEach((record) => {
      push(fieldName, {
        value: record.value,
        timestamp: record.timestamp,
        action: record.action,
      });
    });
  });

  Object.entries(serverHistory || {}).forEach(([fieldName, list]) => {
    (list || []).forEach((record) => {
      push(fieldName, {
        value: record.value,
        timestamp: record.timestamp,
        action: record.action,
      });
    });
  });

  Object.keys(byField).forEach((fieldName) => {
    byField[fieldName].sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  });

  return byField;
}

function buildMergedList(byField) {
  const merged = [];
  Object.entries(byField).forEach(([fieldName, list]) => {
    list.forEach((record) => {
      merged.push({
        field: fieldName,
        timestamp: record.timestamp,
        action: record.action || 'update',
        value: record.value,
      });
    });
  });

  merged.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  return merged;
}

function buildTimelineList(merged) {
  const lastVal = {};
  const byTs = {};

  merged.forEach((record) => {
    const ts = record.timestamp || '';
    const fieldDisplay = FIELD_DISPLAY[record.field] || record.field;
    const oldVal = lastVal[record.field] !== undefined ? formatFieldValue(record.field, lastVal[record.field]) : '';
    const newVal = formatFieldValue(record.field, record.value);

    if (!byTs[ts]) byTs[ts] = { timestamp: ts, actions: [], details: [] };
    byTs[ts].actions.push(record.action);
    byTs[ts].details.push({ field: fieldDisplay, oldVal, newVal });
    lastVal[record.field] = record.value;
  });

  return Object.entries(byTs)
    .sort((a, b) => b[1].timestamp.localeCompare(a[1].timestamp))
    .map(([ts, item], index) => {
      const hasCreate = (item.actions || []).some((action) => action === 'create');
      return {
        id: `h-${index}-${ts}`,
        type: hasCreate ? 'create' : 'update',
        timestamp: item.timestamp,
        summary: hasCreate ? '创建了任务' : '修改了任务详情',
        expanded: false,
        details: item.details || [],
      };
    });
}

function loadTaskAndHistory() {
  if (!taskId.value) return;

  const list = dataManager.loadTasksFromStorage();
  const found = list.find((item) => item.id === taskId.value);
  if (found) {
    task.id = found.id;
    task.title = found.title ?? '';
    task.note = found.note ?? '';
    task.isCompleted = !!found.isCompleted;
    task.importance = found.importance ?? 'low';
    task.urgency = found.urgency ?? 'low';
    task.dueDate = found.dueDate ?? null;
  }

  const localHistory = dataManager.getTaskHistory(taskId.value);
  let serverHistory = {};
  const finish = () => {
    const byField = mergeFieldHistory(localHistory, serverHistory);
    const merged = buildMergedList(byField);
    historyList.value = buildTimelineList(merged);
  };

  if (dataManager.hasRemoteConfig()) {
    getTaskHistoryFromServer(taskId.value).then((res) => {
      if (res.success && res.history) serverHistory = res.history;
      finish();
    }).catch(finish);
  } else {
    finish();
  }
}

onLoad((options) => {
  if (options && options.id) taskId.value = options.id;
});

onShow(() => {
  if (taskId.value) loadTaskAndHistory();
});

function goBack() {
  uni.navigateBack();
}

function goToEdit() {
  const id = task.id || taskId.value;
  if (!id) return;
  uni.navigateTo({ url: `/pages/edit?id=${id}` });
}

function handleHeaderAction() {
  if (isCompletedTask.value) {
    restoreTask();
    return;
  }
  goToEdit();
}

function restoreTask() {
  const id = task.id || taskId.value;
  if (!id) return;

  const all = dataManager.loadTasksFromStorage();
  const found = all.find((item) => item.id === id);
  if (!found) return;

  const updated = {
    ...found,
    isCompleted: false,
    completedAt: null,
  };

  dataManager.saveTask(updated, false).then(() => {
    uni.showToast({ title: '已恢复', icon: 'success' });
    loadTaskAndHistory();
  }).catch(() => {});
}

function toggleHistory(index) {
  const item = historyList.value[index];
  if (item?.details?.length) item.expanded = !item.expanded;
}

function getActionColor(type) {
  switch (type) {
    case 'create':
      return 'bg-green';
    case 'delete':
      return 'bg-red';
    case 'complete':
      return 'bg-blue';
    default:
      return 'bg-gray';
  }
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  return `${date.getMonth() + 1}-${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  padding: 20px 0 0;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
  display: flex;
  flex-direction: column;
}

.form-content-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.form-content {
  flex: 1;
  height: 100%;
}

.form-content-inner {
  padding: 30px 40px 60px;
}

.nav-header {
  justify-content: space-between;
}

.nav-title {
  flex: 1;
  text-align: left;
}

.glass-btn.primary-theme {
  background: rgba(224, 231, 255, 0.8);
  color: #4f46e5;
}

.glass-btn.restore-theme {
  background: rgb(231, 244, 235);
  color: #15803d;
}

.main-info-card {
  padding: 24px;
  margin-bottom: 24px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;

  &.pending {
    background: rgba(0, 0, 0, 0.05);
    color: #6b7280;
  }

  &.completed {
    background: #dcfce7;
    color: #166534;
  }
}

.date-text {
  font-size: 13px;
  color: #9ca3af;
  font-weight: 500;
}

.task-title {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.4;
  margin-bottom: 16px;
}

.tags-row {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tag {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 600;

  &.tag-gray { background: #f3f4f6; color: #6b7280; }
  &.tag-red { background: #fee2e2; color: #ef4444; }
  &.tag-orange { background: #ffedd5; color: #f97316; }
}

.divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.05);
  margin: 0 -24px 16px;
}

.note-section .label {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.note-text {
  font-size: 15px;
  color: #4b5563;
  line-height: 1.6;
}

.history-section {
  padding-top: 10px;
}

.history-empty {
  padding: 24px 16px;
  text-align: center;
}

.history-empty-text {
  font-size: 14px;
  color: #9ca3af;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-left: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
}

.timeline {
  position: relative;
  padding-left: 8px;
}

.timeline-item {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  position: relative;
}

.timeline-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 12px;
  padding-top: 12px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 2;

  &.bg-green { background: #10b981; }
  &.bg-blue { background: #3b82f6; }
  &.bg-red { background: #ef4444; }
  &.bg-gray { background: #9ca3af; }
}

.line {
  flex: 1;
  width: 2px;
  background: #e5e7eb;
  margin-top: 4px;
  min-height: 20px;
}

.glass-card-mini {
  flex: 1;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  padding: 12px;
  transition: all 0.3s ease;
}

.timeline-item.is-expanded .glass-card-mini {
  background: rgba(255, 255, 255, 0.65);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.history-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-info {
  display: flex;
  flex-direction: column;
}

.history-time {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 2px;
}

.history-action {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.history-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.06);
  animation: fadeIn 0.3s ease;
}

.detail-row {
  display: flex;
  align-items: center;
  font-size: 12px;
  margin-bottom: 4px;
  color: #4b5563;
  flex-wrap: wrap;
}

.field-name {
  color: #6b7280;
  margin-right: 6px;
}

.old-val {
  text-decoration: line-through;
  color: #9ca3af;
  margin-right: 6px;
}

.new-val {
  color: #1f2937;
  font-weight: 500;
  margin-left: 6px;
}

.arrow-icon {
  margin-top: 2px;
}

.bottom-spacer {
  height: 40px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
