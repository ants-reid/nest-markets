"""Package init for macro adapters."""

from __future__ import annotations

from app.clients.macro.base import MacroAdapter, MacroDataPoint
from app.clients.macro.fred import FREDAdapter
from app.clients.macro.mock import MockMacroAdapter

__all__ = ["MacroAdapter", "MacroDataPoint", "FREDAdapter", "MockMacroAdapter"]
