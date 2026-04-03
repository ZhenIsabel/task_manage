"""Fluent Widgets compatibility helpers.

This module centralizes qfluentwidgets imports so the rest of the codebase can
gradually migrate without hard-coding fallback behavior in each dialog.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QDate, QEasingCurve, QPoint,Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QWidget,
)

_CALENDAR_WARNING_PATCHED = False
_CALENDAR_POPUP_SHELL_PATCHED = False
_CALENDAR_POPUP_ANIMATION_PATCHED = False

try:
    from qfluentwidgets import (  # type: ignore
        Action,
        CalendarPicker,
        ComboBox,
        DatePicker,
        Dialog,
        LineEdit,
        MessageBox,
        PrimaryPushButton,
        PushButton,
        RoundMenu,
        TableWidget,
        TextEdit,
        Theme,
        setTheme,
        setThemeColor,
    )

except ImportError:
    Action = QAction
    
    class CalendarPicker(QDateEdit):
        """Fallback calendar picker with the Fluent-compatible API we use."""

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self.setCalendarPopup(True)
            

        def getDate(self) -> QDate:
            return self.date()

        def setDateFormat(self, format: str) -> None:
            self.setDisplayFormat(format)

    ComboBox = QComboBox
    Dialog = QDialog
    LineEdit = QLineEdit
    MessageBox = None
    PrimaryPushButton = QPushButton
    PushButton = QPushButton
    RoundMenu = QMenu
    TableWidget = QTableWidget
    TextEdit = QTextEdit
    Theme = None
    setTheme = None
    setThemeColor = None

    class DatePicker(CalendarPicker):
        """Fallback date picker with the same basic API used by dialogs."""

        def __init__(self, parent: Optional[QWidget] = None, format=0, isMonthTight=True):
            super().__init__(parent)



def _patch_calendar_disconnect_warning() -> None:
    """Avoid Qt warnings from qfluentwidgets calendar animation cleanup."""
    global _CALENDAR_WARNING_PATCHED


    try:
        from qfluentwidgets.components.date_time.calendar_view import ScrollViewBase  # type: ignore
    except ImportError:
        _CALENDAR_WARNING_PATCHED = True
        return

    def _safe_on_first_scroll_finished(self):
        self.vScrollBar.setScrollAnimation(300, QEasingCurve.Type.OutQuad)
        try:
            self.vScrollBar.ani.finished.disconnect(self._onFirstScrollFinished)
        except (TypeError, RuntimeError):
            pass

    ScrollViewBase._onFirstScrollFinished = _safe_on_first_scroll_finished
    _CALENDAR_WARNING_PATCHED = True


def _patch_calendar_popup_shell() -> None:
    """Remove the extra outer shell around CalendarPicker popups."""
    global _CALENDAR_POPUP_SHELL_PATCHED

    try:
        from qfluentwidgets.components.date_time.calendar_view import CalendarView  # type: ignore
    except ImportError:
        _CALENDAR_POPUP_SHELL_PATCHED = True
        return

    original_init_widget = CalendarView._CalendarView__initWidget

    def _shellless_init_widget(self):
        original_init_widget(self)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget.setGraphicsEffect(None)

    CalendarView._CalendarView__initWidget = _shellless_init_widget
    _CALENDAR_POPUP_SHELL_PATCHED = True


def _patch_calendar_popup_animation() -> None:
    """Disable CalendarPicker popup animations for instant opening."""
    global _CALENDAR_POPUP_ANIMATION_PATCHED

    try:
        from qfluentwidgets.components.date_time.calendar_view import CalendarView  # type: ignore
        from qfluentwidgets.common.screen import getCurrentScreenGeometry  # type: ignore
    except ImportError:
        _CALENDAR_POPUP_ANIMATION_PATCHED = True
        return

    def _instant_exec(self, pos: QPoint, ani=True):
        if self.isVisible():
            return

        rect = getCurrentScreenGeometry()
        w, h = self.sizeHint().width() + 5, self.sizeHint().height()
        pos.setX(max(rect.left(), min(pos.x(), rect.right() - w)))
        pos.setY(max(rect.top(), min(pos.y() - 4, rect.bottom() - h + 5)))
        self.move(pos)

        self.opacityAni.stop()
        self.slideAni.stop()
        self.aniGroup.stop()
        self.opacityAni.setDuration(0)
        self.slideAni.setDuration(0)
        self.setWindowOpacity(1)
        self.show()

    CalendarView.exec = _instant_exec
    _CALENDAR_POPUP_ANIMATION_PATCHED = True


def create_calendar_picker(
    parent: Optional[QWidget] = None,
    date: Optional[QDate] = None,
    date_format: str = "yyyy-MM-dd",
) -> QWidget:
    """Create a date picker with a consistent API across Fluent and Qt fallback."""
    _patch_calendar_disconnect_warning()
    _patch_calendar_popup_shell()
    _patch_calendar_popup_animation()
    picker = CalendarPicker(parent)
    picker.setDateFormat(date_format)
    if date is not None:
        set_date_on_picker(picker, date)
    return picker


def set_date_on_picker(picker: QWidget, date: QDate) -> None:
    """Normalize date assignment across Fluent and Qt fallback widgets."""
    if hasattr(picker, "setDate"):
        picker.setDate(date)


def is_date_picker(picker: QWidget) -> bool:
    """Detect whether the widget follows the date picker API we use."""
    return isinstance(picker, QDateEdit) or hasattr(picker, "getDate")


def get_date_from_picker(picker: QWidget) -> QDate:
    """Normalize date reads across Fluent and Qt fallback widgets."""
    if hasattr(picker, "getDate"):
        return picker.getDate()
    return picker.date()


def get_date_string_from_picker(picker: QWidget, date_format: str = "yyyy-MM-dd") -> str:
    """Read a normalized date string from any supported picker widget."""
    return get_date_from_picker(picker).toString(date_format)
