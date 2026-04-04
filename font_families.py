"""Centralized font family definitions for the project."""

APP_FONT_FAMILY = "Microsoft YaHei UI"
APP_FONT_FAMILY_QSS = f"'{APP_FONT_FAMILY}'"

APP_FONT_STACK = [
    "Microsoft YaHei",
    "PingFang SC",
    APP_FONT_FAMILY,
    "sans-serif",
]
APP_FONT_STACK_QSS = ", ".join(
    f"'{font}'" if font != "sans-serif" else font for font in APP_FONT_STACK
)

WEB_UI_FONT_STACK = [
    "system-ui",
    "-apple-system",
    "Segoe UI",
    "Roboto",
    "Helvetica Neue",
    "Arial",
    "sans-serif",
]
WEB_UI_FONT_STACK_CSS = ", ".join(
    f'"{font}"' if " " in font else font for font in WEB_UI_FONT_STACK[:-1]
) + f", {WEB_UI_FONT_STACK[-1]}"
