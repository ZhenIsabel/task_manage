/**
 * 封装 uni.request，统一处理鉴权、自动注册与重试逻辑。
 */
import { getRemoteConfig } from './config.js';

const DEFAULT_TIMEOUT = 30000;
const PUBLIC_ENDPOINTS = new Set(['/api/health', '/api/users']);

let remoteUserRegistrationAttempted = false;
let remoteAuthPaused = false;

function normalizeEndpoint(endpoint) {
  return `/${String(endpoint || '').replace(/^\/+/, '')}`;
}

function isPublicEndpoint(endpoint) {
  return PUBLIC_ENDPOINTS.has(normalizeEndpoint(endpoint));
}

function buildHeaders(endpoint, config) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (!isPublicEndpoint(endpoint) && config.api_token) {
    headers.Authorization = `Bearer ${config.api_token}`;
  }

  return headers;
}

function isRemoteEnabled(config) {
  return !!(config && config.enabled && config.api_base_url);
}

function doRequest(method, endpoint, data, config) {
  if (!isRemoteEnabled(config)) {
    return Promise.resolve({
      success: false,
      error: '未配置服务器地址',
      statusCode: 0,
    });
  }

  const url = `${config.api_base_url.replace(/\/$/, '')}/${String(endpoint || '').replace(/^\//, '')}`;
  const header = buildHeaders(endpoint, config);

  return new Promise((resolve) => {
    uni.request({
      url,
      method,
      data: data || undefined,
      header,
      timeout: DEFAULT_TIMEOUT,
      success: (res) => {
        const statusCode = res.statusCode || 0;
        const responseData = res.data;

        if (statusCode === 200 || statusCode === 201) {
          resolve({
            success: true,
            data: responseData,
            statusCode,
          });
          return;
        }

        if (statusCode === 204) {
          resolve({
            success: true,
            data: {},
            statusCode,
          });
          return;
        }

        const errMsg =
          (responseData && (responseData.error || responseData.message)) ||
          res.errMsg ||
          `HTTP ${statusCode}`;

        resolve({
          success: false,
          error: errMsg,
          statusCode,
          data: responseData,
        });
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

async function registerRemoteUser(config) {
  if (remoteUserRegistrationAttempted) {
    return false;
  }

  remoteUserRegistrationAttempted = true;
  if (!config.api_base_url || !config.username || !config.api_token) {
    remoteAuthPaused = true;
    return false;
  }

  const result = await doRequest('POST', '/api/users', {
    username: config.username,
    api_token: config.api_token,
  }, config);

  if (result.success || result.statusCode === 409) {
    remoteAuthPaused = false;
    return true;
  }

  remoteAuthPaused = true;
  return false;
}

export function resetRemoteAuthState() {
  remoteUserRegistrationAttempted = false;
  remoteAuthPaused = false;
}

export async function request(method, endpoint, data = null, options = {}) {
  const config = getRemoteConfig();
  const retryOnAuthFailure = options.retryOnAuthFailure !== false;

  if (!isRemoteEnabled(config)) {
    return {
      success: false,
      error: '未配置服务器地址',
      statusCode: 0,
    };
  }

  if (remoteAuthPaused && !isPublicEndpoint(endpoint)) {
    return {
      success: false,
      error: '远程鉴权已暂停，请检查远程配置',
      statusCode: 401,
    };
  }

  const result = await doRequest(method, endpoint, data, config);
  if (result.success) {
    return result;
  }

  if (result.statusCode === 401 && retryOnAuthFailure && !isPublicEndpoint(endpoint)) {
    const registered = await registerRemoteUser(config);
    if (registered) {
      return request(method, endpoint, data, { ...options, retryOnAuthFailure: false });
    }
  }

  return result;
}

export default request;
