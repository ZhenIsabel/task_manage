<template>
  <view class="conflict-page page-with-nav">
    <view class="background-blobs">
      <view class="blob blue"></view>
      <view class="blob gold"></view>
    </view>

    <scroll-view scroll-y class="page-scroll" :show-scrollbar="false">
      <view class="page-inner">
        <view class="nav-header">
          <view class="glass-btn" @tap="goBack">
            <uni-icons type="back" size="24" color="inherit" />
          </view>
          <text class="nav-title">远程冲突确认</text>
        </view>

        <view class="glass-card intro-card">
          <text class="intro-title">检测到 {{ changes.length }} 条远程修改</text>
          <text class="intro-text">每条记录都需要选择保留本地还是接受远程。接受本地后，app 会把本地版本重新上传到服务器。</text>
        </view>

        <view v-if="changes.length === 0" class="glass-card empty-card">
          <uni-icons type="checkmarkempty" size="42" color="#10b981" />
          <text class="empty-title">没有待处理冲突</text>
          <text class="empty-text">当前本地任务与远程任务已经处于一致或已确认状态。</text>
        </view>

        <view v-else>
          <view v-for="change in changes" :key="change.id" class="glass-card conflict-card">
            <view class="card-head">
              <view>
                <text class="task-title">{{ change.title || '未命名任务' }}</text>
                <text class="task-subtitle">远程更新时间：{{ formatDateTime(change.remoteTask?.updatedAt) }}</text>
              </view>
              <view class="status-tag">需确认</view>
            </view>

            <view class="compare-grid">
              <view class="choice-card" :class="{ selected: selections[change.id] === 'local' }" @tap="selectChoice(change.id, 'local')">
                <view class="choice-head">
                  <text class="choice-title">保留本地</text>
                  <view class="radio-dot" :class="{ active: selections[change.id] === 'local' }"></view>
                </view>
                <text class="choice-body">{{ formatRecord(change.localTask) }}</text>
              </view>

              <view class="choice-card" :class="{ selected: selections[change.id] === 'remote' }" @tap="selectChoice(change.id, 'remote')">
                <view class="choice-head">
                  <text class="choice-title">接受远程</text>
                  <view class="radio-dot" :class="{ active: selections[change.id] === 'remote' }"></view>
                </view>
                <text class="choice-body">{{ formatRecord(change.remoteTask) }}</text>
              </view>
            </view>
          </view>
        </view>

        <view class="bottom-spacer"></view>
      </view>
    </scroll-view>

    <view class="bottom-action" v-if="changes.length > 0">
      <view class="glass-btn secondary" @tap="selectAll('local')">全部本地</view>
      <view class="glass-btn secondary" @tap="selectAll('remote')">全部远程</view>
      <view class="submit-btn" @tap="submitSelection">保存选择</view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import dataManager from '@/services/dataManager.js';

const changes = ref([]);
const selections = reactive({});
const submitting = ref(false);

onMounted(() => {
  const pending = dataManager.getPendingRemoteTaskChanges();
  changes.value = pending;
});

function goBack() {
  uni.navigateBack();
}

function formatDateTime(value) {
  if (!value) return '未记录';
  return String(value).replace('T', ' ').split('.')[0];
}

function formatBoolean(value) {
  return value ? '是' : '否';
}

function formatRecord(task) {
  if (!task) return '无数据';
  const lines = [];
  if (task.title) lines.push(`标题：${task.title}`);
  if (task.note) lines.push(`备注：${task.note}`);
  if (task.dueDate) lines.push(`截止：${String(task.dueDate).split('T')[0]}`);
  lines.push(`重要：${task.importance === 'high' ? '高' : '低'}`);
  lines.push(`紧急：${task.urgency === 'high' ? '高' : '低'}`);
  lines.push(`完成：${formatBoolean(!!task.isCompleted)}`);
  if (task.completedAt) lines.push(`完成时间：${formatDateTime(task.completedAt)}`);
  if (task.updatedAt) lines.push(`更新时间：${formatDateTime(task.updatedAt)}`);
  return lines.join('\n');
}

function selectChoice(id, value) {
  selections[id] = value;
}

function selectAll(value) {
  changes.value.forEach((change) => {
    selections[change.id] = value;
  });
}

function submitSelection() {
  if (submitting.value) return;
  const missing = changes.value.filter((change) => !selections[change.id]);
  if (missing.length > 0) {
    uni.showToast({ title: '还有冲突未选择', icon: 'none' });
    return;
  }

  submitting.value = true;
  const acceptRemoteIds = changes.value.filter((change) => selections[change.id] === 'remote').map((change) => change.id);
  const acceptLocalIds = changes.value.filter((change) => selections[change.id] === 'local').map((change) => change.id);

  uni.showLoading({ title: '处理中...' });
  dataManager.resolvePendingRemoteTaskChanges(acceptRemoteIds, acceptLocalIds).then((res) => {
    uni.hideLoading();
    submitting.value = false;
    if (!res.success) {
      uni.showToast({ title: res.error || '处理失败', icon: 'none' });
      return;
    }
    uni.showToast({ title: '已保存选择', icon: 'success' });
    setTimeout(() => uni.navigateBack(), 250);
  });
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.conflict-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #eef4ff 0%, #ffffff 45%);
  position: relative;
}

.background-blobs {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.22;
}

.blue {
  width: 260px;
  height: 260px;
  top: -40px;
  left: -50px;
  background: #60a5fa;
}

.gold {
  width: 220px;
  height: 220px;
  right: -60px;
  top: 180px;
  background: #f59e0b;
}

.page-scroll {
  position: relative;
  z-index: 1;
  min-height: 100vh;
}

.page-inner {
  padding: 30px 28px 120px;
}

.nav-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.glass-card {
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow: $shadow;
  border-radius: 22px;
  backdrop-filter: blur(12px);
}

.intro-card,
.empty-card,
.conflict-card {
  padding: 18px;
  margin-bottom: 14px;
}

.intro-title,
.task-title,
.empty-title {
  display: block;
  color: #111827;
  font-weight: 700;
}

.intro-title {
  font-size: 18px;
}

.intro-text,
.task-subtitle,
.empty-text {
  display: block;
  margin-top: 8px;
  color: #6b7280;
  line-height: 1.6;
  font-size: 13px;
}

.empty-card {
  text-align: center;
  padding-top: 28px;
  padding-bottom: 28px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.status-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
  font-size: 12px;
  font-weight: 700;
}

.compare-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.choice-card {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 18px;
  padding: 14px;
  transition: all 0.2s ease;
}

.choice-card.selected {
  border-color: rgba(99, 102, 241, 0.55);
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.12);
  background: rgba(238, 242, 255, 0.8);
}

.choice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.choice-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.choice-body {
  white-space: pre-line;
  line-height: 1.7;
  color: #475569;
  font-size: 13px;
}

.radio-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(148, 163, 184, 0.8);
}

.radio-dot.active {
  border-color: #6366f1;
  background: radial-gradient(circle, #6366f1 0 45%, transparent 48% 100%);
}

.bottom-spacer {
  height: 24px;
}

.bottom-action {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  padding: 14px 16px;
  padding-bottom: calc(14px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px);
  display: flex;
  gap: 10px;
}

.glass-btn.secondary,
.submit-btn {
  flex: 1;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.glass-btn.secondary {
  background: rgba(255, 255, 255, 0.7);
  color: #475569;
  border: 1px solid rgba(226, 232, 240, 0.95);
}

.submit-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.24);
}
</style>
