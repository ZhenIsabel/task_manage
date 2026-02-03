<template>
  <view class="edit-page page-with-nav">
    <view class="form-content-wrap">
      <scroll-view scroll-y class="form-content" :style="scrollViewHeight ? { height: scrollViewHeight } : {}" :show-scrollbar="false">
        <view class="form-content-inner" :style="scrollViewHeight ? { minHeight: scrollViewHeight } : {}">
          <view class="nav-header">
            <view class="glass-btn" @tap="goBack">
              <uni-icons type="back" size="24" color="inherit" />
            </view>
            <text class="nav-title">{{ taskId ? '编辑任务' : '创建任务' }}</text>
            <view v-if="taskId" class="glass-btn red-theme" @tap="handleDelete">
              <uni-icons type="trash" size="20" color="#dc2626" />
            </view>
            <view v-else class="placeholder-box"></view>
          </view>

          <view class="glass-card form-section">
            <text class="label">任务标题</text>
            <input
              v-model="form.title"
              placeholder="做什么？"
              placeholder-class="input-placeholder"
              class="input-title"
            />
          </view>

          <view class="row-2-col">
            <view class="glass-card form-section">
              <text class="label flex-label"><uni-icons type="info" size="12" color="inherit" /> 重要程度</text>
              <view class="toggle-group">
                <view class="toggle-btn" :class="{ active: form.importance === 'low' }" @tap="form.importance = 'low'">一般</view>
                <view class="toggle-btn red" :class="{ active: form.importance === 'high' }" @tap="form.importance = 'high'">重要</view>
              </view>
            </view>
            <view class="glass-card form-section">
              <text class="label flex-label"><uni-icons type="notification" size="12" color="inherit" /> 紧急程度</text>
              <view class="toggle-group">
                <view class="toggle-btn" :class="{ active: form.urgency === 'low' }" @tap="form.urgency = 'low'">不急</view>
                <view class="toggle-btn orange" :class="{ active: form.urgency === 'high' }" @tap="form.urgency = 'high'">紧急</view>
              </view>
            </view>
          </view>

          <view class="glass-card form-section row-between">
            <text class="label-row"><uni-icons type="calendar" size="16" color="inherit" /> 截止日期</text>
            <picker mode="date" :value="formatDateForPicker(form.dueDate)" @change="handleDateChange">
              <view class="picker-value">{{ form.dueDate ? formatDate(form.dueDate) : '选择日期' }}</view>
            </picker>
          </view>

          <view class="glass-card form-section h-large">
            <text class="label">备注</text>
            <textarea
              v-model="form.note"
              placeholder="添加详细描述..."
              placeholder-class="input-placeholder"
              class="input-area"
              maxlength="-1"
            />
          </view>
          <view class="bottom-spacer" />
        </view>
      </scroll-view>
    </view>

    <view
      class="bottom-action"
      data-agent="bottom-action-wrap"
      @tap.stop="onSaveTap"
    >
      <view class="btn-save" :class="{ disabled: !(form.title || '').trim() }">保 存</view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, getCurrentInstance } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import dataManager from '@/services/dataManager.js';
import { formatDate, formatDateForPicker } from '@/utils/date.js';

const taskId = ref('');
const scrollViewHeight = ref('');
const saving = ref(false);
const form = reactive({
  title: '',
  note: '',
  createdAt: '',
  dueDate: '',
  importance: 'low',
  urgency: 'low',
});

const defaultForm = () => ({
  title: '',
  note: '',
  createdAt: new Date().toISOString(),
  dueDate: new Date().toISOString(),
  importance: 'low',
  urgency: 'low',
});

onLoad((options) => {
  if (options && options.id) taskId.value = options.id;
});

onMounted(() => {
  if (taskId.value) {
    const list = dataManager.loadTasksFromStorage();
    const task = list.find((t) => t.id === taskId.value);
    if (task) {
      form.title = task.title ?? '';
      form.note = task.note ?? '';
      form.createdAt = task.createdAt ?? new Date().toISOString();
      form.dueDate = task.dueDate ?? null;
      form.importance = task.importance ?? 'low';
      form.urgency = task.urgency ?? 'low';
    }
  } else {
    Object.assign(form, defaultForm());
  }
  try {
    const sys = uni.getSystemInfoSync();
    const winH = sys.windowHeight || sys.screenHeight || 0;
    const top = 60 + 36 + 24;
    const bottom = 50 + 16 + 40;
    if (winH > top + bottom) scrollViewHeight.value = (winH - top - bottom) + 'px';
  } catch (_) {}
  // #region agent log
  nextTick(() => {
    const instance = getCurrentInstance();
    if (!instance || !instance.proxy) return;
    const q = uni.createSelectorQuery().in(instance.proxy);
    q.select('.bottom-action').boundingClientRect();
    q.select('.form-content').boundingClientRect();
    q.selectViewport().fields({ size: true, scrollOffset: true });
    q.exec((res) => {
      const [bottomAction, formContent, viewport] = res || [];
      fetch('http://127.0.0.1:7244/ingest/dc396521-042c-48ee-aa0f-06555631d63b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'edit.vue:onMounted',message:'layout query',data:{bottomAction:bottomAction||null,formContentHeight:formContent?.height,viewportHeight:viewport?.height,viewportScrollTop:viewport?.scrollTop},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A,B,C,D'})}).catch(()=>{});
    });
  });
  // #endregion
});

