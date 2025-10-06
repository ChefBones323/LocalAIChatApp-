
import sys
from pathlib import Path
import json
from PyQt6.QtWidgets import QApplication
from gui import MainWindow
from db import Database

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"
LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

DEFAULT_SETTINGS = {
    "mode": "offline",
    "offline_model": "llama3",
    "online_model": "gpt-4o-mini",
    "anthropic_model": "claude-3-opus-20240229",
    "ollama_base_url": "http://localhost:11434",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "temperature": 0.7,
    "system_prompt": "You are a helpful assistant.",
    "max_tokens": 1024
}

def ensure_settings():
    if not SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)

def main():
    ensure_settings()
    db = Database()
    app = QApplication(sys.argv)
    app.setApplicationName("LocalAIApp")
    window = MainWindow(db, str(SETTINGS_PATH))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
