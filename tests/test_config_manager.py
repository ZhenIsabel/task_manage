"""配置加载/合并/损坏恢复 与 任务坐标→紧急/重要契约测试"""

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config import config_manager
from config.config_manager import (
    DEFAULT_CONFIG,
    _merge_defaults,
    load_config,
    save_tasks,
)


class ConfigMergeTests(unittest.TestCase):
    """配置 JSON 深度合并与损坏恢复"""

    def setUp(self):
        fd, self._config_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self._config_path)
        patcher = patch.object(config_manager, "CONFIG_FILE", self._config_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._remove_config_file)

    def _remove_config_file(self):
        if os.path.exists(self._config_path):
            os.remove(self._config_path)

    def _write_config(self, content: str):
        with open(self._config_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_merge_defaults_backfills_missing_nested_keys(self):
        user = {"ui": {"border_radius": 7}}
        merged = _merge_defaults(DEFAULT_CONFIG, user)
        self.assertEqual(merged["ui"]["border_radius"], 7, "用户已有值不得被默认值覆盖")
        self.assertIn("font_family", merged["ui"], "缺失的嵌套键应从默认配置补齐")
        self.assertIn("quadrants", merged)
        self.assertEqual(merged["quadrants"]["q1"]["color"], DEFAULT_CONFIG["quadrants"]["q1"]["color"])

    def test_merge_defaults_does_not_mutate_inputs(self):
        user = {"ui": {"border_radius": 7}}
        _merge_defaults(DEFAULT_CONFIG, user)
        self.assertEqual(user, {"ui": {"border_radius": 7}})

    def test_load_config_missing_file_creates_defaults(self):
        config = load_config()
        self.assertEqual(config, DEFAULT_CONFIG)
        self.assertTrue(os.path.exists(self._config_path), "缺失配置文件时应落盘默认配置")

    def test_load_config_corrupt_json_falls_back_to_defaults(self):
        self._write_config("{not valid json")
        config = load_config()
        self.assertEqual(config, DEFAULT_CONFIG, "损坏的配置文件不应抛错，应回退默认配置")

    def test_load_config_merges_partial_user_config(self):
        self._write_config(json.dumps({
            "size": {"width": 1234},
            "ui": {"border_radius": 3},
        }, ensure_ascii=False))
        config = load_config()
        self.assertEqual(config["size"]["width"], 1234)
        self.assertIn("height", config["size"], "嵌套缺失键应补齐")
        self.assertEqual(config["ui"]["border_radius"], 3)
        # 升级新增的定时任务字段应被按名合并补齐
        names = [f["name"] for f in config["schedule_task_fields"]]
        self.assertIn("due_offset_days", names)


def _fake_task(task_id, x, y):
    data = {
        "id": task_id,
        "position": {"x": x, "y": y},
        "priority": "旧字段",
    }
    task = SimpleNamespace(urgency=None, importance=None)
    task.get_data = lambda d=data: d
    return task, data


class QuadrantPositionContractTests(unittest.TestCase):
    """全局空间契约：右=高紧急，上=高重要（save_tasks 是该契约的持久化入口）"""

    def _run_save(self, tasks):
        db = Mock()
        db.save_task.return_value = True
        parent = Mock()
        parent.width.return_value = 1000
        parent.height.return_value = 800
        with patch.object(config_manager, "get_db_manager", return_value=db):
            self.assertTrue(save_tasks(tasks, parent=parent))
        return db

    def test_four_quadrants_map_to_urgency_importance(self):
        cases = [
            # (x, y) 相对中心 (500, 400)，期望 (urgency, importance)
            ((600, 300), ("高", "高")),  # 右上
            ((400, 300), ("低", "高")),  # 左上
            ((600, 500), ("高", "低")),  # 右下
            ((400, 500), ("低", "低")),  # 左下
        ]
        for (x, y), (urgency, importance) in cases:
            with self.subTest(x=x, y=y):
                task, data = _fake_task("t1", x, y)
                self._run_save([task])
                self.assertEqual(data["urgency"], urgency)
                self.assertEqual(data["importance"], importance)
                self.assertEqual(task.urgency, urgency, "任务对象自身属性也应同步更新")
                self.assertEqual(task.importance, importance)

    def test_center_boundary_counts_as_low(self):
        """正中心：x 不大于中心 → 低紧急；y 不小于中心 → 低重要"""
        task, data = _fake_task("t-center", 500, 400)
        self._run_save([task])
        self.assertEqual(data["urgency"], "低")
        self.assertEqual(data["importance"], "低")

    def test_legacy_priority_field_is_stripped_before_save(self):
        task, data = _fake_task("t-legacy", 600, 300)
        db = self._run_save([task])
        saved = db.save_task.call_args[0][0]
        self.assertNotIn("priority", saved, "旧 priority 字段不得继续写入数据库")


if __name__ == "__main__":
    unittest.main()
