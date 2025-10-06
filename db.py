
import sqlite3
import uuid
import datetime

def utc_now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()

class Database:
    def __init__(self, path: str = "chat_history.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        ensure_schema(self.conn)

    def start_new_session(self) -> str:
        session_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, utc_now_iso())
        )
        self.conn.commit()
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, utc_now_iso())
        )
        self.conn.commit()

    def get_messages(self, session_id: str, as_openai_format: bool = False):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        )
        rows = cur.fetchall()
        if as_openai_format:
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        return [dict(r) for r in rows]
