import json
import os
import sqlite3
from datetime import datetime, timedelta

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

            # Phase 30+: Lightweight telemetry for background observer
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    target TEXT NOT NULL,
                    meta TEXT
                )
            ''')

            # Phase 30+: Learned patterns for auto-suggestions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT UNIQUE NOT NULL,
                    label TEXT,
                    count INTEGER DEFAULT 1,
                    last_seen TEXT NOT NULL,
                    last_suggested TEXT,
                    embedding BLOB
                )
            ''')

            # Phase 30+: Scheduler for triggered/recurring tasks
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    command TEXT NOT NULL,
                    run_at TEXT NOT NULL,
                    recur_seconds INTEGER DEFAULT 0,
                    auto_execute INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    last_run TEXT,
                    source TEXT DEFAULT 'user',
                    metadata TEXT
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

    # ─── Observations & Patterns ─────────────────────────────

    def log_observation(self, kind: str, target: str, meta: dict | None = None) -> None:
        """Persist lightweight telemetry from the background observer."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO observations (timestamp, kind, target, meta) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), kind, target, json.dumps(meta or {})),
            )
            conn.commit()

    def record_pattern(self, sequence: list[str], label: str | None = None, embedding: bytes | None = None) -> dict:
        """
        Upsert a pattern occurrence.
        Returns the updated row (count, label, last_seen).
        """
        pattern_key = json.dumps(sequence)
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO patterns (pattern, label, count, last_seen, embedding)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(pattern) DO UPDATE SET
                    count = patterns.count + 1,
                    label = COALESCE(?, patterns.label),
                    last_seen = excluded.last_seen
                ''',
                (pattern_key, label, now, embedding, label),
            )
            cursor.execute("SELECT pattern, label, count, last_seen, last_suggested FROM patterns WHERE pattern = ?", (pattern_key,))
            row = cursor.fetchone()
            return dict(row) if row else {}

    def mark_pattern_suggested(self, sequence: list[str]) -> None:
        pattern_key = json.dumps(sequence)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE patterns SET last_suggested = ? WHERE pattern = ?",
                (datetime.now().isoformat(), pattern_key),
            )
            conn.commit()

    def get_top_patterns(self, min_count: int = 2, limit: int = 5) -> list[dict]:
        """Return frequent patterns for reporting/suggestions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT pattern, label, count, last_seen, last_suggested
                FROM patterns
                WHERE count >= ?
                ORDER BY count DESC, last_seen DESC
                LIMIT ?
                ''',
                (min_count, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ─── Scheduler ───────────────────────────────────────────

    def add_scheduled_task(self, label: str, command: str, run_at: datetime, recur_seconds: int = 0,
                           auto_execute: bool = False, source: str = "user", metadata: dict | None = None) -> int:
        """Insert a scheduled or recurring task; returns task ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO scheduled_tasks (label, command, run_at, recur_seconds, auto_execute, status, source, metadata)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ''',
                (label, command, run_at.isoformat(), recur_seconds, 1 if auto_execute else 0, source, json.dumps(metadata or {})),
            )
            conn.commit()
            return cursor.lastrowid

    def due_tasks(self, now: datetime | None = None) -> list[dict]:
        """Return pending or recurring tasks that should run at the provided time."""
        ts = now or datetime.now()
        due: list[dict] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scheduled_tasks WHERE status IN ('pending', 'recurring')"
            )
            rows = cursor.fetchall()
            for row in rows:
                run_at = datetime.fromisoformat(row["run_at"])
                recur = row["recur_seconds"] or 0
                last_run = datetime.fromisoformat(row["last_run"]) if row["last_run"] else None

                next_run = run_at
                if recur and last_run:
                    next_run = last_run + timedelta(seconds=recur)

                if next_run <= ts:
                    rec = dict(row)
                    rec["next_run"] = next_run
                    rec["auto_execute"] = bool(rec.get("auto_execute"))
                    rec["recur_seconds"] = recur
                    due.append(rec)
        return due

    def mark_task_run(self, task_id: int, status: str = "completed") -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE scheduled_tasks
                SET last_run = ?, status = ?
                WHERE id = ?
                ''',
                (datetime.now().isoformat(), status, task_id),
            )
            conn.commit()

# Single-use migration helper from JSON
if __name__ == "__main__":
    db = MemoryDB()
    print("Memory database initialized.")
