import sqlite3
import os
from datetime import datetime

class MemoryDB:
    def __init__(self, db_path="memory/jarvis.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Setup SQLite tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Interactions Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,         -- Store JSON string for current window/process
                    embedding BLOB        -- Store vector embedding (to be used later if local vector db needed)
                )
            ''')
            
            # Knowledge/Preferences Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Phase 24: Usage Stats for Habit Tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()

    def add_interaction(self, role, content, context=None, embedding=None):
        """Log a user/ai interaction with optional vector embedding."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interactions (timestamp, role, content, context, embedding) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), role, content, str(context) if context else None, embedding)
            )
            conn.commit()

    def get_recent_history(self, limit=10):
        """Fetch the last N interactions as dicts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, context FROM interactions ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()[::-1]
            return [{"role": row["role"], "content": row["content"], "context": row["context"]} for row in rows]

    def get_all_embeddings(self):
        """Fetch all stored embeddings and their content for vector search."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT role, content, embedding FROM interactions WHERE embedding IS NOT NULL")
            rows = cursor.fetchall()
            return [{"role": row["role"], "content": row["content"], "embedding": row["embedding"]} for row in rows]

    def upsert_knowledge(self, key, value, category='general'):
        """Store or update a learned preference/fact."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO knowledge (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
            ''', (key, value, category, datetime.now().isoformat()))
            conn.commit()
    def log_usage(self, action, target):
        """Track app/url usage for habit prediction."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usage_stats (action, target, timestamp) VALUES (?, ?, ?)",
                (action, target, datetime.now().isoformat())
            )
            conn.commit()

    def get_top_habits(self, limit=5):
        """Find most frequent actions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action, target, COUNT(*) as count 
                FROM usage_stats 
                GROUP BY action, target 
                ORDER BY count DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Single-use migration helper from JSON
if __name__ == "__main__":
    db = MemoryDB()
    print("Memory database initialized.")
