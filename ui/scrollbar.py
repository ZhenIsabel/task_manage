"""Scroll area compatibility helpers."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QEasingCurve, QEvent, QObject, Qt
from PyQt6.QtWidgets import QApplication, QAbstractScrollArea, QFrame, QScrollArea, QWidget

FLUENT_SCROLL_AVAILABLE = False

try:
    from qfluentwidgets import ScrollBarHandleDisplayMode, SmoothScrollArea, SmoothScrollDelegate  # type: ignore

    FLUENT_SCROLL_AVAILABLE = True
except ImportError:
    ScrollBarHandleDisplayMode = None
    SmoothScrollArea = None
    SmoothScrollDelegate = None


SCROLL_ANIMATION_DURATION = 500
SCROLL_EASING_CURVE = QEasingCurve.Type.OutQuint


class _FluentScrollAreaFallback(QScrollArea):
    """Qt fallback that keeps the same construction API."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        enable_vertical_animation: bool = True,
        enable_horizontal_animation: bool = False,
        animation_duration: int = 500,
        easing_curve: QEasingCurve.Type = QEasingCurve.Type.OutQuint,
        use_hover_handle: bool = False,
        transparent_background: bool = True,
        borderless: bool = True,
    ):
        super().__init__(parent)
        self._apply_common_style(transparent_background=transparent_background, borderless=borderless)

    def _apply_common_style(self, *, transparent_background: bool, borderless: bool) -> None:
        if borderless:
            self.setFrameShape(QFrame.Shape.NoFrame)

        if transparent_background:
            self.setStyleSheet("QScrollArea { background: transparent; border: none; }")


def _apply_scroll_bar_behavior(scroll_bar) -> None:
    """Normalize Fluent scrollbar animation and visibility."""
    if scroll_bar is None:
        return

    if hasattr(scroll_bar, "setScrollAnimation"):
        scroll_bar.setScrollAnimation(SCROLL_ANIMATION_DURATION, SCROLL_EASING_CURVE)


def _apply_hover_handle(scroll_bar, use_hover_handle: bool) -> None:
    if not use_hover_handle or scroll_bar is None or ScrollBarHandleDisplayMode is None:
        return

    if hasattr(scroll_bar, "setHandleDisplayMode"):
        scroll_bar.setHandleDisplayMode(ScrollBarHandleDisplayMode.ON_HOVER)


