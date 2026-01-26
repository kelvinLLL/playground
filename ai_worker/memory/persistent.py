"""
Persistent memory using SQLite.

Stores long-term information like user preferences, important facts,
and conversation summaries.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class MemoryRecord:
    """A persistent memory record."""

    id: Optional[int]
    user_id: str
    key: str
    value: Any
    memory_type: str  # 'preference', 'fact', 'summary'
    created_at: float
    updated_at: float
    metadata: dict[str, Any]


class MemoryStore:
    """
    SQLite-based persistent memory store.

    Provides key-value storage with metadata and search capabilities.
    """

    def __init__(self, db_path: str = "ai_worker_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'fact',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(user_id, key)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            """)
            conn.commit()

    def set(
        self,
        user_id: str,
        key: str,
        value: Any,
        memory_type: str = "fact",
        metadata: Optional[dict] = None,
    ) -> None:
        """Store or update a memory."""
        now = time.time()
        value_json = json.dumps(value) if not isinstance(value, str) else value
        metadata_json = json.dumps(metadata or {})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memories (user_id, key, value, memory_type, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET
                    value = excluded.value,
                    memory_type = excluded.memory_type,
                    updated_at = excluded.updated_at,
                    metadata = excluded.metadata
            """, (user_id, key, value_json, memory_type, now, now, metadata_json))
            conn.commit()

    def get(self, user_id: str, key: str) -> Optional[Any]:
        """Retrieve a memory value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM memories WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return None

    def get_record(self, user_id: str, key: str) -> Optional[MemoryRecord]:
        """Retrieve a full memory record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT id, user_id, key, value, memory_type, created_at, updated_at, metadata
                   FROM memories WHERE user_id = ? AND key = ?""",
                (user_id, key)
            )
            row = cursor.fetchone()
            if row:
                try:
                    value = json.loads(row[3])
                except json.JSONDecodeError:
                    value = row[3]
                try:
                    metadata = json.loads(row[7])
                except json.JSONDecodeError:
                    metadata = {}

                return MemoryRecord(
                    id=row[0],
                    user_id=row[1],
                    key=row[2],
                    value=value,
                    memory_type=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    metadata=metadata,
                )
            return None

    def delete(self, user_id: str, key: str) -> bool:
        """Delete a memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_keys(self, user_id: str, memory_type: Optional[str] = None) -> list[str]:
        """List all keys for a user."""
        with sqlite3.connect(self.db_path) as conn:
            if memory_type:
                cursor = conn.execute(
                    "SELECT key FROM memories WHERE user_id = ? AND memory_type = ?",
                    (user_id, memory_type)
                )
            else:
                cursor = conn.execute(
                    "SELECT key FROM memories WHERE user_id = ?",
                    (user_id,)
                )
            return [row[0] for row in cursor.fetchall()]

    def get_all(
        self, user_id: str, memory_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Get all memories for a user as a dict."""
        with sqlite3.connect(self.db_path) as conn:
            if memory_type:
                cursor = conn.execute(
                    "SELECT key, value FROM memories WHERE user_id = ? AND memory_type = ?",
                    (user_id, memory_type)
                )
            else:
                cursor = conn.execute(
                    "SELECT key, value FROM memories WHERE user_id = ?",
                    (user_id,)
                )
            result = {}
            for row in cursor.fetchall():
                try:
                    result[row[0]] = json.loads(row[1])
                except json.JSONDecodeError:
                    result[row[0]] = row[1]
            return result

    def search(self, user_id: str, query: str) -> list[MemoryRecord]:
        """Search memories by key or value content."""
        pattern = f"%{query}%"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT id, user_id, key, value, memory_type, created_at, updated_at, metadata
                   FROM memories
                   WHERE user_id = ? AND (key LIKE ? OR value LIKE ?)
                   ORDER BY updated_at DESC""",
                (user_id, pattern, pattern)
            )
            records = []
            for row in cursor.fetchall():
                try:
                    value = json.loads(row[3])
                except json.JSONDecodeError:
                    value = row[3]
                try:
                    metadata = json.loads(row[7])
                except json.JSONDecodeError:
                    metadata = {}

                records.append(MemoryRecord(
                    id=row[0],
                    user_id=row[1],
                    key=row[2],
                    value=value,
                    memory_type=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    metadata=metadata,
                ))
            return records

    def clear_user(self, user_id: str) -> int:
        """Clear all memories for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount


class PersistentMemory:
    """
    High-level interface for persistent memory.

    Provides typed access patterns for common use cases:
    - User preferences
    - Important facts
    - Conversation summaries
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

    def set_preference(self, user_id: str, name: str, value: Any) -> None:
        """Store a user preference."""
        self.store.set(user_id, f"pref:{name}", value, memory_type="preference")

    def get_preference(self, user_id: str, name: str, default: Any = None) -> Any:
        """Get a user preference."""
        value = self.store.get(user_id, f"pref:{name}")
        return value if value is not None else default

    def get_all_preferences(self, user_id: str) -> dict[str, Any]:
        """Get all preferences for a user."""
        all_prefs = self.store.get_all(user_id, memory_type="preference")
        return {k.replace("pref:", ""): v for k, v in all_prefs.items()}

    def remember_fact(self, user_id: str, key: str, fact: str) -> None:
        """Store an important fact about the user."""
        self.store.set(user_id, f"fact:{key}", fact, memory_type="fact")

    def recall_fact(self, user_id: str, key: str) -> Optional[str]:
        """Recall a stored fact."""
        return self.store.get(user_id, f"fact:{key}")

    def get_all_facts(self, user_id: str) -> dict[str, str]:
        """Get all facts for a user."""
        all_facts = self.store.get_all(user_id, memory_type="fact")
        return {k.replace("fact:", ""): v for k, v in all_facts.items()}

    def store_summary(self, user_id: str, date: str, summary: str) -> None:
        """Store a conversation summary."""
        self.store.set(
            user_id,
            f"summary:{date}",
            summary,
            memory_type="summary"
        )

    def get_recent_summaries(self, user_id: str, limit: int = 5) -> list[str]:
        """Get recent conversation summaries."""
        all_summaries = self.store.get_all(user_id, memory_type="summary")
        sorted_keys = sorted(all_summaries.keys(), reverse=True)[:limit]
        return [all_summaries[k] for k in sorted_keys]

    def get_context_for_llm(self, user_id: str) -> str:
        """Get formatted context string for LLM prompts."""
        lines = []

        # Preferences
        prefs = self.get_all_preferences(user_id)
        if prefs:
            lines.append("User Preferences:")
            for k, v in prefs.items():
                lines.append(f"  - {k}: {v}")

        # Facts
        facts = self.get_all_facts(user_id)
        if facts:
            lines.append("\nKnown Facts:")
            for k, v in list(facts.items())[:10]:  # Limit to 10 facts
                lines.append(f"  - {k}: {v}")

        return "\n".join(lines) if lines else ""

    def forget(self, user_id: str, key: str) -> bool:
        """Forget a specific memory."""
        deleted_pref = self.store.delete(user_id, f"pref:{key}")
        deleted_fact = self.store.delete(user_id, f"fact:{key}")
        return deleted_pref or deleted_fact

    def forget_all(self, user_id: str) -> int:
        """Forget everything about a user."""
        return self.store.clear_user(user_id)
