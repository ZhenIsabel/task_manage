<template>
  <view class="archive-page page-with-nav">
    <view class="nav-header">
      <view class="glass-btn" @click="goBack">
        <uni-icons type="back" size="24" color="inherit" />
      </view>
      <view class="header-text-col">
        <text class="nav-title">已完成任务</text>
        <text class="nav-sub">共 {{ list.length }} 项历史记录</text>
      </view>
    </view>

    <scroll-view scroll-y class="archive-list" :show-scrollbar="false">
      <view v-if="list.length === 0" class="empty-archive">
        <uni-icons type="checkmarkempty" size="48" color="#ccc" />
        <text>暂无已完成任务</text>
      </view>
      <view v-else v-for="task in list" :key="task.id" class="glass-card archive-item">
        <view class="archive-info">
          <text class="archive-title">{{ task.title }}</text>
          <text class="archive-date">{{ formatDateShort(task.completedAt) }} 完成</text>
        </view>
        <view class="btn-restore" @click="handleRestore(task.id)">
          <uni-icons type="redo" size="16" color="#15803d" />
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import dataManager from '@/services/dataManager.js';
import { formatDateShort } from '@/utils/date.js';

const tasks = ref([]);

const list = computed(() => tasks.value.filter((t) => t.isCompleted));

function loadTasks() {
  tasks.value = dataManager.loadTasksFromStorage();
}

onMounted(loadTasks);
onShow(loadTasks);

function goBack() {
  uni.navigateBack();
}

function handleRestore(id) {
  const all = dataManager.loadTasksFromStorage();
  const task = all.find((t) => t.id === id);
  if (!task) return;
  const updated = {
    ...task,
    isCompleted: false,
    completedAt: null,
  };
  dataManager.saveTask(updated, true).then(() => {
    tasks.value = dataManager.loadTasksFromStorage();
    uni.showToast({ title: '已恢复', icon: 'success' });
  }).catch(() => {});
}
</script>

<style lang="scss" scoped>
.archive-page {
  min-height: 100vh;
  padding: 60px 20px 40px;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
  display: flex;
  flex-direction: column;
}
.nav-sub {
  font-size: 11px;
  color: #6b7280;
  display: block;
  margin-top: 2px;
}

.archive-list {
  flex: 1;
  min-height: 0;
}
.empty-archive {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #9ca3af;
  gap: 10px;
  font-size: 13px;
}
.glass-card {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 20px;
  margin-bottom: 16px;
}
.archive-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  margin-bottom: 10px;
}
.archive-info {
  flex: 1;
  overflow: hidden;
  margin-right: 10px;
}
.archive-title {
  font-size: 14px;
  color: #374151;
  text-decoration: line-through;
  opacity: 0.6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.archive-date {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
  display: block;
}
.btn-restore {
  padding: 6px;
  border-radius: 50%;
  background: #dcfce7;
  color: #15803d;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
