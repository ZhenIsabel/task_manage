function getSearchKeywords(searchText) {
  return String(searchText || '')
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
}

export function filterArchivedTasks(tasks, searchText = '') {
  const keywords = getSearchKeywords(searchText);

  return (tasks || []).filter((task) => {
    if (task.deleted || !task.isCompleted) return false;
    if (keywords.length === 0) return true;

    const title = String(task.title || '').toLowerCase();
    return keywords.every((keyword) => title.includes(keyword));
  });
}
