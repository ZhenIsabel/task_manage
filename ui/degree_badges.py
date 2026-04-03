from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget


DEGREE_BADGE_CONFIG = {
    "urgency": {
        "title": "紧急程度",
        "low_text": "不紧急",
        "high_text": "很紧急",
        "cool": {
            "bg_color": "#E0F2FE",
            "border_color": "#7DD3FC",
            "text_color": "#0C4A6E",
        },
        "warm": {
            "bg_color": "#FFEDD5",
            "border_color": "#FDBA74",
            "text_color": "#9A3412",
        },
    },
    "importance": {
        "title": "重要程度",
        "low_text": "不重要",
        "high_text": "很重要",
        "cool": {
            "bg_color": "#DBEAFE",
            "border_color": "#93C5FD",
            "text_color": "#1E3A8A",
        },
        "warm": {
            "bg_color": "#FEE2E2",
            "border_color": "#FCA5A5",
            "text_color": "#991B1B",
        },
    },
}

STATUS_BADGE_CONFIG = {
    False: {
        "display_text": "未完成",
        "bg_color": "#F6E7D8",
        "border_color": "#D8B89A",
        "text_color": "#8A6748",
    },
    True: {
        "display_text": "已完成",
        "bg_color": "#E4F0E8",
        "border_color": "#AFC8B4",
        "text_color": "#587561",
    },
}


def is_degree_field(field_name):
    return field_name in DEGREE_BADGE_CONFIG


def get_degree_badge_meta(field_name, value):
    config = DEGREE_BADGE_CONFIG.get(field_name, {})
    normalized_value = str(value or "").strip()
    title = config.get("title", field_name)

    if normalized_value == "高":
        temperature = "warm"
        display_text = config.get("high_text", normalized_value or "-")
    else:
        temperature = "cool"
        display_text = config.get("low_text", normalized_value or "-")

    palette = config.get(temperature, {})
    return {
        "field": field_name,
        "title": title,
        "raw_value": normalized_value or "低",
        "display_text": display_text,
        "temperature": temperature,
        "bg_color": palette.get("bg_color", "#F3F4F6"),
        "border_color": palette.get("border_color", "#D1D5DB"),
        "text_color": palette.get("text_color", "#374151"),
    }


def build_degree_badge_stylesheet(meta):
    return (
        "QLabel {"
        f"background-color: {meta['bg_color']};"
        f"color: {meta['text_color']};"
        f"border: 1px solid {meta['border_color']};"
        "border-radius: 10px;"
        "padding: 3px 10px;"
        "font-family: '微软雅黑';"
        "font-size: 12px;"
        "font-weight: 600;"
        "}"
    )


def create_degree_badge_label(field_name, value, parent=None):
    meta = get_degree_badge_meta(field_name, value)
    label = QLabel(meta["display_text"], parent)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(build_degree_badge_stylesheet(meta))
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return label


def create_degree_display_widget(field_name, value, title=None, parent=None, centered=False):
    container = QWidget(parent)
    container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    badge_label = create_degree_badge_label(field_name, value, container)

    if centered:
        layout.addStretch()
    layout.addWidget(badge_label)
    if centered:
        layout.addStretch()
    else:
        layout.addStretch()

    return container


def create_degree_table_cell(field_name, value, parent=None):
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(0)
    layout.addStretch()
    layout.addWidget(create_degree_badge_label(field_name, value, container))
    layout.addStretch()
    return container


def get_status_badge_meta(completed):
    config = STATUS_BADGE_CONFIG[bool(completed)]
    return {
        "field": "status",
        "title": "状态",
        "raw_value": bool(completed),
        "display_text": config["display_text"],
        "bg_color": config["bg_color"],
        "border_color": config["border_color"],
        "text_color": config["text_color"],
    }
