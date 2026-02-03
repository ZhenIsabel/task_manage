
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
                  @click="goEdit(task)"
                >
                  <view class="checkbox" :class="{ checked: task.isCompleted }" @click.stop="handleToggleTask(task.id)">
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
                <text class="quadrant-title">重要·好急</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.tr.length === 0" class="empty-state">无任务</view>
                <template v-else>
                <view
                  v-for="task in quadrantData.tr"
                  :key="task.id"
                  class="task-item"
                  @click="goEdit(task)"
                >
                  <view class="checkbox" :class="{ checked: task.isCompleted }" @click.stop="handleToggleTask(task.id)">
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
                <text class="quadrant-title">垃圾</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.bl.length === 0" class="empty-state">无任务</view>
                <template v-else>
                <view
                  v-for="task in quadrantData.bl"
                  :key="task.id"
                  class="task-item"
                  @click="goEdit(task)"
                >
                  <view class="checkbox" :class="{ checked: task.isCompleted }" @click.stop="handleToggleTask(task.id)">
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
                <text class="quadrant-title">急啥</text>
              </view>
              <scroll-view scroll-y class="task-list" :show-scrollbar="false">
                <view v-if="quadrantData.br.length === 0" class="empty-state">无任务</view>
                <template v-else>
                <view
                  v-for="task in quadrantData.br"
                  :key="task.id"
                  class="task-item"
                  @click="goEdit(task)"
                >
                  <view class="checkbox" :class="{ checked: task.isCompleted }" @click.stop="handleToggleTask(task.id)">
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

      <!-- 底部 Dock：仅保留高频操作；新建任务为 FAB -->
      <view class="bottom-dock">
        <view class="dock-bar">
          <view class="dock-item" @click="goSettings">
            <view class="dock-icon-wrap">
              <uni-icons type="gear" size="28" color="inherit" />
            </view>
          </view>
          <view class="dock-item dock-item-spacer" aria-hidden="true" />
          <view class="dock-item" @click="goArchive">
            <view class="dock-icon-wrap">
              <uni-icons type="checkmarkempty" size="28" color="inherit" />
            </view>
          </view>
        </view>
        <!-- FAB：新建任务，居中悬浮 -->
        <view
          class="fab"
          :class="{ 'fab--pressed': fabPressed }"
          @click="onFabTap"
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

// --- Data ---
const tasks = ref([]);
const syncStatus = ref(null);
const fabPressed = ref(false);
const loading = ref(false);

