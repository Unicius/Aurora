import os
import traceback
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QTextEdit, QPushButton, QLabel,
    QFileDialog, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

try:
    from UM.Extension import Extension
    from UM.Application import Application
    UM_AVAILABLE = True
except ImportError:
    # Running standalone (test_standalone.py)
    class Extension:
        def __init__(self): pass
        def addMenuItem(self, name, fn): pass
        def setMenuName(self, name): pass
        def getPluginId(self): return "AuroraAI"

    UM_AVAILABLE = False

from .components.message_widget import MessageWidget, ToolCallBadge
from ..core.agent import Agent
from ..utils.file_utils import is_stl_file, is_image_file, save_uploaded_file


# ─── Worker thread ─────────────────────────────────────────────────────────────

class AgentWorker(QObject):
    finished   = pyqtSignal(str)
    tool_start = pyqtSignal(str, dict)
    error      = pyqtSignal(str)

    def __init__(self, user_text: str, files: List[str]):
        super().__init__()
        self._text  = user_text
        self._files = files

    def run(self):
        try:
            agent = Agent()
            result = agent.run(
                self._text,
                attached_files=self._files,
                on_tool_call=lambda name, args: self.tool_start.emit(name, args),
            )
            self.finished.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


# ─── Chat window ───────────────────────────────────────────────────────────────

