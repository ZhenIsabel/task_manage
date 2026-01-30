
<template>
  <view class="container">
    <view class="background-blobs">
      <view class="blob blue"></view>
      <view class="blob purple"></view>
      <view class="blob pink"></view>
    </view>

    <view class="app-window">
      <view v-if="view === 'matrix'" class="view-container matrix-view">
        <view class="header">
          <view>
            <text class="main-title">不想干活</text>
          </view>
          <view class="header-right">
            <view class="date-display">
              <text class="day">{{ currentDay }}</text>
              <text class="month">{{ currentMonth }}</text>
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
                  @click="navigateTo('edit', task)"
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
                  @click="navigateTo('edit', task)"
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
                  @click="navigateTo('edit', task)"
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
                  @click="navigateTo('edit', task)"
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

      <view v-if="view === 'create' || view === 'edit'" class="view-container editor-view slide-in-up">
        <view class="nav-header">
          <view class="btn-icon glass-btn" @click="navigateTo('matrix')">
            <uni-icons type="back" size="24" color="inherit" />
          </view>
          <text class="nav-title">{{ currentTask ? '编辑任务' : '创建任务' }}</text>
          <view v-if="currentTask" class="btn-icon glass-btn red-theme" @click="handleDeleteTask(currentTask.id)">
            <uni-icons type="trash" size="20" color="#dc2626" />
          </view>
          <view v-else class="placeholder-box"></view>
        </view>

        <scroll-view scroll-y="true" class="form-content":show-scrollbar="false">
          <view class="glass-card form-section">
            <text class="label">任务标题</text>
            <input 
              v-model="formData.title" 
              placeholder="做什么？" 
              placeholder-class="input-placeholder"
              class="input-title"
            />
          </view>

          <view class="row-2-col">
            <view class="glass-card form-section">
              <text class="label flex-label"><uni-icons type="info" size="12" color="inherit" /> 重要程度</text>
              <view class="toggle-group">
                <view 
                  class="toggle-btn" 
                  :class="{ active: formData.importance === 'low' }"
                  @click="formData.importance = 'low'"
                >一般</view>
                <view 
                  class="toggle-btn red" 
                  :class="{ active: formData.importance === 'high' }"
                  @click="formData.importance = 'high'"
                >重要</view>
              </view>
            </view>

            <view class="glass-card form-section">
              <text class="label flex-label"><uni-icons type="notification" size="12" color="inherit" /> 紧急程度</text>
              <view class="toggle-group">
                <view 
                  class="toggle-btn" 
                  :class="{ active: formData.urgency === 'low' }"
                  @click="formData.urgency = 'low'"
                >不急</view>
                <view 
                  class="toggle-btn orange" 
                  :class="{ active: formData.urgency === 'high' }"
                  @click="formData.urgency = 'high'"
                >紧急</view>
              </view>
            </view>
          </view>

          <view class="glass-card form-section row-between">
            <text class="label-row"><uni-icons type="calendar" size="16" color="inherit" /> 截止日期</text>
            <picker mode="date" :value="formatDateForPicker(formData.dueDate)" @change="handleDateChange">
               <view class="picker-value">
                 {{ formData.dueDate ? formatDate(formData.dueDate) : '选择日期' }}
               </view>
            </picker>
          </view>

          <view class="glass-card form-section h-large">
            <text class="label">备注</text>
            <textarea 
              v-model="formData.note" 
              placeholder="添加详细描述..." 
              placeholder-class="input-placeholder"
              class="input-area"
              maxlength="-1"
            />
          </view>
        </scroll-view>

        <view class="bottom-action">
          <button 
            class="btn-save" 
            :disabled="!formData.title.trim()" 
            @click="handleSaveTask"
          >保 存</button>
        </view>
      </view>

      <view v-if="view === 'archive'" class="view-container archive-view fade-in">
        <view class="nav-header">
          <view class="btn-icon glass-btn" @click="navigateTo('matrix')">
            <uni-icons type="back" size="24" color="inherit" />
          </view>
          <view class="header-text-col">
            <text class="nav-title">已完成任务</text>
            <text class="nav-sub">共 {{ archivedTasks.length }} 项历史记录</text>
          </view>
        </view>

        <scroll-view scroll-y="true" class="archive-list":show-scrollbar="false">
          <view v-if="archivedTasks.length === 0" class="empty-archive">
            <uni-icons type="checkmarkempty" size="48" color="#ccc" />
            <text>暂无已完成任务</text>
          </view>
          <view v-else v-for="task in archivedTasks" :key="task.id" class="glass-card archive-item">
            <view class="archive-info">
              <text class="archive-title">{{ task.title }}</text>
              <text class="archive-date">{{ formatDate(task.completedAt) }} 完成</text>
            </view>
            <view class="btn-restore" @click="handleToggleTask(task.id)">
              <uni-icons type="redo" size="16" color="#15803d" />
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- 底部 Dock 液态玻璃风格 -->
      <view class="bottom-dock">
        <view class="dock-bar">
        <view class="dock-item" @click="goSettings">
            <view class="dock-icon-wrap">
              <uni-icons type="gear" size="20" color="inherit" />
            </view>
          </view>
          <view 
            v-if="dataManager.hasRemoteConfig()"
            class="dock-item" 
            :class="{ loading }"
            @click="doSyncToServer"
          >
            <view class="dock-icon-wrap">
              <uni-icons type="cloud-upload" size="20" color="inherit" />
            </view>
          </view>

          <view 
            v-if="dataManager.hasRemoteConfig()"
            class="dock-item" 
            :class="{ loading }"
            @click="doSyncFromServer"
          >
            <view class="dock-icon-wrap">
              <uni-icons type="cloud-download" size="20" color="inherit" />
            </view>
          </view>

          <view class="dock-item" @click="navigateTo('archive')">
            <view class="dock-icon-wrap">
              <uni-icons type="checkmarkempty" size="20" color="inherit" />
            </view>
          </view>

          <view class="dock-item" @click="navigateTo('create')">
            <view class="dock-icon-wrap">
              <uni-icons type="plus" size="20" color="inherit" />
            </view>
          </view>
          
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, reactive, onMounted, getCurrentInstance } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import dataManager from '@/services/dataManager.js';

