"""Broker gateway factory — instantiates appropriate broker adapter."""
from __future__ import annotations

from typing import Literal

from app.clients.broker.broker_interface import BrokerInterface
from app.clients.broker.ibkr_adapter import IBKRAdapter

BrokerType = Literal["ibkr", "paper", "tws", "tws_socket"]


class BrokerGatewayFactory:
    """Factory for creating broker adapter instances."""

    @staticmethod
    def create(
        broker_type: BrokerType,
        base_url: str | None = None,
        timeout: float = 30.0,
        preferred_account_id: str | None = None,
        tws_host: str | None = None,
        tws_port: int | None = None,
        tws_client_id: int | None = None,
    ) -> BrokerInterface:
        """Create a broker adapter.

        Args:
            broker_type:  "ibkr" (CP Gateway, default), "paper" (not yet
                          implemented), or "tws"/"tws_socket" (read-only
                          scaffold; must be explicitly selected).
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
        if broker_type in ("tws", "tws_socket"):
            # Lazy import keeps ib_async optional at app/test collection time.
            from app.clients.broker.tws_adapter import TwsBroker

            return TwsBroker(
                host=tws_host or "127.0.0.1",
                port=tws_port if tws_port is not None else 4002,
                client_id=tws_client_id if tws_client_id is not None else 43,
                account_id=preferred_account_id,
                connect_timeout=timeout,
            )
        if broker_type == "paper":
            # Placeholder for paper trading adapter (to be implemented)
            raise NotImplementedError("Paper trading adapter not yet implemented")
        raise ValueError(f"Unknown broker type: {broker_type}")