function goBack() {
  uni.navigateBack();
}

function handleDateChange(e) {
  form.dueDate = e.detail.value ? new Date(e.detail.value).toISOString() : null;
}

function onSaveTap() {
  if (saving.value) return;
  const title = (form.title || '').trim();
  if (!title) {
    uni.showToast({ title: '请填写标题', icon: 'none' });
    return;
  }
  handleSave();
}

function handleSave() {
  if (saving.value) return;
  saving.value = true;
  const payload = {
    title: form.title.trim(),
    note: form.note ?? '',
    createdAt: form.createdAt ?? new Date().toISOString(),
    dueDate: form.dueDate || null,
    importance: form.importance,
    urgency: form.urgency,
  };
  if (taskId.value) {
    const list = dataManager.loadTasksFromStorage();
    const task = list.find((t) => t.id === taskId.value);
    if (!task) {
      uni.showToast({ title: '任务不存在', icon: 'none' });
      return;
    }
    const updated = { ...task, ...payload };
    dataManager.saveTask(updated, true).then(() => {
      uni.showToast({ title: '已保存', icon: 'success' });
      setTimeout(() => {
        saving.value = false;
        uni.navigateBack();
      }, 300);
    }).catch(() => {
      saving.value = false;
      uni.showToast({ title: '保存失败', icon: 'none' });
    });
  } else {
    const newTask = {
      id: Math.random().toString(36).substr(2, 9),
      ...payload,
      isCompleted: false,
      completedAt: null,
    };
    dataManager.saveTask(newTask, true).then(() => {
      uni.showToast({ title: '已保存', icon: 'success' });
      setTimeout(() => {
        saving.value = false;
        uni.navigateBack();
      }, 300);
    }).catch(() => {
      saving.value = false;
      uni.showToast({ title: '保存失败', icon: 'none' });
    });
  }
}

function handleDelete() {
  uni.showModal({
    title: '确认删除',
    content: '删除后无法恢复，确定删除吗？',
    success: (res) => {
      if (!res.confirm) return;
      dataManager.deleteTask(taskId.value, true).then(() => {
        uni.showToast({ title: '已删除', icon: 'success' });
        setTimeout(() => uni.navigateBack(), 300);
      }).catch(() => {});
    },
  });
}
</script>

<style lang="scss" scoped>
.edit-page {
  min-height: 100vh;
  padding: 20px 00px 00px;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
  display: flex;
  flex-direction: column;
}
.nav-header {
  justify-content: space-between;
}
.glass-btn.red-theme {
  background: rgba(254, 226, 226, 0.8);
  color: #dc2626;
}
.placeholder-box {
  width: 36px;
}
.nav-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  flex: 1;
  text-align: left;
}
.form-content-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.form-content {
  flex: 1;
  min-height: 0;
  height: 100%;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.form-content::-webkit-scrollbar {
  display: none;
}
.form-content-inner {
  padding: 30px 40px 60px;
  /* min-height 由 :style 绑定 scrollViewHeight，避免 100% 解析成 100vh 导致底部可滚空白 */
}
.glass-card {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 20px;
  margin-bottom: 16px;
}
.form-section {
  padding: 16px;
}
.form-section .label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.flex-label {
  display: flex;
  align-items: center;
  gap: 4px;
}
.input-title {
  width: 100%;
  height: 30px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}
.input-placeholder {
  color: #9ca3af;
}

.row-2-col {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.row-2-col .form-section {
  flex: 1;
  margin-bottom: 0;
}
.toggle-group {
  display: flex;
  gap: 6px;
}
.toggle-btn {
  flex: 1;
  padding: 6px 0;
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.03);
  color: #6b7280;
  &.active {
    background: #3b82f6;
    color: white;
    &.red {
      background: #ef4444;
    }
    &.orange {
      background: #f97316;
    }
  }
}

.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.label-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
}
.picker-value {
  font-size: 14px;
  color: #1f2937;
}

.h-large {
  height: 140px;
}
.input-area {
  width: 100%;
  height: 100%;
  font-size: 14px;
  line-height: 1.5;
  box-sizing: border-box;
}

.bottom-spacer {
  flex-shrink: 0;
}
.bottom-action {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 16px 20px;
  padding-bottom: calc(16px + constant(safe-area-inset-bottom, 0));
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0));
  background: #fff;
  z-index: 100;
  box-sizing: border-box;
  cursor: pointer;
}
.btn-save {
  width: 100%;
  height: 50px;
  line-height: 50px;
  background: linear-gradient(145deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  box-shadow:
    0 6px 20px rgba(99, 102, 241, 0.45),
    0 2px 8px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  color: white;
  border: none;
  border-radius: 14px;
  font-weight: 600;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
  &.disabled {
    opacity: 0.2;
    pointer-events: none;
  }
}
</style>
