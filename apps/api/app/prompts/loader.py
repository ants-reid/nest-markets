"""Filesystem prompt loader for versioned prompt text files."""

from __future__ import annotations

from pathlib import Path


class PromptLoader:
    """Loads versioned prompt files as plain text from the prompts directory."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize loader with an optional prompts base directory override."""
        self._base_dir = base_dir or Path(__file__).resolve().parent

    def load_prompt(self, relative_path: str) -> str:
        """Load prompt text from a relative path under the prompts directory."""
        path = self._base_dir / relative_path
        return path.read_text(encoding="utf-8")
