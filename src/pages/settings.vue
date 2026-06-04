<template>
  <view class="settings-page page-with-nav">
    <view class="nav-header">
      <view class="btn-back glass-btn" @tap="goBack">
        <uni-icons type="back" size="24" color="inherit" />
      </view>
      <text class="nav-title">设置</text>
    </view>

    <view class="form-card glass-card">
      <view class="switch-row">
        <view>
          <text class="section-title">远程同步</text>
          <text class="section-subtitle">仅接入普通任务 tasks，同步策略与 PC 端一致。</text>
        </view>
        <switch :checked="form.enabled" color="#6366f1" @change="handleEnabledChange" />
      </view>

      <text class="label">服务器地址</text>
      <input
        v-model="form.api_base_url"
        class="input"
        placeholder="例如 https://your-server.com"
        placeholder-class="placeholder"
      />

      <text class="label">用户名</text>
      <input
        v-model="form.username"
        class="input"
        placeholder="与远程注册用户一致"
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
      <button class="btn-save" @tap="saveConfig">保存配置</button>
    </view>

    <view v-if="hasRemote" class="actions-card glass-card">
      <text class="section-title">数据同步</text>
      <button class="btn-action" @tap="runBootstrapSync">健康检查并拉取任务</button>
      <button class="btn-action" @tap="syncFrom">仅拉取服务器任务</button>
      <button class="btn-action" @tap="syncTo">上传本地任务到服务器</button>
      <button class="btn-action warning" v-if="pendingCount > 0" @tap="openConflictPage">处理 {{ pendingCount }} 条冲突</button>
      <view v-if="lastSync" class="sync-info">
        <text>最近同步：{{ lastSync.sync_type }} - {{ lastSync.message }}</text>
      </view>
    </view>

    <view class="tip glass-card tip-card">
      <text>业务接口会带 Bearer token；若遇到 401，app 会按用户名和 token 自动调用 /api/users 注册一次后重试。远程与本地内容冲突时，不会直接覆盖，而是进入确认页。</text>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { getRemoteConfig, setRemoteConfig } from '@/api/config.js';
import dataManager from '@/services/dataManager.js';

const form = reactive({
  enabled: false,
  api_base_url: '',
  api_token: '',
  username: '',
});

const hasRemote = ref(false);
const lastSync = ref(null);
const pendingCount = ref(0);

function refreshStatus() {
  hasRemote.value = dataManager.hasRemoteConfig();
  lastSync.value = dataManager.getLastSyncStatus();
  pendingCount.value = dataManager.getPendingRemoteTaskChanges().length;
}

onMounted(() => {
  const cfg = getRemoteConfig();
  form.enabled = !!cfg.enabled;
  form.api_base_url = cfg.api_base_url || '';
  form.api_token = cfg.api_token || '';
  form.username = cfg.username || '';
  refreshStatus();
});

function persistConfig() {
  setRemoteConfig({
    enabled: !!form.enabled,
    api_base_url: (form.api_base_url || '').trim(),
    api_token: (form.api_token || '').trim(),
    username: (form.username || '').trim(),
  });
  refreshStatus();
}

function saveConfig() {
  persistConfig();
  uni.showToast({ title: '已保存', icon: 'success' });
}

function handleEnabledChange(event) {
  form.enabled = !!event.detail.value;
}

function goBack() {
  uni.navigateBack();
}

function openConflictPage() {
  if (pendingCount.value <= 0) return;
  uni.navigateTo({ url: '/pages/remote-conflicts' });
}

function handleSyncResult(res, successTitle) {
  refreshStatus();
  if (res.success) {
    if ((res.pendingChanges || []).length > 0) {
      uni.showToast({ title: `发现 ${res.pendingChanges.length} 条冲突`, icon: 'none' });
      setTimeout(() => openConflictPage(), 200);
      return;
    }
    uni.showToast({ title: successTitle, icon: 'success' });
    return;
  }

  uni.showToast({ title: res.error || '同步失败', icon: 'none' });
}

function runBootstrapSync() {
  persistConfig();
  uni.showLoading({ title: '检查中...' });
  dataManager.bootstrapRemoteSync().then((res) => {
    uni.hideLoading();
    handleSyncResult(res, '同步完成');
  });
}

function syncFrom() {
  persistConfig();
  const local = dataManager.loadTasksFromStorage();
  uni.showLoading({ title: '拉取中...' });
  dataManager.syncFromServer(local).then((res) => {
    uni.hideLoading();
    handleSyncResult(res, '拉取成功');
  });
}

function syncTo() {
  persistConfig();
  const local = dataManager.loadTasksFromStorage();
  uni.showLoading({ title: '上传中...' });
  dataManager.syncToServer(local).then((res) => {
    uni.hideLoading();
    refreshStatus();
    if (res.success) {
      uni.showToast({ title: `已上传 ${res.uploaded || 0} 条`, icon: 'success' });
    } else {
      uni.showToast({ title: res.error || '上传失败', icon: 'none' });
    }
  });
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.settings-page {
  min-height: 100vh;
  padding: 50px 40px 60px;
  background: linear-gradient(180deg, #f0f4ff 0%, #fff 40%);
}

.settings-page.page-with-nav .glass-btn {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.nav-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: block;
}

.glass-card {
  padding: 20px;
  margin-bottom: 16px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
  display: block;
}

.section-subtitle {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.form-card .label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
  margin-top: 12px;
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
  box-shadow: $shadow;
  border: 1px solid $glass-border;
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
  margin-top: 10px;
}

.btn-action.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  border-color: rgba(245, 158, 11, 0.25);
}

.sync-info {
  margin-top: 14px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.tip-card {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.7;
}
</style>
