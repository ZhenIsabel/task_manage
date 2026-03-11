<template>
  <view class="container">
    <view class="background-blobs">
      <view class="blob blue"></view>
      <view class="blob purple"></view>
      <view class="blob pink"></view>
    </view>

    <view class="app-window">
      <view class="view-container matrix-view">
        <view class="header">
          <view>
            <text class="main-title">不想干活</text>
          </view>
          <view class="header-right">
            <view class="date-display">
              <text class="day">{{ currentWeekday }}</text>
              <text class="month">{{ currentDateStr }}</text>
            </view>
          </view>
        </view>

        <view class="grid-layout">
          <view class="grid-item">
            <view class="glass-card quadrant-card">
              <view class="glow-bg bg-blue"></view>
              <view class="quadrant-header">
                <view class="icon-wrap"><uni-icons type="calendar" size="16" color="inherit" /></view>
                <text class="quadrant-title">重要 · 不急</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.tl.length === 0" class="empty-state">无任务</view>
                <template v-else>
                  <view
                    v-for="task in quadrantData.tl"
                    :key="task.id"
                    class="task-item"
                    @tap="goDetail(task)"
                  >
                    <view class="checkbox" :class="{ checked: task.isCompleted }" @tap.stop="handleToggleTask(task.id)">
                      <uni-icons v-if="task.isCompleted" type="checkmarkempty" size="12" color="white" />
                    </view>
                    <text class="task-title" :class="{ completed: task.isCompleted }">{{ task.title }}</text>
                  </view>
                </template>
              </scroll-view>
            </view>
          </view>

          <view class="grid-item">
            <view class="glass-card quadrant-card">
              <view class="glow-bg bg-red"></view>
              <view class="quadrant-header">
                <view class="icon-wrap"><uni-icons type="fire" size="16" color="inherit" /></view>
                <text class="quadrant-title">重要 · 紧急</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.tr.length === 0" class="empty-state">无任务</view>
                <template v-else>
                  <view
                    v-for="task in quadrantData.tr"
                    :key="task.id"
                    class="task-item"
                    @tap="goDetail(task)"
                  >
                    <view class="checkbox" :class="{ checked: task.isCompleted }" @tap.stop="handleToggleTask(task.id)">
                      <uni-icons v-if="task.isCompleted" type="checkmarkempty" size="12" color="white" />
                    </view>
                    <text class="task-title" :class="{ completed: task.isCompleted }">{{ task.title }}</text>
                  </view>
                </template>
              </scroll-view>
            </view>
          </view>

          <view class="grid-item">
            <view class="glass-card quadrant-card">
              <view class="glow-bg bg-gray"></view>
              <view class="quadrant-header">
                <view class="icon-wrap"><uni-icons type="bars" size="16" color="inherit" /></view>
                <text class="quadrant-title">不重要 · 不急</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.bl.length === 0" class="empty-state">无任务</view>
                <template v-else>
                  <view
                    v-for="task in quadrantData.bl"
                    :key="task.id"
                    class="task-item"
                    @tap="goDetail(task)"
                  >
                    <view class="checkbox" :class="{ checked: task.isCompleted }" @tap.stop="handleToggleTask(task.id)">
                      <uni-icons v-if="task.isCompleted" type="checkmarkempty" size="12" color="white" />
                    </view>
                    <text class="task-title" :class="{ completed: task.isCompleted }">{{ task.title }}</text>
                  </view>
                </template>
              </scroll-view>
            </view>
          </view>

          <view class="grid-item">
            <view class="glass-card quadrant-card">
              <view class="glow-bg bg-yellow"></view>
              <view class="quadrant-header">
                <view class="icon-wrap"><uni-icons type="info" size="16" color="inherit" /></view>
                <text class="quadrant-title">不重要 · 紧急</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.br.length === 0" class="empty-state">无任务</view>
                <template v-else>
                  <view
                    v-for="task in quadrantData.br"
                    :key="task.id"
                    class="task-item"
                    @tap="goDetail(task)"
                  >
                    <view class="checkbox" :class="{ checked: task.isCompleted }" @tap.stop="handleToggleTask(task.id)">
                      <uni-icons v-if="task.isCompleted" type="checkmarkempty" size="12" color="white" />
                    </view>
                    <text class="task-title" :class="{ completed: task.isCompleted }">{{ task.title }}</text>
                  </view>
                </template>
              </scroll-view>
            </view>
          </view>
        </view>
      </view>

      <view class="bottom-dock">
        <view class="dock-bar">
          <view class="dock-item" @tap="goSettings">
            <view class="dock-icon-wrap">
              <uni-icons type="gear" size="28" color="inherit" />
            </view>
          </view>
          <view class="dock-item dock-item-spacer" aria-hidden="true" />
          <view class="dock-item" @tap="goArchive">
            <view class="dock-icon-wrap">
              <uni-icons type="checkmarkempty" size="28" color="inherit" />
            </view>
          </view>
        </view>
        <view
          class="fab"
          :class="{ 'fab--pressed': fabPressed }"
          @tap="onFabTap"
          @touchstart="fabPressed = true"
          @touchend="fabPressed = false"
          @touchcancel="fabPressed = false"
        >
          <uni-icons type="plus" size="36" color="#fff" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { onShow, onBackPress } from '@dcloudio/uni-app';
