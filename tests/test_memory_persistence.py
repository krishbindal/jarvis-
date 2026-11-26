"""Interaction rows should be durable, ordered and bounded before embeddings."""
import sqlite3
from contextlib import closing
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from memory.database import MemoryDB
from memory import memory_store as store


class MemoryDurabilityTests(unittest.TestCase):
    def test_save_with_busy_embedding_workers_keeps_both_messages(self):
        with tempfile.TemporaryDirectory() as folder:
            db = MemoryDB(str(Path(folder) / "memory.sqlite"))
            with patch.object(store, "_DB", db), patch.object(store, "_EMBEDDING_SLOTS") as slots:
                slots.acquire.return_value = False
                store.save_interaction("please open notepad", [], {"message": "I could not open it."})
                history = store.get_recent_history(5)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["user_input"], "please open notepad")
            self.assertEqual(history[0]["result"]["output"], "I could not open it.")
            with closing(sqlite3.connect(db.db_path)) as conn:
                rows = conn.execute("SELECT role, content FROM interactions ORDER BY id").fetchall()
            self.assertEqual(rows, [
                ("user", "please open notepad"),
                ("assistant", "I could not open it."),
            ])

    def test_embedding_updates_do_not_create_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            db = MemoryDB(str(Path(folder) / "memory.sqlite"))
            id1 = db.add_interaction("user", "hello")
            db.update_interaction_embedding(id1, b"0123")
            with closing(sqlite3.connect(db.db_path)) as conn:
                data = conn.execute("SELECT id, embedding FROM interactions").fetchall()
            self.assertEqual(data, [(id1, b"0123")])

    def test_history_pairs_user_and_assistant_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            db = MemoryDB(str(Path(folder) / "memory.sqlite"))
            for role, content in [
                ("user", "task one"), ("assistant", "result one"),
                ("user", "task two"), ("assistant", "result two"),
            ]:
                db.add_interaction(role, content)
            with patch.object(store, "_DB", db):
                turns = store.get_recent_history(2)
            self.assertEqual(len(turns), 2)
            self.assertEqual(turns[0]["user_input"], "task one")
            self.assertEqual(turns[0]["result"]["output"], "result one")
            self.assertEqual(turns[1]["user_input"], "task two")
            self.assertEqual(turns[1]["result"]["output"], "result two")


if __name__ == "__main__":
    unittest.main()
