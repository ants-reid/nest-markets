"""Prompt version seeding service.

Reads prompt files from the prompts/ directory tree and upserts a
``PromptVersion`` row for each file, keyed on (role, version) so that
re-running the seed is idempotent.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import PromptRole
from app.db.models.prompt_version import PromptVersion

_PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"

# Regex to extract a version tag like "v1", "v2" from filenames
_VERSION_RE = re.compile(r"_(v\d+)", re.IGNORECASE)

# Map filename prefixes to PromptRole enum values
_ROLE_MAP: dict[str, PromptRole] = {
    "signal_engine": PromptRole.SIGNAL_ENGINE,
    "catalyst_classifier": PromptRole.CATALYST_CLASSIFIER,
    "trade_reviewer": PromptRole.TRADE_REVIEWER,
    "signal_input_template": PromptRole.SIGNAL_ENGINE,  # user template → signal engine role
}


def _infer_role(filename: str) -> PromptRole | None:
    """Return the PromptRole for a filename, or None if unrecognised."""
    stem = Path(filename).stem.lower()
    for prefix, role in _ROLE_MAP.items():
        if stem.startswith(prefix):
            return role
    return None


def _infer_version(filename: str) -> str:
    """Extract version tag from filename, defaulting to 'v1'."""
    match = _VERSION_RE.search(filename)
    return match.group(1).lower() if match else "v1"


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def seed_prompt_versions(session: Session) -> int:
    """Upsert a ``PromptVersion`` row for every prompt file found on disk.

    Returns the number of rows created or updated.
    """
    upserted = 0
    for subdir in ("system", "user"):
        target = _PROMPTS_ROOT / subdir
        if not target.is_dir():
            continue
        for path in sorted(target.iterdir()):
            if not path.is_file() or path.suffix not in {".md", ".txt", ".json"}:
                continue
            role = _infer_role(path.name)
            if role is None:
                continue
            version = _infer_version(path.name)
            content = path.read_text(encoding="utf-8")
            fhash = _file_hash(content)

            # Look up existing row
            stmt = select(PromptVersion).where(
                PromptVersion.role == role,
                PromptVersion.version == version,
            )
            row = session.execute(stmt).scalar_one_or_none()

            if row is None:
                row = PromptVersion(
                    name=path.name,
                    role=role,
                    version=version,
                    system_prompt=content if subdir == "system" else "",
                    user_template=content if subdir == "user" else "",
                    schema_json={"file": path.name, "hash": fhash},
                    is_active=True,
                    notes=f"Auto-seeded from {subdir}/{path.name}",
                )
                session.add(row)
                upserted += 1
            else:
                # Update content if hash changed
                current_hash = (row.schema_json or {}).get("hash")
                if current_hash != fhash:
                    if subdir == "system":
                        row.system_prompt = content
                    else:
                        row.user_template = content
                    row.schema_json = {"file": path.name, "hash": fhash}
                    upserted += 1

    session.flush()
    return upserted
