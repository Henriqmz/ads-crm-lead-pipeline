from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class LeadStorage:
    """SQLite store for idempotent lead processing and delivery auditing."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_leads (
                    lead_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    form_id TEXT NOT NULL,
                    crm_deal_id TEXT,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
                """
            )

    def already_processed(self, lead_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_leads WHERE lead_id = ?",
                (lead_id,),
            ).fetchone()
            return row is not None

    def mark_processed(
        self,
        lead_id: str,
        account_id: str,
        form_id: str,
        crm_deal_id: str | None,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_leads
                (lead_id, account_id, form_id, crm_deal_id, status, payload_json, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    account_id,
                    form_id,
                    crm_deal_id,
                    status,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM processed_leads").fetchone()
            return int(row[0]) if row else 0

    def list_processed(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM processed_leads ORDER BY processed_at DESC").fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                item = dict(r)
                try:
                    item["payload"] = json.loads(item.pop("payload_json", "{}"))
                except Exception:
                    item["payload"] = {}
                out.append(item)
            return out
