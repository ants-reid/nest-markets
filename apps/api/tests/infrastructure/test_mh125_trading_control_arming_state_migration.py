"""MH-125 migration verification for trading_control_arming_states table."""

from pathlib import Path


def test_mh125_migration_declares_trading_control_arming_states_table_indexes_and_seed_row():
    migration = Path("alembic/versions/q2r3s4t5u6v7_add_mh125_trading_control_arming_states.py")
    text = migration.read_text(encoding="utf-8")

    assert 'revision = "q2r3s4t5u6v7"' in text
    assert 'down_revision = "p1q2r3s4t5u6"' in text
    assert '"trading_control_arming_states",' in text
    assert 'sa.UniqueConstraint("scope", "trading_mode", name="uq_trading_control_arming_states_scope_mode")' in text
    assert 'name="ck_trading_control_arming_states_state"' in text
    assert 'name="ck_trading_control_arming_states_enablement_status"' in text
    assert 'name="ck_trading_control_arming_states_armed_fields"' in text
    assert 'name="ck_trading_control_arming_states_disarmed_expiry"' in text
    assert 'op.create_index(' in text
    assert '"ix_trading_control_arming_states_state_expires_at"' in text
    assert '"ix_trading_control_arming_states_updated_at"' in text
    assert 'INSERT INTO trading_control_arming_states' in text
    assert "'auto_paper'" in text
    assert "'paper'" in text
    assert "'disarmed'" in text
    assert 'op.drop_table("trading_control_arming_states")' in text