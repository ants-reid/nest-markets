"""Backend-backed paper execution journal persistence for MVP."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID


def _utc_now_iso() -> str:
    """Return a UTC ISO timestamp string with timezone information."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExecutionJournalRecord:
    """Typed execution journal record used by the API layer."""

    execution_id: str
    outcome_tag: str
    note: str
    tags: list[str]
    updated_at: str


class ExecutionJournalService:
    """Persist execution journals in a shared JSON store for MVP backend use."""

    _lock = Lock()

    def __init__(self, store_path: Path | None = None) -> None:
        """Initialize the service with an explicit or default store path."""
        self._store_path = store_path or Path(__file__).resolve().parents[1] / "data" / "execution_journals.json"

    def get_journal(self, execution_id: UUID) -> ExecutionJournalRecord | None:
        """Return one journal record by execution id if it exists."""
        store = self._read_store()
        payload = store.get(str(execution_id))
        if payload is None:
            return None
        return self._build_record(str(execution_id), payload)

    def upsert_journal(self, execution_id: UUID, *, outcome_tag: str, note: str, tags: list[str]) -> ExecutionJournalRecord:
        """Create or update one journal record by execution id."""
        normalized_tags = self._normalize_tags(tags)
        record = ExecutionJournalRecord(
            execution_id=str(execution_id),
            outcome_tag=outcome_tag,
            note=note.strip(),
            tags=normalized_tags,
            updated_at=_utc_now_iso(),
        )

        with self._lock:
            store = self._read_store()
            store[str(execution_id)] = asdict(record)
            self._write_store(store)

        return record

    def _build_record(self, execution_id: str, payload: dict[str, object]) -> ExecutionJournalRecord:
        """Hydrate a typed record from raw JSON payload data."""
        tags = payload.get("tags")
        return ExecutionJournalRecord(
            execution_id=execution_id,
            outcome_tag=str(payload.get("outcome_tag", "untagged")),
            note=str(payload.get("note", "")).strip(),
            tags=self._normalize_tags(tags if isinstance(tags, list) else []),
            updated_at=str(payload.get("updated_at", _utc_now_iso())),
        )

    def _normalize_tags(self, tags: list[object]) -> list[str]:
        """Return unique, lowercase tags in stable order."""
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_tag in tags:
            cleaned = str(raw_tag).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return normalized[:6]

    def _read_store(self) -> dict[str, dict[str, object]]:
        """Read the JSON store into a plain dictionary."""
        if not self._store_path.exists():
            return {}

        try:
            raw = self._store_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(parsed, dict):
            return {}

        return {str(key): value for key, value in parsed.items() if isinstance(value, dict)}

    def _write_store(self, store: dict[str, dict[str, object]]) -> None:
        """Persist the in-memory store back to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")