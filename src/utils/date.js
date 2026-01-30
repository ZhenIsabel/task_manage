/**
 * 日期工具：统一格式与判断，供各页面复用
 */

/**
 * 判断是否为今天
 * @param {string|Date} dateString - ISO 或可解析的日期
 * @returns {boolean}
 */
export function isToday(dateString) {
  if (!dateString) return false;
  const date = new Date(dateString);
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
}

/**
 * 格式化为 YYYY-MM-DD（展示用）
 * @param {string|Date} dateString
 * @returns {string}
 */
export function formatDate(dateString) {
  if (!dateString) return '';
  const d = new Date(dateString);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * 短格式 M/D（归档等场景）
 * @param {string|Date} dateString
 * @returns {string}
 */
export function formatDateShort(dateString) {
  if (!dateString) return '';
  const d = new Date(dateString);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

/**
 * 供 picker mode="date" 使用的 value（YYYY-MM-DD）
 * @param {string} isoString - ISO 日期字符串
 * @returns {string}
 */
export function formatDateForPicker(isoString) {
  if (!isoString) return '';
  return isoString.split('T')[0];
}
