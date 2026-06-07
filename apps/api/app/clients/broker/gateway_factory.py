"""Broker gateway factory — instantiates appropriate broker adapter."""
from __future__ import annotations

from threading import Lock
from typing import Literal

from app.clients.broker.broker_interface import BrokerInterface
from app.clients.broker.ibkr_adapter import IBKRAdapter

BrokerType = Literal["ibkr", "paper", "tws", "tws_socket"]


_tws_cache_lock = Lock()
_tws_shared_brokers: dict[tuple[str, int, int, str | None, bool], BrokerInterface] = {}


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
        tws_submit_enabled: bool = False,
    ) -> BrokerInterface:
        """Create a broker adapter.

        Args:
            broker_type:  "ibkr" (CP Gateway, default), "paper" (not yet
                          implemented), or "tws"/"tws_socket" (socket
                          adapter; must be explicitly selected).
            base_url:     Gateway URL (IBKR only). Defaults to local paper gateway.
            timeout:      HTTP request timeout in seconds.
            tws_submit_enabled: Defence-in-depth flag for the TWS adapter.
                          When False (default), the adapter opens its IB
                          socket as read-only and refuses every submit call.

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
            host = tws_host or "127.0.0.1"
            port = tws_port if tws_port is not None else 4002
            client_id = tws_client_id if tws_client_id is not None else 43
            submit_enabled = bool(tws_submit_enabled)
            cache_key = (host, int(port), int(client_id), preferred_account_id, submit_enabled)

            with _tws_cache_lock:
                cached = _tws_shared_brokers.get(cache_key)
                if cached is not None:
                    return cached

                broker = TwsBroker(
                    host=host,
                    port=port,
                    client_id=client_id,
                    account_id=preferred_account_id,
                    connect_timeout=timeout,
                    submit_enabled=submit_enabled,
                )
                _tws_shared_brokers[cache_key] = broker
                return broker
        if broker_type == "paper":
            # Placeholder for paper trading adapter (to be implemented)
            raise NotImplementedError("Paper trading adapter not yet implemented")
        raise ValueError(f"Unknown broker type: {broker_type}")
