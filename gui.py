
import json
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QHBoxLayout, QLabel, QDialog, QFormLayout, QComboBox
)

from llm_client import LLMClient
from db import ensure_schema

ASSETS = Path(__file__).resolve().parent / "assets"

class StreamWorker(QThread):
    chunk = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client, session_id: str, messages: list, parent=None):
        super().__init__(parent)
        self.client = client
        self.session_id = session_id
        self.messages = messages

    def run(self):
        try:
            full_text = ""
            for piece in self.client.stream_chat(self.messages, session_id=self.session_id):
                full_text += piece
                self.chunk.emit(piece)
            self.done.emit(full_text)
        except Exception as e:
            self.error.emit(str(e))

class SettingsDialog(QDialog):
    def __init__(self, settings_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings and Models and Keys")
        self.settings_path = Path(settings_path)
        with open(self.settings_path) as f:
            self.settings = json.load(f)

        layout = QFormLayout(self)

        self.mode = QComboBox()
        self.mode.addItems(["offline", "openai", "anthropic"])
        self.mode.setCurrentText(self.settings.get("mode", "offline"))

        self.offline_model = QLineEdit(self.settings.get("offline_model", "llama3"))
        self.online_model = QLineEdit(self.settings.get("online_model", "gpt-4o-mini"))
        self.anthropic_model = QLineEdit(self.settings.get("anthropic_model", "claude-3-opus-20240229"))

        self.ollama_url = QLineEdit(self.settings.get("ollama_base_url", "http://localhost:11434"))
        self.openai_key = QLineEdit(self.settings.get("openai_api_key", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key = QLineEdit(self.settings.get("anthropic_api_key", ""))
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.temp = QLineEdit(str(self.settings.get("temperature", 0.7)))
        self.max_tok = QLineEdit(str(self.settings.get("max_tokens", 1024)))
        self.system_prompt = QTextEdit(self.settings.get("system_prompt", "You are a helpful assistant."))

        layout.addRow("Mode", self.mode)
        layout.addRow("Offline model", self.offline_model)
        layout.addRow("OpenAI model", self.online_model)
        layout.addRow("Anthropic model", self.anthropic_model)
        layout.addRow("Ollama URL", self.ollama_url)
        layout.addRow("OpenAI API Key", self.openai_key)
        layout.addRow("Anthropic API Key", self.anthropic_key)
        layout.addRow("Temperature", self.temp)
        layout.addRow("Max tokens", self.max_tok)
        layout.addRow("System Prompt", self.system_prompt)

        btns = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addRow(btns)

        save.clicked.connect(self.save_settings)
        cancel.clicked.connect(self.reject)

    def save_settings(self):
        try:
            self.settings["mode"] = self.mode.currentText()
            self.settings["offline_model"] = self.offline_model.text().strip()
            self.settings["online_model"] = self.online_model.text().strip()
            self.settings["anthropic_model"] = self.anthropic_model.text().strip()
            self.settings["ollama_base_url"] = self.ollama_url.text().strip()
            self.settings["openai_api_key"] = self.openai_key.text().strip()
            self.settings["anthropic_api_key"] = self.anthropic_key.text().strip()
            self.settings["temperature"] = float(self.temp.text().strip())
            self.settings["max_tokens"] = int(self.max_tok.text().strip())
            self.settings["system_prompt"] = self.system_prompt.toPlainText().strip()
            with open(self.settings_path, "w") as f:
                json.dump(self.settings, f, indent=2)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class MainWindow(QMainWindow):
    def __init__(self, db, settings_path: str):
        super().__init__()
        self.db = db
        ensure_schema(self.db.conn)
        self.settings_path = Path(settings_path)
        with open(self.settings_path) as f:
            self.settings = json.load(f)

        self.setWindowTitle("LocalAIApp")
        icon_path = ASSETS / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.session_id = self.db.start_new_session()

        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message...")
        self.send_btn = QPushButton("Send")

        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(self.send_btn)

        v.addWidget(self.chat_view)
        v.addLayout(row)

        self.status_lbl = QLabel("Mode: " + self.settings.get("mode", "offline"))
        v.addWidget(self.status_lbl)

        self.send_btn.clicked.connect(self.on_send)
        self.input.returnPressed.connect(self.on_send)

        menubar = self.menuBar()
        m_app = menubar.addMenu("App")
        m_mode = menubar.addMenu("Mode")
        m_history = menubar.addMenu("History")
        m_export = menubar.addMenu("Export")
        m_settings = menubar.addMenu("Settings")

        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self.close)
        m_app.addAction(quit_act)

        offline_act = QAction("Switch to Offline", self)
        openai_act = QAction("Switch to OpenAI", self)
        anthropic_act = QAction("Switch to Anthropic", self)
        offline_act.triggered.connect(lambda: self.switch_mode("offline"))
        openai_act.triggered.connect(lambda: self.switch_mode("openai"))
        anthropic_act.triggered.connect(lambda: self.switch_mode("anthropic"))
        m_mode.addAction(offline_act)
        m_mode.addAction(openai_act)
        m_mode.addAction(anthropic_act)

        view_hist = QAction("View Session History", self)
        view_hist.triggered.connect(self.view_history)
        m_history.addAction(view_hist)

        export_json = QAction("Export Session as JSON", self)
        export_txt = QAction("Export Session as TXT", self)
        export_json.triggered.connect(lambda: self.export_session("json"))
        export_txt.triggered.connect(lambda: self.export_session("txt"))
        m_export.addAction(export_json)
        m_export.addAction(export_txt)

        settings_act = QAction("Models and API Keys", self)
        settings_act.triggered.connect(self.open_settings)
        m_settings.addAction(settings_act)

        self.client = LLMClient(self.settings, self.db)
        self.load_session_into_view()

    def load_session_into_view(self):
        messages = self.db.get_messages(self.session_id)
        self.chat_view.clear()
        for m in messages:
            self.append_message(m["role"], m["content"])

    def append_message(self, role: str, content: str):
        if role == "user":
            self.chat_view.append(f"<p><b>You:</b> {content}</p>")
        else:
            self.chat_view.append(f"<p><b>Assistant:</b> {content}</p>")

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.db.add_message(self.session_id, "user", text)
        self.append_message("user", text)

        messages = self.db.get_messages(self.session_id, as_openai_format=True)
        self.stream_thread = StreamWorker(self.client, self.session_id, messages)
        self.stream_thread.chunk.connect(self._on_stream_chunk)
        self.stream_thread.done.connect(self._on_stream_done)
        self.stream_thread.error.connect(self._on_stream_error)
        self.stream_thread.start()

    def _on_stream_chunk(self, chunk: str):
        self._ensure_last_assistant_paragraph()
        self._append_to_last_assistant(chunk)

    def _on_stream_done(self, full: str):
        self.db.add_message(self.session_id, "assistant", full)

    def _on_stream_error(self, err: str):
        QMessageBox.critical(self, "Error", err)

    def _ensure_last_assistant_paragraph(self):
        cursor = self.chat_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        html = self.chat_view.toHtml()
        if "Assistant:" not in html[-300:]:
            self.chat_view.append(f"<p><b>Assistant:</b> </p>")

    def _append_to_last_assistant(self, text: str):
        cursor = self.chat_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.chat_view.setTextCursor(cursor)

    def switch_mode(self, mode: str):
        self.settings["mode"] = mode
        with open(self.settings_path, "w") as f:
            json.dump(self.settings, f, indent=2)
        self.status_lbl.setText("Mode: " + mode)
        self.client = LLMClient(self.settings, self.db)

    def open_settings(self):
        dlg = SettingsDialog(str(self.settings_path), self)
        if dlg.exec():
            with open(self.settings_path) as f:
                self.settings = json.load(f)
            self.status_lbl.setText("Mode: " + self.settings.get("mode", "offline"))
            self.client = LLMClient(self.settings, self.db)

    def view_history(self):
        msgs = self.db.get_messages(self.session_id)
        lines = []
        for m in msgs:
            lines.append(f"[{m['created_at']}] {m['role']}: {m['content']}")
        dlg = QDialog(self)
        dlg.setWindowTitle("Session History")
        lay = QVBoxLayout(dlg)
        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText("\n\n".join(lines))
        lay.addWidget(box)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec()

    def export_session(self, kind: str):
        if kind == "json":
            path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "conversation.json", "JSON Files (*.json)")
            if not path:
                return
            data = self.db.get_messages(self.session_id)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Export", "Exported as JSON")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save TXT", "conversation.txt", "Text Files (*.txt)")
            if not path:
                return
            data = self.db.get_messages(self.session_id)
            with open(path, "w") as f:
                for m in data:
                    f.write(f"[{m['created_at']}] {m['role'].upper()}: {m['content']}\n\n")
            QMessageBox.information(self, "Export", "Exported as TXT")
