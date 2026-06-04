/**
 * 远程 API 配置（与 task_manage 项目 database_manager 的 remote_config 对应）
 */
const STORAGE_KEY = 'task_remote_config';

const defaultConfig = {
  enabled: false,
  api_base_url: '',
  api_token: '',
  username: '',
};

function normalizeRemoteConfig(raw) {
  const parsed = raw && typeof raw === 'object' ? raw : {};
  const apiBaseUrl = String(parsed.api_base_url || '').trim();
  const apiToken = String(parsed.api_token || '').trim();
  const username = String(parsed.username || '').trim();
  const enabled = typeof parsed.enabled === 'boolean' ? parsed.enabled : !!apiBaseUrl;

  return {
    ...defaultConfig,
    enabled,
    api_base_url: apiBaseUrl,
    api_token: apiToken,
    username,
  };
}

export function getRemoteConfig() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY);
    if (raw) {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return normalizeRemoteConfig(parsed);
    }
  } catch (e) {
    console.warn('[api/config] getRemoteConfig failed', e);
  }
  return { ...defaultConfig };
}

export function setRemoteConfig(config) {
  try {
    const current = getRemoteConfig();
    const next = normalizeRemoteConfig({ ...current, ...(config || {}) });
    uni.setStorageSync(STORAGE_KEY, JSON.stringify(next));
    return next;
  } catch (e) {
    console.warn('[api/config] setRemoteConfig failed', e);
    return getRemoteConfig();
  }
}

export default { getRemoteConfig, setRemoteConfig };
