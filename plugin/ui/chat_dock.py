from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from UM.Extension import Extension

class ChatDock(Extension, QDockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant Aurora (3D/5D)")
        
        container = QWidget()
        layout = QVBoxLayout()
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Опишите задачу (например: Кронштейн под нагрузку, PETG, без поддержек)...")
        
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.handle_send)
        
        layout.addWidget(self.chat_history)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_btn)
        
        container.setLayout(layout)
        self.setWidget(container)

    def handle_send(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.chat_history.append(f"<b>Пользователь:</b> {text}")
        self.input_field.clear()
        self.chat_history.append("<b>Агент Aurora:</b> Подбираю параметры печати и режим 5D...")
