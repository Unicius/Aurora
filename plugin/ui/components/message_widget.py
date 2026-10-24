"""
Chat message widgets — PyQt5 version.

MessageWidget  — a single chat bubble (user | agent | error)
ToolCallBadge  — inline status pill shown while the agent executes a tool
"""

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt


# ─── Tool label mapping ───────────────────────────────────────────────────────
_TOOL_LABELS = {
    "analyze_geometry":     "🔍 Анализ геометрии STL…",
    "analyze_stress":       "🌡️ FEA анализ напряжений…",
    "set_print_mode":       "⚙️ Переключение режима печати…",
    "set_print_setting":    "🔧 Настройка параметра…",
    "apply_full_profile":   "📋 Применение профиля печати…",
    "load_and_orient_model":"📦 Загрузка и ориентация модели…",
    "apply_adaptive_infill":"🎯 Адаптивное заполнение…",
    "start_slicing":        "▶️ Запуск слайсинга…",
    "get_scene_info":       "📊 Получение состояния сцены…",
}

_COLORS = {
    "user":    ("#1A73E8", "#FFFFFF"),
    "agent":   ("#2D2D2D", "#E0E0E0"),
    "error":   ("#8B0000", "#FFD0D0"),
}


class MessageWidget(QFrame):
    """A styled chat bubble."""

    def __init__(self, text: str, role: str = "agent", parent=None):
        super().__init__(parent)
        self.setObjectName("MessageWidget")

        bg, fg = _COLORS.get(role, _COLORS["agent"])
        self.setStyleSheet(f"""
            QFrame#MessageWidget {{
                background-color: {bg};
                border-radius: 10px;
                padding: 6px;
                margin: 2px 4px;
            }}
            QLabel {{
                color: {fg};
                font-size: 13px;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        if role == "user":
            lbl_header = QLabel("<b>👤 Вы</b>")
            lbl_header.setStyleSheet(f"color: {fg}; font-size: 11px;")
            layout.addWidget(lbl_header)
        elif role == "error":
            lbl_header = QLabel("<b>⚠️ Ошибка</b>")
            lbl_header.setStyleSheet(f"color: {fg}; font-size: 11px;")
            layout.addWidget(lbl_header)

        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        lbl_text.setOpenExternalLinks(True)
        layout.addWidget(lbl_text)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)


class ToolCallBadge(QFrame):
    """Small inline pill shown while the agent is calling a tool."""

    def __init__(self, tool_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolCallBadge")
        self.setStyleSheet("""
            QFrame#ToolCallBadge {
                background-color: #1B4332;
                border-radius: 6px;
                margin: 1px 4px;
            }
            QLabel { color: #B7E4C7; font-size: 11px; background: transparent; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        label_text = _TOOL_LABELS.get(tool_name, f"🔧 {tool_name}…")
        layout.addWidget(QLabel(label_text))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
