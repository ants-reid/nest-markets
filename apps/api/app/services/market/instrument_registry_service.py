"""InstrumentRegistryService — resolve symbol metadata."""

from __future__ import annotations


class InstrumentRegistryService:
    """Centralised registry for instrument/symbol metadata.

    In Phase 5 this is a thin stub; the registry will be backed by the DB
    in a later phase.
    """

    def __init__(self) -> None:
        self._registry: dict[str, dict] = {}

    def register(self, symbol: str, **metadata) -> None:
        """Register or update a symbol with arbitrary metadata."""
        self._registry[symbol] = metadata

    def lookup(self, symbol: str) -> dict | None:
        """Return metadata for a symbol, or None if not registered."""
        return self._registry.get(symbol)

    def all_symbols(self) -> list[str]:
        """Return all registered symbols."""
        return list(self._registry.keys())

    def is_registered(self, symbol: str) -> bool:
        return symbol in self._registry
