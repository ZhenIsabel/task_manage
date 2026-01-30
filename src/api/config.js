/**
 * 远程 API 配置（与 task_manage 项目 database_manager 的 remote_config 对应）
 * 可在运行时修改，或从本地存储/环境变量读取
 */
const STORAGE_KEY = 'task_remote_config';

const defaultConfig = {
  api_base_url: '', // 例如: 'http://localhost:5000'
  api_token: '',
};

/**
 * 获取远程配置
 * @returns {{ api_base_url: string, api_token: string }}
 */
export function getRemoteConfig() {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY);
    if (raw) {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return { ...defaultConfig, ...parsed };
    }
  } catch (e) {
    console.warn('[api/config] getRemoteConfig failed', e);
  }
  return { ...defaultConfig };
}

/**
 * 保存远程配置
 * @param {{ api_base_url?: string, api_token?: string }} config
 */
export function setRemoteConfig(config) {
  try {
    const current = getRemoteConfig();
    const next = { ...current, ...config };
    uni.setStorageSync(STORAGE_KEY, JSON.stringify(next));
    return next;
  } catch (e) {
    console.warn('[api/config] setRemoteConfig failed', e);
    return getRemoteConfig();
  }
}

export default { getRemoteConfig, setRemoteConfig };
