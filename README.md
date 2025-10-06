
# LocalAIChatApp

Local desktop chat app for macOS using a local LLM with Ollama and optional online models through OpenAI and Anthropic.  
Runs offline by default. Switch providers in the Mode menu or the Settings dialog.

## Features
- PyQt6 desktop GUI
- Offline mode through Ollama at http://localhost:11434
- Online mode through OpenAI or Anthropic
- Streaming responses for smooth chat
- Unlimited chat history in SQLite
- Export conversations to JSON or TXT
- Settings in JSON for models and keys
- Logs folder placeholder

## Requirements
- Python 3.10 or newer
- Ollama installed and running for offline mode
- OpenAI API key and/or Anthropic API key for online modes

## Quick Start

1. Install dependencies (already done on Replit):
```bash
pip install PyQt6 requests openai anthropic
```

2. For offline mode, ensure Ollama is running locally and has a model pulled.

3. Run the app:
```bash
python main.py
```

4. Switch modes and set keys using the Settings menu.

## API Keys

You can set your API keys in two ways:
- Through the Settings menu in the app
- As environment variables: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`

## Project Structure

```
/LocalAIChatApp
├── main.py           # Entry point
├── gui.py            # PyQt6 interface
├── llm_client.py     # LLM provider integration
├── db.py             # SQLite chat history
├── settings.json     # Configuration
├── chat_history.db   # SQLite database
├── assets/           # Icons and images
├── logs/             # Log files
└── README.md
```

## GitHub Sync

This project is configured for auto-sync with GitHub. Click the Run button to sync changes.
