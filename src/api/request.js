/**
 * 封装 uni.request，统一带 Authorization: Bearer <token>
 * 与 database_manager._make_api_request 行为一致
 */
import { getRemoteConfig } from './config.js';

const DEFAULT_TIMEOUT = 30000;

/**
 * 发起 API 请求
 * @param {string} method - GET | POST | PUT | DELETE
 * @param {string} endpoint - 例如 '/api/tasks'
 * @param {object} [data] - 请求体（POST/PUT）
 * @returns {Promise<{ success: boolean, data?: any, error?: string, statusCode?: number }>}
 */
export function request(method, endpoint, data = null) {
  const { api_base_url, api_token } = getRemoteConfig();

  if (!api_base_url) {
    return Promise.resolve({
      success: false,
      error: '未配置服务器地址',
      statusCode: 0,
    });
  }

  const url = `${api_base_url.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;
  const header = {
    'Content-Type': 'application/json',
    Authorization: api_token ? `Bearer ${api_token}` : '',
  };

  return new Promise((resolve) => {
    uni.request({
      url,
      method,
      data: data || undefined,
      header,
      timeout: DEFAULT_TIMEOUT,
      success: (res) => {
        const statusCode = res.statusCode || 0;
        if (statusCode === 200) {
          resolve({
            success: true,
            data: res.data,
            statusCode,
          });
        } else {
          const errMsg =
            (res.data && (res.data.error || res.data.message)) ||
            res.errMsg ||
            `HTTP ${statusCode}`;
          resolve({
            success: false,
            error: errMsg,
            statusCode,
            data: res.data,
          });
        }
      },
      fail: (err) => {
        resolve({
          success: false,
          error: err.errMsg || '网络请求失败',
          statusCode: 0,
        });
      },
    });
  });
}

export default request;