// --- Computed ---
const currentWeekday = computed(() => {
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
});
const currentDateStr = computed(() => {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${m}.${day}`;
});

const getQuadrantTasks = (imp, urg) => {
  return tasks.value.filter(t => {
    const isVisible = !t.isCompleted || (t.isCompleted && isToday(t.completedAt));
    const matchImp = imp === 'high' ? t.importance === 'high' : t.importance !== 'high';
    const matchUrg = urg === 'high' ? t.urgency === 'high' : t.urgency !== 'high';
    return isVisible && matchImp && matchUrg;
  });
};

const quadrantData = computed(() => ({
  tl: getQuadrantTasks('high', 'low'),
  tr: getQuadrantTasks('high', 'high'),
  bl: getQuadrantTasks('low', 'low'),
  br: getQuadrantTasks('low', 'high'),
}));

// --- 数据加载与同步 ---
function loadTasks() {
  const local = dataManager.loadTasksFromStorage();
  tasks.value = local.length ? local : [];
  syncStatus.value = dataManager.getLastSyncStatus();
}

//从服务器拉取任务并合并到本地
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

//首页组件挂载完成后就从服务器拉取任务到本地
onMounted(() => {
  loadTasks();
  if (dataManager.hasRemoteConfig()) doSyncFromServer();
});

onShow(() => {
  loadTasks();
});

// 物理返回：首页时确认退出
onBackPress(() => {
  uni.showModal({
    title: '提示',
    content: '是否退出应用？',
    success: (res) => {
      if (res.confirm && typeof plus !== 'undefined') {
        plus.runtime.quit();
      }
    }
  });
  return true;
});

// --- Methods ---
const handleToggleTask = (id) => {
  const idx = tasks.value.findIndex(t => t.id === id);
  if (idx !== -1) {
    const t = tasks.value[idx];
    const newState = !t.isCompleted;
    const updated = {
      ...t,
      isCompleted: newState,
      completedAt: newState ? new Date().toISOString() : null
    };
    tasks.value[idx] = updated;
    dataManager.saveTask(updated, true).catch(() => {});
  }
};

function goEdit(task) {
  uni.navigateTo({ url: '/pages/edit/edit?id=' + encodeURIComponent(task.id) });
}
function goCreate() {
  uni.navigateTo({ url: '/pages/edit/edit' });
}
function onFabTap() {
  goCreate();
}
function goArchive() {
  uni.navigateTo({ url: '/pages/archive/archive' });
}
function goSettings() {
  uni.navigateTo({ url: '/pages/settings/settings' });
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
*, *::before, *::after {
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

/* 2. 背景动画 (保持不变) */
.background-blobs {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
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

/* 3. 主布局结构 */
.app-window {
  position: relative;
  width: 100%;
  height: 100%;
  z-index: 1;
  display: flex;
  flex-direction: column;

  box-sizing: border-box;
}

/* 通用视图容器 */
.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

/*四宫格区域*/
.grid-layout{
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  padding-bottom: 16px;
  min-height: 0;
    /* 底部留白避让 FAB + Dock，避免内容被遮挡 */
  padding-bottom: calc(80px + constant(safe-area-inset-bottom, 0px));
  padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
}
.grid-item {
  width: calc(50% - 6px);   /* gap 的一半 */
  height: calc(50% - 6px);
  min-height: 0;
  min-width: 0;
}


/* --- 修复后的四象限视图 (Matrix View) --- */

.matrix-view {
  /* 确保占满屏幕 */
  height: 100%; 
}

.header {
  /* 头部高度固定或自适应，不设绝对高度，靠 padding 撑开 */
  padding: 50px 24px 10px; /* 顶部留出状态栏空间 */
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  flex-shrink: 0; /* 防止头部被压缩 */
  
  .sub-title { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px; }
  .main-title { font-size: 28px; font-weight: 800; color: #111827; line-height: 1.2; }
  
  .header-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .sync-wrap { display: flex; gap: 6px; }
  .btn-sync, .btn-settings {
    display: flex; align-items: center; gap: 4px; padding: 6px 10px; border-radius: 20px;
    font-size: 12px; font-weight: 600; color: #374151;
    &.loading { opacity: 0.7; }
  }
  .btn-settings { padding: 6px; }
  .date-display { text-align: right; margin-left: 4px;height: 28px; }
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

/* 象限卡片内部 */
.glow-bg {
  position: absolute;
  top: -30%; right: -30%; width: 70%; height: 70%;
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
  flex-shrink: 0; /* 标题不被压缩 */
  
  .quadrant-title { font-size: 11px; font-weight: 800; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.5px; }
  .icon-wrap { opacity: 0.7; display: flex; }
}

/* 列表滚动区域 */
.task-list {
  flex: 1;
  height: 0; /* 关键：配合 flex:1 启用 scroll-view 内部滚动 */
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
  background: rgba(255,255,255,0.3);
  border-radius: 10px;
  margin-bottom: 8px;
  
  &:active { background: rgba(255,255,255,0.5); }
}

.checkbox {
  width: 18px; height: 18px;
  border-radius: 5px;
  border: 1.5px solid rgba(107, 114, 128, 0.4);
  display: flex; align-items: center; justify-content: center;
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
  word-break: break-all; /* 防止长文本撑开布局 */
  
  &.completed {
    text-decoration: line-through;
    opacity: 0.5;
  }
}

/* --- 底部 Dock：仅设置 + 归档；FAB 居中悬浮 --- */
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
  pointer-events: none;
}
.bottom-dock > * {
  pointer-events: auto;
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
  box-shadow:$shadow;
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
  box-shadow:$shadow;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.dock-item:active .dock-icon-wrap {
  background: rgba(255, 255, 255, 0.75);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 1);
}

/* FAB：新建任务，居中悬浮，层级高于 Dock */
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