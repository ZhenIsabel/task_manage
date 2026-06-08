const DISPLAY_FIELDS = new Set(['text', 'notes', 'due_date', 'urgency', 'importance']);

const FIELD_DISPLAY = {
  text: '任务内容',
  notes: '备注',
  due_date: '截止日期',
  urgency: '紧急程度',
  importance: '重要程度',
};

const HIGH_HISTORY_VALUES = new Set(['高', 'high', 'HIGH', 'High', '1', 1, true, 'true']);
const LOW_HISTORY_VALUES = new Set(['低', 'low', 'LOW', 'Low', '0', 0, false, 'false']);

function formatDateValue(value) {
  if (!value) return '';
  if (value instanceof Date) {
    const time = value.getTime();
    return Number.isNaN(time) ? '' : value.toISOString().split('T')[0];
  }

  const raw = String(value).trim();
  if (!raw) return '';
  return raw.split('T')[0].split(' ')[0] || raw;
}

function formatFieldValue(field, value) {
  const normalized = value == null ? '' : String(value);
  if (!normalized) return '';

  if (field === 'due_date') return formatDateValue(value);

  if (field === 'urgency') {
    if (HIGH_HISTORY_VALUES.has(value) || HIGH_HISTORY_VALUES.has(normalized)) return '紧急';
    if (LOW_HISTORY_VALUES.has(value) || LOW_HISTORY_VALUES.has(normalized)) return '不急';
  }

  if (field === 'importance') {
    if (HIGH_HISTORY_VALUES.has(value) || HIGH_HISTORY_VALUES.has(normalized)) return '重要';
    if (LOW_HISTORY_VALUES.has(value) || LOW_HISTORY_VALUES.has(normalized)) return '一般';
  }

  return normalized;
}

function buildDisplayRecordKey(fieldName, record) {
  return JSON.stringify([
    fieldName,
    formatFieldValue(fieldName, record?.value),
    record?.action || 'update',
    record?.timestamp || '',
  ]);
}

export function mergeDisplayHistory(localHistory, serverHistory) {
  const byField = {};
  const seen = new Set();

  const append = (history) => {
    Object.entries(history || {}).forEach(([fieldName, list]) => {
      if (!DISPLAY_FIELDS.has(fieldName) || !Array.isArray(list)) return;

      list.forEach((record) => {
        const normalized = {
          value: record?.value ?? '',
          timestamp: record?.timestamp || '',
          action: record?.action || 'update',
        };
        const key = buildDisplayRecordKey(fieldName, normalized);
        if (seen.has(key)) return;

        seen.add(key);
        if (!byField[fieldName]) byField[fieldName] = [];
        byField[fieldName].push(normalized);
      });
    });
  };

  append(localHistory);
  append(serverHistory);

  Object.values(byField).forEach((list) => {
    list.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  });

  return byField;
}

export function buildHistoryTimeline(byField) {
  const merged = [];

  Object.entries(byField || {}).forEach(([fieldName, list]) => {
    (list || []).forEach((record) => {
      merged.push({
        field: fieldName,
        timestamp: record.timestamp || '',
        action: record.action || 'update',
        value: record.value,
      });
    });
  });

  merged.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));

  const lastValueByField = {};
  const byTimestamp = {};

  merged.forEach((record) => {
    const newVal = formatFieldValue(record.field, record.value);
    const hasPreviousValue = Object.prototype.hasOwnProperty.call(lastValueByField, record.field);
    const oldVal = hasPreviousValue ? lastValueByField[record.field] : '';
    lastValueByField[record.field] = newVal;

    if (hasPreviousValue && oldVal === newVal) return;

    const timestamp = record.timestamp || '';
    if (!byTimestamp[timestamp]) {
      byTimestamp[timestamp] = { timestamp, actions: [], details: [] };
    }
    byTimestamp[timestamp].actions.push(record.action);
    byTimestamp[timestamp].details.push({
      field: FIELD_DISPLAY[record.field],
      oldVal,
      newVal,
    });
  });

  return Object.values(byTimestamp)
    .filter((item) => item.details.length > 0)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .map((item, index) => {
      const hasCreate = item.actions.some((action) => action === 'create');
      return {
        id: `h-${index}-${item.timestamp}`,
        type: hasCreate ? 'create' : 'update',
        timestamp: item.timestamp,
        summary: hasCreate ? '创建了任务' : '修改了任务详情',
        expanded: false,
        details: item.details,
      };
    });
}
