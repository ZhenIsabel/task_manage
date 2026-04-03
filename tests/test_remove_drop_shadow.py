import unittest
from pathlib import Path


class DropShadowRemovalTests(unittest.TestCase):
    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding="utf-8")

    def test_apply_drop_shadow_should_be_removed_from_public_api(self):
        exports = self._read("ui/__init__.py")
        self.assertNotIn("apply_drop_shadow", exports)

    def test_ui_module_should_not_depend_on_drop_shadow_effect(self):
        ui_module = self._read("ui/ui.py")
        self.assertNotIn("QGraphicsDropShadowEffect", ui_module)
        self.assertNotIn("def apply_drop_shadow(", ui_module)

    def test_core_modules_should_not_reference_apply_drop_shadow(self):
        for rel_path in [
            "core/add_task_dialog.py",
            "core/export_summary_dialog.py",
            "core/history_viewer.py",
            "core/quadrant_widget.py",
            "core/scheduler.py",
            "core/task_label.py",
            "core/complete_table.py",
        ]:
            with self.subTest(rel_path=rel_path):
                self.assertNotIn("apply_drop_shadow", self._read(rel_path))


if __name__ == "__main__":
    unittest.main()