// --- Utils ---
const generateId = () => Math.random().toString(36).substr(2, 9);
const isToday = (dateString) => {
  if (!dateString) return false;
  const date = new Date(dateString);
  const today = new Date();
  return date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear();
};
const formatDate = (dateString) => {
  if (!dateString) return '';
  const d = new Date(dateString);
  return `${d.getMonth() + 1}/${d.getDate()}`;
};
const formatDateForPicker = (isoString) => {
    if (!isoString) return '';
    return isoString.split('T')[0];
}
const pickEditable = (t) => ({
  title: t?.title ?? '',
  note: t?.note ?? '',
  createdAt: t?.createdAt ?? new Date().toISOString(),
  dueDate: t?.dueDate ?? null,
  importance: t?.importance ?? 'low',
  urgency: t?.urgency ?? 'low',
});

// --- Data ---
const tasks = ref([]);
const view = ref('matrix');
const currentTask = ref(null);
const loading = ref(false);
const syncStatus = ref(null);

const defaultForm = {
    title: '',
    note: '',
    createdAt: '',
    dueDate: '',
    importance: 'low',
    urgency: 'low'
};
const formData = reactive({ ...defaultForm });

// --- Computed ---
const currentDay = computed(() => new Date().getDate());
const currentMonth = computed(() => {
    const m = new Date().getMonth() + 1;
    const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
    return `${m}月 · ${week}`;
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

const archivedTasks = computed(() => tasks.value.filter(t => t.isCompleted));

// --- 数据加载与同步 ---
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

function doSyncToServer() {
  if (!dataManager.hasRemoteConfig()) return;
  loading.value = true;
  dataManager.syncToServer(tasks.value).then((res) => {
    loading.value = false;
    syncStatus.value = dataManager.getLastSyncStatus();
    if (res.error) uni.showToast({ title: res.error || '上传失败', icon: 'none' });
  });
}

onMounted(() => {
  loadTasks();
  if (dataManager.hasRemoteConfig()) doSyncFromServer();
  // #region agent log
  setTimeout(() => {
    const hasRemote = dataManager.hasRemoteConfig();
    fetch('http://127.0.0.1:7244/ingest/dc396521-042c-48ee-aa0f-06555631d63b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'index.vue:onMounted',message:'Dock debug',data:{hasRemoteConfig:hasRemote},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
    const q = uni.createSelectorQuery().in(getCurrentInstance());
    q.select('.dock-bar').boundingClientRect();
    q.select('.dock-icon-wrap').boundingClientRect();
    q.exec((res) => {
      fetch('http://127.0.0.1:7244/ingest/dc396521-042c-48ee-aa0f-06555631d63b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'index.vue:onMounted',message:'Dock dimensions',data:{dockBar:res[0],iconWrap:res[1]},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
    });
  }, 500);
  // #endregion
});

onShow(() => {
  loadTasks();
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

const navigateTo = (screen, task = null) => {
  currentTask.value = task;
  if (screen === 'create') {
      Object.assign(formData, { ...defaultForm, createdAt: new Date().toISOString(), dueDate: new Date().toISOString() });
  } else if (screen === 'edit' && task) {
      Object.assign(formData, pickEditable(task));
  }
  view.value = screen;
};

const handleSaveTask = () => {
  const payload = { ...pickEditable(formData) };

  if (currentTask.value) {
    const idx = tasks.value.findIndex(t => t.id === currentTask.value.id);
    if (idx !== -1) {
      const updated = {
        ...tasks.value[idx],
        ...payload,
      };
      tasks.value[idx] = updated;
      dataManager.saveTask(updated, true).then((res) => {
        if (res && res.tasks) tasks.value = res.tasks;
      }).catch(() => {});
    }
  } else {
    const newTask = {
      id: generateId(),
      ...payload,
      isCompleted: false,
      completedAt: null,
    };
    tasks.value.push(newTask);
    dataManager.saveTask(newTask, true).then((res) => {
      if (res && res.tasks) tasks.value = res.tasks;
    }).catch(() => {});
  }

  navigateTo('matrix');
};

const handleDeleteTask = (id) => {
  tasks.value = tasks.value.filter(t => t.id !== id);
  dataManager.deleteTask(id, true).then((res) => {
    if (res && res.tasks) tasks.value = res.tasks;
  }).catch(() => {});
  navigateTo('matrix');
};

const handleDateChange = (e) => {
    formData.dueDate = new Date(e.detail.value).toISOString();
};

function goSettings() {
  uni.navigateTo({ url: '/pages/settings/settings' });
}
</script>

<style lang="scss" scoped>
/* 1. 全局变量与基础设置 */
$glass-bg: rgba(255, 255, 255, 0.45);
$glass-border: rgba(255, 255, 255, 0.6);
$shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);

/* 强制使用边框盒模型，防止 padding 撑大元素导致重叠 */
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
  display: flex; /* 使用 Flex 纵向布局 */
  flex-direction: column;
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

/* Glass Card 基础样式 */
.glass-card {
  background: $glass-bg;
  border: 1px solid $glass-border;
  box-shadow: $shadow;
  border-radius: 20px;
  overflow: hidden;
  /* 移除 backdrop-filter 以提升部分安卓机性能，依靠背景色透明度 */
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
  align-items: flex-end;
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
  .date-display { text-align: right; margin-left: 4px; }
  .day { font-size: 24px; font-weight: 700; display: block; line-height: 1; color: #1f2937; }
  .month { font-size: 12px; color: #6b7280; font-weight: 500; margin-top: 4px; display: block; }
}

/* 核心修复：使用 Grid 布局替代 Flex wrap */
.grid-layout {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  padding-bottom: 72px;
  min-height: 0;
}
.grid-item {
  width: calc(50% - 6px);   /* gap 的一半 */
  height: calc(50% - 6px);
  min-height: 0;
  min-width: 0;
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

/* --- 底部 Dock 液态玻璃风格 --- */
.bottom-dock {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
}

.dock-bar {
  width: 100%;
  display: flex;
  align-items: stretch;
  gap: 6px;
  padding: 6px 6px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 
    0 4px 20px rgba(31, 38, 135, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.dock-item {
  flex: 1;
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 4px 2px;
  border-radius: 14px;
  color: #374151;
  transition: all 0.2s ease;
  min-width: 0;

  &:active {
    transform: scale(0.92);
    background: rgba(255, 255, 255, 0.3);
  }

  &.loading {
    opacity: 0.6;
    pointer-events: none;
  }
}

.dock-icon-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.2s ease;
}

.dock-item:active .dock-icon-wrap {
  background: rgba(255, 255, 255, 0.7);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 1);
}

/* --- 编辑/新建页面 (Editor) --- */
.editor-view, .archive-view {
  background: rgba(245, 245, 247, 0.85); /* 稍微不透明一点，防止背景干扰 */
  backdrop-filter: blur(20px);
  z-index: 20;
}

.nav-header {
  padding: 50px 20px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.glass-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(255,255,255,0.6);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  
  &.red-theme { background: rgba(254, 226, 226, 0.8); color: #dc2626; }
}
.placeholder-box { width: 36px; }

.nav-title { font-size: 17px; font-weight: 600; color: #111827; }

.form-content {
  flex: 1;
  height: 0;
  padding: 0 20px;
}

.form-section {
  padding: 16px;
  margin-bottom: 16px;
  background: rgba(255,255,255,0.6);
}

.label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.flex-label { display: flex; align-items: center; gap: 4px; }

.input-title {
  width: 100%;
  height: 30px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.row-2-col {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  .form-section { flex: 1; margin-bottom: 0; }
}

.toggle-group { display: flex; gap: 6px; }
.toggle-btn {
  flex: 1;
  padding: 6px 0;
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  background: rgba(0,0,0,0.03);
  color: #6b7280;
  
  &.active {
    background: #3b82f6; color: white;
    &.red { background: #ef4444; }
    &.orange { background: #f97316; }
  }
}

.row-between { display: flex; justify-content: space-between; align-items: center; }
.label-row { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 500; color: #4b5563; }
.picker-value { font-size: 14px; color: #1f2937; }

.h-large { height: 140px; }
.input-area { width: 100%; height: 100%; font-size: 14px; line-height: 1.5; }

.bottom-action {
  padding: 16px 20px 40px;
  background: linear-gradient(to top, rgba(242,242,247, 1), rgba(242,242,247, 0));
  flex-shrink: 0;
}

.btn-save {
  width: 100%; height: 50px; line-height: 50px;
  background: #1f2937; color: white;
  border-radius: 14px; font-weight: 600; font-size: 16px;
  
  &[disabled] { opacity: 0.5; }
}

/* --- Archive View --- */
.header-text-col { flex: 1; margin-left: 12px; }
.nav-sub { font-size: 11px; color: #6b7280; }

.archive-list { flex: 1; height: 0; padding: 0 20px 20px; }
.empty-archive { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 50%; color: #9ca3af; gap: 10px; font-size: 13px; }

.archive-item {
  padding: 14px; margin-bottom: 10px;
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(255,255,255,0.6);
}
.archive-info { flex: 1; overflow: hidden; margin-right: 10px; }
.archive-title { font-size: 14px; color: #374151; text-decoration: line-through; opacity: 0.6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.archive-date { font-size: 11px; color: #9ca3af; margin-top: 2px; }

.btn-restore {
  padding: 6px; border-radius: 50%;
  background: #dcfce7; color: #15803d;
  display: flex; align-items: center; justify-content: center;
}

/* 动画 */
.slide-in-up { animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.fade-in { animation: fadeIn 0.2s ease-out; }

@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
</style>