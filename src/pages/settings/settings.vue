<template>
  <view class="settings-page page-with-nav">
    <view class="nav-header">
      <view class="btn-back glass-btn" @click="goBack">
        <uni-icons type="back" size="24" color="inherit" />
      </view>
      <text class="nav-title">设置</text>
    </view>

    <view class="form-card glass-card">
      <text class="label">服务器地址</text>
      <input
        v-model="form.api_base_url"
        class="input"
        placeholder="例如 https://your-server.com 或 http://localhost:5000"
        placeholder-class="placeholder"
      />
      <text class="label">API Token</text>
      <input
        v-model="form.api_token"
        class="input"
        type="text"
        placeholder="与服务器配置的 token 一致"
        placeholder-class="placeholder"
      />
      <button class="btn-save" @click="saveConfig">保存配置</button>
    </view>

    <view v-if="hasRemote" class="actions-card glass-card">
      <text class="section-title">数据同步 / 备份</text>
      <button class="btn-action" @click="syncFrom">从服务器拉取任务</button>
      <button class="btn-action" :disabled="uploadDisabled" :class="{ disabled: uploadDisabled }" @click="syncTo">上传本地任务到服务器</button>
      <button class="btn-action danger" :disabled="clearDisabled" :class="{ disabled: clearDisabled }" @click="clearAndUpload">清空服务器并用本地覆盖</button>
      <view v-if="lastSync" class="sync-info">
        <text>最近同步：{{ lastSync.sync_type }} - {{ lastSync.message }}</text>
      </view>
    </view>

    <view class="tip">
      <text>与 task_manage 项目的 server_example 或自建 API 对接，需配置相同的 api_base_url 和 api_token。</text>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { getRemoteConfig, setRemoteConfig } from '@/api/config.js';
import dataManager from '@/services/dataManager.js';

const form = reactive({
  api_base_url: '',
  api_token: '',
});

const hasRemote = ref(false);
const lastSync = ref(null);
// 暂时禁用上传与清空覆盖功能
const uploadDisabled = true;
const clearDisabled = true;

onMounted(() => {
  const cfg = getRemoteConfig();
  form.api_base_url = cfg.api_base_url || '';
  form.api_token = cfg.api_token || '';
  hasRemote.value = !!cfg.api_base_url;
  lastSync.value = dataManager.getLastSyncStatus();
});

function saveConfig() {
  setRemoteConfig({
    api_base_url: (form.api_base_url || '').trim(),
    api_token: (form.api_token || '').trim(),
  });
  hasRemote.value = !!form.api_base_url.trim();
  uni.showToast({ title: '已保存', icon: 'success' });
}

function goBack() {
  uni.navigateBack();
}

function syncFrom() {
  const local = dataManager.loadTasksFromStorage();
  uni.showLoading({ title: '拉取中...' });
  dataManager.syncFromServer(local).then((res) => {
    uni.hideLoading();
    lastSync.value = dataManager.getLastSyncStatus();
    if (res.success) {
      uni.showToast({ title: '拉取成功，请返回首页查看', icon: 'success' });
    } else {
      uni.showToast({ title: res.error || '拉取失败', icon: 'none' });
    }
  });
}

function syncTo() {
  if (uploadDisabled) return;
  const local = dataManager.loadTasksFromStorage();
  uni.showLoading({ title: '上传中...' });
  dataManager.syncToServer(local).then((res) => {
    uni.hideLoading();
    lastSync.value = dataManager.getLastSyncStatus();
    if (res.success) {
      uni.showToast({ title: `已上传 ${res.uploaded || 0} 条`, icon: 'success' });
    } else {
      uni.showToast({ title: res.error || '上传失败', icon: 'none' });
    }
  });
}

function clearAndUpload() {
  if (clearDisabled) return;
  uni.showModal({
    title: '确认',
    content: '将先清空服务器上的任务，再用本地任务覆盖。是否继续？',
    success: (r) => {
      if (!r.confirm) return;
      const local = dataManager.loadTasksFromStorage();
      uni.showLoading({ title: '执行中...' });
      dataManager.clearServerAndUpload(local).then((res) => {
        uni.hideLoading();
        lastSync.value = dataManager.getLastSyncStatus();
        if (res.success) {
          uni.showToast({ title: '已完成', icon: 'success' });
        } else {
          uni.showToast({ title: res.error || '失败', icon: 'none' });
        }
      });
    },
  });
}
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  padding: 60px 20px 40px;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
}
.settings-page.page-with-nav .glass-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.6);
}
.nav-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}
.glass-card {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 20px;
  margin-bottom: 16px;
}
.form-card .label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
  margin-top: 12px;
}
.form-card .label:first-child {
  margin-top: 0;
}
.input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  font-size: 14px;
  box-sizing: border-box;
}
.placeholder {
  color: #9ca3af;
}
.btn-save {
  margin-top: 20px;
  width: 100%;
  height: 44px;
  line-height: 44px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
}
.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 12px;
  display: block;
}
.btn-action {
  width: 100%;
  height: 44px;
  line-height: 44px;
  background: rgba(99, 102, 241, 0.15);
  color: #4f46e5;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}
.btn-action.danger {
  background: rgba(220, 38, 38, 0.08);
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.2);
}
.btn-action.disabled {
  opacity: 0.5;
  color: #9ca3af;
  border-color: rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.04);
}
.btn-action.danger.disabled {
  color: #9ca3af;
  border-color: rgba(0, 0, 0, 0.08);
}
.sync-info {
  margin-top: 12px;
  font-size: 12px;
  color: #6b7280;
}
.tip {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
  padding: 0 4px;
}
</style>