class ChatWindow(QWidget):
    """Floating chat window — the visible UI panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🤖 Aurora — AI Print Assistant")
        self.resize(500, 680)
        self.setMinimumSize(380, 480)

        self._attached_files: List[str] = []
        self._thread: Optional[QThread] = None
        self._worker: Optional[AgentWorker] = None

        self._build_ui()

    # ─── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("QWidget { background-color: #121212; }")
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header ──
        header = QLabel("🤖 Aurora — AI Print Assistant")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(
            "background:#1a1a2e; color:#90cdf4; font-size:14px;"
            "font-weight:bold; padding:8px; border-bottom:1px solid #333;"
        )
        root_layout.addWidget(header)

        # ── Scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:#121212;}")

        self._msgs_container = QWidget()
        self._msgs_container.setStyleSheet("background:#121212;")
        self._msgs_layout = QVBoxLayout(self._msgs_container)
        self._msgs_layout.setAlignment(Qt.AlignTop)
        self._msgs_layout.setSpacing(4)
        self._msgs_layout.setContentsMargins(4, 8, 4, 8)
        self._scroll.setWidget(self._msgs_container)
        root_layout.addWidget(self._scroll, stretch=1)

        # ── Status label ──
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#888;font-size:11px;padding:2px 8px;")
        self._status_lbl.setVisible(False)
        root_layout.addWidget(self._status_lbl)

        # ── Attached files row ──
        self._files_row = QWidget()
        self._files_row.setStyleSheet("background:#1a1a2e;")
        self._files_layout = QHBoxLayout(self._files_row)
        self._files_layout.setContentsMargins(4, 2, 4, 2)
        self._files_layout.setSpacing(4)
        self._files_layout.addStretch()
        self._files_row.setVisible(False)
        root_layout.addWidget(self._files_row)

        # ── Input area ──
        input_frame = QFrame()
        input_frame.setStyleSheet(
            "QFrame{background:#1e1e2e;border-top:1px solid #333;}"
        )
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 6, 6, 6)
        input_layout.setSpacing(4)

        self._input = QTextEdit()
        self._input.setPlaceholderText(
            "Опишите задачу… (например: Кронштейн под нагрузку 50 кг, PETG, без поддержек)"
        )
        self._input.setMaximumHeight(90)
        self._input.setStyleSheet(
            "QTextEdit{background:#2d2d3d;color:#e0e0e0;"
            "border:1px solid #444;border-radius:6px;padding:6px;font-size:13px;}"
        )
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._attach_btn = QPushButton("📎 Файл")
        self._attach_btn.setFixedHeight(32)
        self._attach_btn.setCursor(Qt.PointingHandCursor)
        self._attach_btn.setStyleSheet(self._btn_style("#2d3748", "#90cdf4"))
        self._attach_btn.clicked.connect(self._on_attach)

        self._clear_btn = QPushButton("🗑️ Очистить")
        self._clear_btn.setFixedHeight(32)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(self._btn_style("#3d2d2d", "#fc8181"))
        self._clear_btn.clicked.connect(self._on_clear)

        self._send_btn = QPushButton("▶ Отправить")
        self._send_btn.setFixedHeight(32)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setStyleSheet(self._btn_style("#1a4a2e", "#68d391"))
        self._send_btn.clicked.connect(self._on_send)

        btn_row.addWidget(self._attach_btn)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._send_btn)
        input_layout.addLayout(btn_row)
        root_layout.addWidget(input_frame)

        # Welcome message
        self._add_agent_message(
            "👋 Привет! Я Aurora — ИИ-ассистент для настройки 3D/5D-печати.\n\n"
            "Опишите вашу задачу и при необходимости прикрепите STL-файл или фото детали. "
            "Я автоматически подберу все параметры, режим печати и запущу слайсинг."
        )

    # ─── Event filter (Enter to send) ────────────────────────────────────────

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return and
                    not (event.modifiers() & Qt.ShiftModifier)):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    # ─── Slots ────────────────────────────────────────────────────────────────

    def _on_attach(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Прикрепить файлы",
            "",
            "3D Models & Images (*.stl *.STL *.png *.jpg *.jpeg *.bmp *.webp);;All files (*)",
        )
        for path in paths:
            if path and (is_stl_file(path) or is_image_file(path)):
                saved = save_uploaded_file(path)
                self._attached_files.append(saved)
                icon = "📐" if is_stl_file(path) else "🖼️"
                badge = QLabel(f"{icon} {os.path.basename(path)}")
                badge.setStyleSheet(
                    "background:#2d3748;color:#90cdf4;border-radius:4px;"
                    "padding:2px 6px;font-size:11px;"
                )
                count = self._files_layout.count()
                self._files_layout.insertWidget(count - 1, badge)

        if self._attached_files:
            self._files_row.setVisible(True)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text or self._thread is not None:
            return

        self._input.clear()
        self._add_user_message(text, self._attached_files[:])

        files = self._attached_files[:]
        self._attached_files.clear()
        while self._files_layout.count() > 1:
            item = self._files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._files_row.setVisible(False)

        self._set_input_enabled(False)
        self._status_lbl.setText("⏳ Агент Aurora думает…")
        self._status_lbl.setVisible(True)

        self._thread = QThread()
        self._worker = AgentWorker(text, files)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_agent_done)
        self._worker.error.connect(self._on_agent_error)
        self._worker.tool_start.connect(self._on_tool_start)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def _on_clear(self):
        while self._msgs_layout.count():
            item = self._msgs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._attached_files.clear()
        while self._files_layout.count() > 1:
            item = self._files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._files_row.setVisible(False)
        self._status_lbl.setVisible(False)

    def _on_tool_start(self, tool_name: str, args: dict):
        badge = ToolCallBadge(tool_name)
        self._msgs_layout.addWidget(badge)
        self._scroll_to_bottom()
        self._status_lbl.setText(f"⚙️ Выполняется: {tool_name}…")

    def _on_agent_done(self, text: str):
        self._add_agent_message(text)
        self._status_lbl.setVisible(False)

    def _on_agent_error(self, error_text: str):
        short = error_text.strip().split("\n")[-1]
        self._add_error_message(f"Ошибка агента:\n{short}")
        self._status_lbl.setVisible(False)

    def _on_thread_finished(self):
        self._thread = None
        self._worker = None
        self._set_input_enabled(True)

    # ─── Message helpers ──────────────────────────────────────────────────────

    def _add_user_message(self, text: str, files: List[str]):
        msg_text = text
        if files:
            msg_text += "\n📎 " + " | ".join(os.path.basename(f) for f in files)
        self._msgs_layout.addWidget(MessageWidget(msg_text, role="user"))
        self._scroll_to_bottom()

    def _add_agent_message(self, text: str):
        self._msgs_layout.addWidget(MessageWidget(text, role="agent"))
        self._scroll_to_bottom()

    def _add_error_message(self, text: str):
        self._msgs_layout.addWidget(MessageWidget(text, role="error"))
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(
            50,
            lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            ),
        )

    def _set_input_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._attach_btn.setEnabled(enabled)

    @staticmethod
    def _btn_style(bg: str, fg: str) -> str:
        return (
            f"QPushButton{{background-color:{bg};color:{fg};"
            f"border:1px solid {fg}44;border-radius:5px;"
            f"padding:4px 12px;font-size:12px;}}"
            f"QPushButton:hover{{background-color:{fg}22;border-color:{fg};}}"
            f"QPushButton:disabled{{color:#555;border-color:#333;}}"
        )


# ─── Plugin entry point ────────────────────────────────────────────────────────

class ChatDock(QObject, Extension):
    """
    STE Slicer plugin entry point.
    Registered as "extension" in __init__.py → register().
    Adds a menu item under Extensions → Aurora.
    """

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._window: Optional[ChatWindow] = None

        self.setMenuName("Aurora AI Assistant")
        self.addMenuItem("Открыть чат", self._show_window)

        # Auto-open once the engine is ready (only inside STE Slicer)
        if UM_AVAILABLE:
            try:
                Application.getInstance().engineCreatedSignal.connect(
                    self._show_window
                )
            except Exception:
                pass

    def _show_window(self):
        if self._window is None:
            self._window = ChatWindow()
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
