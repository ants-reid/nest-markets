"""Filesystem loader for versioned JSON schema prompt contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaLoader:
    """Loads JSON schema files from the prompts directory into dictionaries."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize loader with an optional prompts base directory override."""
        self._base_dir = base_dir or Path(__file__).resolve().parent

    def load_schema(self, relative_path: str) -> dict[str, Any]:
        """Load a JSON schema from a relative path under the prompts directory."""
        path = self._base_dir / relative_path
        return json.loads(path.read_text(encoding="utf-8"))
