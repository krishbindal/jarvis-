"""
JARVIS-X Phase 26: Knowledge Indexer
A background daemon that scans documents and source files to build a local vector knowledge base.
"""

import os
import time
import threading
import hashlib
from typing import List, Optional, Set
from pathlib import Path
from utils.logger import get_logger
from memory.memory_store import get_embedding, _LOCK, _DB
import struct

logger = get_logger(__name__)

class KnowledgeIndexer:
    """Crawl and index local documents for RAG."""

    def __init__(self, interval_min: int = 60):
        self._interval = interval_min * 60
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._indexed_hashes: Set[str] = set()
        
        # Whitelist of folders to index
        home = str(Path.home())
        self._targets = [
            os.path.join(home, "Documents"),
            os.path.join(home, "Desktop"),
            os.getcwd() # Current project folder
        ]
        # Supported extensions
        self._extensions = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json"}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._indexer_loop, daemon=True, name="KnowledgeIndexer")
        self._thread.start()
        logger.info("[OMNISCIENT] Knowledge Indexer activated.")

    def stop(self) -> None:
        self._running = False

    def _get_file_hash(self, path: str) -> str:
        """MD5 hash of file content to detect changes."""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _chunk_text(self, text: str, size: int = 500) -> List[str]:
        """Simple chunking by character count (can be improved)."""
        return [text[i:i+size] for i in range(0, len(text), size)]

    def _index_file(self, path: str) -> None:
        """Read, chunk, embed, and store file content."""
        file_hash = self._get_file_hash(path)
        if not file_hash or file_hash in self._indexed_hashes:
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                return

            filename = os.path.basename(path)
            chunks = self._chunk_text(content)
            
            logger.info(f"[OMNISCIENT] Indexing {filename} ({len(chunks)} chunks)...")
            
            for i, chunk in enumerate(chunks):
                vec = get_embedding(chunk)
                if vec:
                    blob = struct.pack(f'{len(vec)}f', *vec)
                    context = {"source": path, "chunk_index": i, "filename": filename}
                    with _LOCK:
                        # Use a unique role for local knowledge
                        _DB.add_interaction("knowledge_source", chunk, context=context, embedding=blob)
            
            self._indexed_hashes.add(file_hash)
        except Exception as e:
            logger.error(f"[OMNISCIENT] Failed to index {path}: {e}")

    def _indexer_loop(self) -> None:
        """Periodic indexing loop."""
        while self._running:
            try:
                for target in self._targets:
                    if not os.path.exists(target):
                        continue
                    
                    for root, _, files in os.walk(target):
                        if ".git" in root or "__pycache__" in root or "node_modules" in root:
                            continue
                        
                        for file in files:
                            ext = os.path.splitext(file)[1].lower()
                            if ext in self._extensions:
                                file_path = os.path.join(root, file)
                                self._index_file(file_path)
                                # Throttle to prevent high CPU / disk IO
                                time.sleep(0.5) 
                                if not self._running: break
                        if not self._running: break
                    if not self._running: break
                
                logger.info("[OMNISCIENT] Knowledge indexing pass complete.")
            except Exception as e:
                logger.error(f"[OMNISCIENT] Indexer loop error: {e}")

            # Sleep for the interval
            for _ in range(self._interval):
                if not self._running: break
                time.sleep(1)
