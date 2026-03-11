// 模拟远程配置接口，测试时通过全局状态控制是否启用远程同步。
export function getRemoteConfig() {
  const state = globalThis.__SYNC_TEST_STATE__ || {};
  return state.remoteConfig || { api_base_url: '' };
}
