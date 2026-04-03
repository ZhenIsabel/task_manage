"""UI package exports for convenience imports."""

from .adaptive_table import AdaptiveTextTableWidget, compute_multiline_item_size_hint
from .scrollbar import FLUENT_SCROLL_AVAILABLE, FluentScrollArea, install_global_fluent_scrollbars
from .ui import UIManager, MyColorDialog, WarningPopup
from .styles import StyleManager

__all__ = [
    "AdaptiveTextTableWidget",
    "FLUENT_SCROLL_AVAILABLE",
    "FluentScrollArea",
    "compute_multiline_item_size_hint",
    "install_global_fluent_scrollbars",
    "UIManager",
    "MyColorDialog",
    "WarningPopup",
    "StyleManager",
]