import dataManager from '@/services/dataManager.js';
import { isToday } from '@/utils/date.js';

const tasks = ref([]);
const syncStatus = ref(null);
const fabPressed = ref(false);
const loading = ref(false);

const currentWeekday = computed(() => ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()]);
const currentDateStr = computed(() => {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${m}.${day}`;
});

const getQuadrantTasks = (importance, urgency) => {
  return tasks.value.filter((task) => {
    const isVisible = !task.isCompleted || (task.isCompleted && isToday(task.completedAt));
    const matchImportance = importance === 'high' ? task.importance === 'high' : task.importance !== 'high';
    const matchUrgency = urgency === 'high' ? task.urgency === 'high' : task.urgency !== 'high';
    return isVisible && matchImportance && matchUrgency;
  });
};

const quadrantData = computed(() => ({
  tl: getQuadrantTasks('high', 'low'),
  tr: getQuadrantTasks('high', 'high'),
  bl: getQuadrantTasks('low', 'low'),
  br: getQuadrantTasks('low', 'high'),
}));

function loadTasks() {
  const local = dataManager.loadTasksFromStorage();
  tasks.value = local.length ? local : [];
  syncStatus.value = dataManager.getLastSyncStatus();
}

function doSyncFromServer() {
  if (!dataManager.hasRemoteConfig()) return;
  loading.value = true;
  dataManager.syncFromServer([...tasks.value]).then((res) => {
    loading.value = false;
    if (res.success && res.merged) tasks.value = res.merged;
    syncStatus.value = dataManager.getLastSyncStatus();
    if (res.error) uni.showToast({ title: res.error || '同步失败', icon: 'none' });
  });
}

onMounted(() => {
  loadTasks();
  if (dataManager.hasRemoteConfig()) doSyncFromServer();
});

onShow(() => {
  loadTasks();
});

onBackPress(() => {
  uni.showModal({
    title: '提示',
    content: '是否退出应用？',
    success: (res) => {
      if (res.confirm && typeof plus !== 'undefined') {
        plus.runtime.quit();
      }
    },
  });
  return true;
});

const handleToggleTask = (id) => {
  const idx = tasks.value.findIndex((task) => task.id === id);
  if (idx === -1) return;

  const task = tasks.value[idx];
  const updated = {
    ...task,
    isCompleted: !task.isCompleted,
    completedAt: !task.isCompleted ? new Date().toISOString() : null,
  };

  tasks.value[idx] = updated;
  dataManager.saveTask(updated, false).catch(() => {});
};

function goCreate() {
  uni.navigateTo({ url: '/pages/edit' });
}

function onFabTap() {
  goCreate();
}

function goArchive() {
  uni.navigateTo({ url: '/pages/archive' });
}

function goSettings() {
  uni.navigateTo({ url: '/pages/settings' });
}

function goDetail(task) {
  uni.navigateTo({ url: '/pages/detail?id=' + encodeURIComponent(task.id) });
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

view, text, button, scroll-view, input, textarea {
  box-sizing: border-box;
}

.container {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background-color: #f2f2f7;
  overflow: hidden;
  font-family: -apple-system, Helvetica, sans-serif;
}

.background-blobs {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;

  .blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
    animation: pulse 8s infinite ease-in-out;
  }

  .blue { top: -10%; left: -10%; width: 60%; height: 60%; background: #60a5fa; }
  .purple { bottom: -10%; right: -10%; width: 60%; height: 60%; background: #c084fc; animation-delay: 1s; }
  .pink { top: 40%; left: 30%; width: 40%; height: 40%; background: #f472b6; animation-delay: 2s; }
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.app-window {
  position: relative;
  width: 100%;
  height: 100%;
  z-index: 1;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.grid-layout {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  min-height: 0;
  padding-bottom: calc(80px + constant(safe-area-inset-bottom, 0px));
  padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
}

.grid-item {
  width: calc(50% - 6px);
  height: calc(50% - 6px);
  min-height: 0;
  min-width: 0;
}

.matrix-view {
  height: 100%;
}

.header {
  padding: 50px 24px 10px;
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  flex-shrink: 0;

  .main-title { font-size: 28px; font-weight: 800; color: #111827; line-height: 1.2; }
  .header-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .date-display { text-align: right; margin-left: 4px; height: 28px; }
  .day { font-size: 16px; font-weight: 700; display: block; line-height: 1; color: #1f2937; }
  .month { font-size: 12px; color: #6b7280; font-weight: 500; margin-top: 4px; display: block; }
}

.quadrant-card {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 12px;
  position: relative;
}

.glow-bg {
  position: absolute;
  top: -30%;
  right: -30%;
  width: 70%;
  height: 70%;
  border-radius: 50%;
  opacity: 0.15;
  filter: blur(20px);
  pointer-events: none;
}

.bg-blue { background-color: #3b82f6; }
.bg-red { background-color: #ef4444; }
.bg-gray { background-color: #9ca3af; }
.bg-yellow { background-color: #f59e0b; }

.quadrant-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  flex-shrink: 0;

  .quadrant-title { font-size: 11px; font-weight: 800; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.5px; }
  .icon-wrap { opacity: 0.7; display: flex; }
}

.task-list {
  flex: 1;
  height: 0;
  width: 100%;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 12px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  margin-bottom: 8px;

  &:active { background: rgba(255, 255, 255, 0.5); }
}

.checkbox {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid rgba(107, 114, 128, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.checked {
    background: rgba(55, 65, 81, 0.8);
    border-color: transparent;
    color: white;
  }
}

.task-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  color: #374151;
  word-break: break-all;

  &.completed {
    text-decoration: line-through;
    opacity: 0.5;
  }
}

$fab-size: 60px;
$dock-bar-height: 56px;

.bottom-dock {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.dock-bar {
  width: 100%;
  max-width: 320px;
  display: flex;
  align-items: stretch;
  gap: 0;
  padding: 6px 8px;
  border-radius: 20px;
  background: $glass-bg;
  border: 1px solid $glass-border;
  box-shadow: $shadow;
  min-height: $dock-bar-height;
}

.dock-item {
  flex: 1;
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 4px 2px;
  border-radius: 16px;
  color: #374151;
  transition: transform 0.2s ease, background 0.2s ease;
  min-width: 0;

  &:active {
    transform: scale(0.94);
    background: rgba(255, 255, 255, 0.35);
  }
}

.dock-item-spacer {
  flex: 0 0 $fab-size;
  pointer-events: none;
  padding: 0;
}

.dock-icon-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  border-radius: 14px;
  background: $glass-bg;
  border: 1px solid $glass-border;
  box-shadow: $shadow;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.dock-item:active .dock-icon-wrap {
  background: rgba(255, 255, 255, 0.75);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 1);
}

.fab {
  position: absolute;
  left: 50%;
  bottom: calc(8px + env(safe-area-inset-bottom) + 14px);
  transform: translate(-50%, 0);
  width: $fab-size;
  height: $fab-size;
  border-radius: 50%;
  background: linear-gradient(145deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  box-shadow:
    0 6px 20px rgba(99, 102, 241, 0.45),
    0 2px 8px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 101;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:active,
  &.fab--pressed {
    transform: translate(-50%, 0) scale(0.92);
    box-shadow:
      0 2px 12px rgba(99, 102, 241, 0.4),
      0 1px 4px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }
}
</style>