if FLUENT_SCROLL_AVAILABLE:

    def _is_qfluent_scroll_widget(widget: QAbstractScrollArea) -> bool:
        return widget.__class__.__module__.startswith("qfluentwidgets")


    def _should_install_delegate(widget: QAbstractScrollArea) -> bool:
        if isinstance(widget, SmoothScrollArea):
            return False

        if _is_qfluent_scroll_widget(widget):
            return False

        return getattr(widget, "_fluent_scroll_delegate", None) is None


    def _install_delegate(
        widget: QAbstractScrollArea,
        *,
        use_ani: bool = True,
        use_hover_handle: bool = False,
    ) -> bool:
        if not _should_install_delegate(widget):
            return False

        # SmoothScrollDelegate 构造时会先把原生 scrollbar policy 设为 AlwaysOff，
        # 所以必须在构造前保存原始策略，再回写给 Fluent scrollbar。
        vertical_policy = widget.verticalScrollBarPolicy()
        horizontal_policy = widget.horizontalScrollBarPolicy()
        delegate = SmoothScrollDelegate(widget, useAni=use_ani)
        widget._fluent_scroll_delegate = delegate
        delegate.setVerticalScrollBarPolicy(vertical_policy)
        delegate.setHorizontalScrollBarPolicy(horizontal_policy)
        _apply_scroll_bar_behavior(delegate.vScrollBar)
        _apply_scroll_bar_behavior(delegate.hScrollBar)
        _apply_hover_handle(delegate.vScrollBar, use_hover_handle)
        _apply_hover_handle(delegate.hScrollBar, use_hover_handle)
        return True


    class _GlobalFluentScrollBarManager(QObject):
        """Install Fluent scrollbars on all Qt scroll areas."""

        def __init__(self, app: QApplication, *, use_ani: bool = True, use_hover_handle: bool = False):
            super().__init__(app)
            self.app = app
            self.use_ani = use_ani
            self.use_hover_handle = use_hover_handle

        def install_existing(self) -> None:
            for widget in self.app.allWidgets():
                self._install_for_widget(widget)

        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.Polish, QEvent.Type.Show):
                self._install_for_widget(obj)
            return super().eventFilter(obj, event)

        def _install_for_widget(self, obj) -> None:
            if isinstance(obj, QAbstractScrollArea):
                _install_delegate(obj, use_ani=self.use_ani, use_hover_handle=self.use_hover_handle)
                return

            if not isinstance(obj, QWidget):
                return

            for scroll_widget in obj.findChildren(QAbstractScrollArea):
                _install_delegate(scroll_widget, use_ani=self.use_ani, use_hover_handle=self.use_hover_handle)


    def install_global_fluent_scrollbars(
        app: Optional[QApplication],
        *,
        use_ani: bool = True,
        use_hover_handle: bool = False,
    ) -> bool:
        """Install Fluent scrollbars for all Qt scroll areas in the app."""
        if not FLUENT_SCROLL_AVAILABLE or app is None:
            return False

        manager = getattr(app, "_fluent_scroll_bar_manager", None)
        if manager is None:
            manager = _GlobalFluentScrollBarManager(
                app,
                use_ani=use_ani,
                use_hover_handle=use_hover_handle,
            )
            app._fluent_scroll_bar_manager = manager
            app.installEventFilter(manager)

        manager.install_existing()
        return True

else:

    def install_global_fluent_scrollbars(
        app: Optional[QApplication],
        *,
        use_ani: bool = True,
        use_hover_handle: bool = False,
    ) -> bool:
        return False


if FLUENT_SCROLL_AVAILABLE:

    class FluentScrollArea(SmoothScrollArea):
        """Unified scroll area that prefers qfluentwidgets when available."""

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            *,
            enable_vertical_animation: bool = True,
            enable_horizontal_animation: bool = False,
            animation_duration: int = 500,
            easing_curve: QEasingCurve.Type = QEasingCurve.Type.OutQuint,
            use_hover_handle: bool = False,
            transparent_background: bool = True,
            borderless: bool = True,
        ):
            super().__init__(parent)
            self._apply_common_style(transparent_background=transparent_background, borderless=borderless)

            if enable_vertical_animation:
                self.setScrollAnimation(Qt.Orientation.Vertical, animation_duration, easing_curve)
                _apply_scroll_bar_behavior(self.verticalScrollBar())

            if enable_horizontal_animation:
                self.setScrollAnimation(Qt.Orientation.Horizontal, animation_duration, easing_curve)
                _apply_scroll_bar_behavior(self.horizontalScrollBar())

            if use_hover_handle:
                self._enable_hover_handle()

        def _apply_common_style(self, *, transparent_background: bool, borderless: bool) -> None:
            if borderless:
                self.setFrameShape(QFrame.Shape.NoFrame)

            if transparent_background:
                self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        def _enable_hover_handle(self) -> None:
            delegate = getattr(self, "delegate", None)
            if delegate is None:
                return

            v_scroll_bar = getattr(delegate, "vScrollBar", None)
            if v_scroll_bar is None or ScrollBarHandleDisplayMode is None:
                return

            v_scroll_bar.setHandleDisplayMode(ScrollBarHandleDisplayMode.ON_HOVER)

else:

    class FluentScrollArea(_FluentScrollAreaFallback):
        """Fallback scroll area with the same API when Fluent is unavailable."""


__all__ = ["FLUENT_SCROLL_AVAILABLE", "FluentScrollArea", "install_global_fluent_scrollbars"]
