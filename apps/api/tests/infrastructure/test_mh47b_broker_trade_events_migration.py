"""MH-47B migration verification for broker_trade_events table."""

from pathlib import Path


def test_mh47b_migration_declares_broker_trade_events_table_and_indexes():
    migration = Path("alembic/versions/p1q2r3s4t5u6_add_mh47_broker_trade_events.py")
    text = migration.read_text(encoding="utf-8")

    assert 'revision = "p1q2r3s4t5u6"' in text
    assert 'down_revision = "o0p1q2r3s4t5"' in text
    assert "op.create_table(" in text
    assert '"broker_trade_events",' in text
    assert 'sa.UniqueConstraint("event_fingerprint", name="uq_broker_trade_event_fingerprint")' in text
    assert 'op.create_index("ix_broker_trade_events_event_fingerprint", "broker_trade_events", ["event_fingerprint"])' in text
    assert 'op.create_index("ix_broker_trade_events_trade_ts", "broker_trade_events", ["trade_ts"])' in text
    assert 'op.drop_table("broker_trade_events")' in text
