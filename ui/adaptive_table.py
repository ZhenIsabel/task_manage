from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem
from qfluentwidgets import TableWidget


def compute_multiline_item_size_hint(font_metrics: QFontMetrics, text: str, width: int) -> QSize:
    """根据给定宽度计算多行单元格需要的尺寸。"""
    available_width = max(width - 16, 1)
    text_rect = font_metrics.boundingRect(
        0,
        0,
        available_width,
        10000,
        int(Qt.TextFlag.TextWordWrap),
        text,
    )
    return QSize(width, text_rect.height() + 16)


class AdaptiveTextTableWidget(TableWidget):
    """支持固定列宽和多行文本自适应行高的通用表格。"""

    def __init__(
        self,
        headers,
        rows,
        fixed_width_columns=None,
        multiline_columns=None,
        parent=None,
    ):
        super().__init__(parent)
        self._headers = list(headers)
        self._rows = list(rows)
        self._fixed_width_columns = dict(fixed_width_columns or {})
        self._multiline_columns = set(multiline_columns or set())

        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setColumnCount(len(self._headers))
        self.setHorizontalHeaderLabels(self._headers)
        self.setRowCount(len(self._rows))
        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideNone)
        self.horizontalHeader().setStretchLastSection(False)

        for column in range(self.columnCount()):
            if column in self._fixed_width_columns:
                self.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.setColumnWidth(column, self._fixed_width_columns[column])
            else:
                self.horizontalHeader().setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )

        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setSortingEnabled(True)
        self.set_rows(self._rows)

    def set_rows(self, rows):
        self._rows = list(rows)
        sorting_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.clearSpans()
        self.clearContents()
        self.setRowCount(len(self._rows))

        for row_index, row_values in enumerate(self._rows):
            for column_index, value in enumerate(row_values):
                item_text = "" if value is None else str(value)
                item = QTableWidgetItem(item_text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column_index in self._multiline_columns:
                    width = self._fixed_width_columns.get(column_index, self.columnWidth(column_index))
                    item.setSizeHint(
                        compute_multiline_item_size_hint(self.fontMetrics(), item_text, width)
                    )
                self.setItem(row_index, column_index, item)

        self.resizeRowsToContents()
        self.setSortingEnabled(sorting_enabled)
