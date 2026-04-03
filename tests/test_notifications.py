import os
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import InfoBarPosition

from ui.notifications import (
    DEFAULT_SUCCESS_DURATION_MS,
    resolve_notification_host,
    show_error,
    show_success,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class NotificationHelpersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_resolve_notification_host_returns_top_level_parent(self):
        main_window = QWidget()
        container = QWidget(main_window)
        child = QWidget(container)
        self.addCleanup(child.deleteLater)
        self.addCleanup(container.deleteLater)
        self.addCleanup(main_window.deleteLater)

        self.assertIs(resolve_notification_host(child), main_window)

    def test_show_success_binds_infobar_to_top_level_parent(self):
        main_window = QWidget()
        dialog = QWidget(main_window)
        child = QWidget(dialog)
        self.addCleanup(child.deleteLater)
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(main_window.deleteLater)

        with patch("ui.notifications.InfoBar.success") as success_mock:
            show_success(child, "成功", "操作完成")

        success_mock.assert_called_once_with(
            title="成功",
            content="操作完成",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=DEFAULT_SUCCESS_DURATION_MS,
            parent=main_window,
        )

    def test_show_error_falls_back_to_message_box_when_no_host_exists(self):
        with patch("ui.notifications.InfoBar.error") as error_mock, patch(
            "ui.notifications.QMessageBox.critical"
        ) as critical_mock, patch(
            "ui.notifications.QApplication.activeWindow", return_value=None
        ):
            show_error(None, "失败", "没有可用窗口")

        error_mock.assert_not_called()
        critical_mock.assert_called_once_with(None, "失败", "没有可用窗口")


if __name__ == "__main__":
    unittest.main()
