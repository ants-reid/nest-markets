-- Default risk profiles seed
-- Loaded by scripts/db/seed.sh

INSERT INTO risk_profiles (
  id,
  profile_name,
  max_position_pct,
  max_daily_loss_pct,
  max_drawdown_pct,
  max_open_positions,
  is_default,
  created_at
) VALUES
  (uuid_generate_v4(), 'conservative', 0.02, 0.01, 0.05, 3, false, NOW()),
  (uuid_generate_v4(), 'moderate',     0.05, 0.02, 0.10, 5, true,  NOW()),
  (uuid_generate_v4(), 'aggressive',   0.10, 0.03, 0.20, 10, false, NOW())
ON CONFLICT (profile_name) DO NOTHING;
