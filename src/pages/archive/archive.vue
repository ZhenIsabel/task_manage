<template>
  <view class="archive-page page-with-nav">

    <scroll-view scroll-y class="archive-list" :show-scrollbar="false">
     
      <view class="archive-list-content">
        <view class="archive-header-row">
          <view class="glass-btn" @click="goBack">
            <uni-icons type="back" size="24" color="inherit" />
          </view>
          <view class="archive-list-title">
            <text class="nav-title">已完成任务</text>
            <text class="nav-sub">共 {{ list.length }} 项历史记录</text>
          </view>
        </view>
        <view v-if="list.length === 0" class="empty-archive">
          <uni-icons type="checkmarkempty" size="48" color="#ccc" />
          <text>暂无已完成任务</text>
        </view>
        <template v-else>
          <view v-for="task in list" :key="task.id" class="glass-card archive-item">
            <view class="archive-info">
              <text class="archive-title">{{ task.title }}</text>
              <text class="archive-date">{{ formatDateShort(task.completedAt) }} 完成</text>
            </view>
            <view class="btn-restore" @click="handleRestore(task.id)">
              <uni-icons type="redo" size="16" color="#15803d" />
            </view>
          </view>
        </template>
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
  padding: 20px 00px 00px;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
  display: flex;
  flex-direction: column;
}
// 按钮和标题同一行，悬浮在列表顶部
.archive-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  margin-bottom: 8px;
}
.archive-list-title {
  flex: 1;
  min-width: 0;
}
.nav-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: block;
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
/* 给卡片阴影留出空间*/
.archive-list-content {
  padding: 30px 40px 60px;
  min-height: 100%;
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
  background:rgb(231, 244, 235);
  color: #15803d;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
