"""Broker gateway factory — instantiates appropriate broker adapter."""
from __future__ import annotations

from typing import Literal

from app.clients.broker.broker_interface import BrokerInterface
from app.clients.broker.ibkr_adapter import IBKRAdapter


class BrokerGatewayFactory:
    """Factory for creating broker adapter instances."""

    @staticmethod
    def create(
        broker_type: Literal["ibkr", "paper"],
        base_url: str | None = None,
        timeout: float = 30.0,
        preferred_account_id: str | None = None,
    ) -> BrokerInterface:
        """Create a broker adapter.

        Args:
            broker_type:  "ibkr" for Interactive Brokers, "paper" for paper trading.
            base_url:     Gateway URL (IBKR only). Defaults to local paper gateway.
            timeout:      HTTP request timeout in seconds.

        Returns:
            A concrete BrokerInterface implementation.

        Raises:
            ValueError: If broker_type is not recognized.
        """
        if broker_type == "ibkr":
            url = base_url or "https://localhost:5000/v1/api"
            return IBKRAdapter(
                base_url=url,
                timeout=timeout,
                preferred_account_id=preferred_account_id,
            )
        if broker_type == "paper":
            # Placeholder for paper trading adapter (to be implemented)
            raise NotImplementedError("Paper trading adapter not yet implemented")
        raise ValueError(f"Unknown broker type: {broker_type}")
