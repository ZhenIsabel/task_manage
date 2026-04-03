from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition


DEFAULT_SUCCESS_DURATION_MS = 1000
DEFAULT_ERROR_DURATION_MS = -1
DEFAULT_WARNING_DURATION_MS = 3000

def resolve_notification_host(widget: Optional[QWidget]) -> Optional[QWidget]:
    """Resolve the top-level host widget so InfoBar appears on the main window."""
    host = widget or QApplication.activeWindow()
    while host is not None and host.parentWidget() is not None:
        host = host.parentWidget()
    return host


def _show_info_bar(factory, fallback, widget: Optional[QWidget], title: str, content: str, *, position, duration: int):
    host = resolve_notification_host(widget)
    if host is None:
        fallback(None, title, content)
        return None

    return factory(
        title=title,
        content=content,
        orient=Qt.Orientation.Horizontal,
        isClosable=True,
        position=position,
        duration=duration,
        parent=host,
    )


def show_success(
    widget: Optional[QWidget],
    title: str,
    content: str,
    *,
    position=InfoBarPosition.TOP,
    duration: int = DEFAULT_SUCCESS_DURATION_MS,
):
    return _show_info_bar(
        InfoBar.success,
        QMessageBox.information,
        widget,
        title,
        content,
        position=position,
        duration=duration,
    )


def show_error(
    widget: Optional[QWidget],
    title: str,
    content: str,
    *,
    position=InfoBarPosition.TOP,
    duration: int = DEFAULT_ERROR_DURATION_MS,
):
    return _show_info_bar(
        InfoBar.error,
        QMessageBox.critical,
        widget,
        title,
        content,
        position=position,
        duration=duration,
    )


def show_warning(
    widget: Optional[QWidget],
    title: str,
    content: str,
    *,
    position=InfoBarPosition.TOP,
    duration: int = DEFAULT_WARNING_DURATION_MS,
):
    return _show_info_bar(
        InfoBar.warning,
        QMessageBox.critical,
        widget,
        title,
        content,
        position=position,
        duration=duration,
    )