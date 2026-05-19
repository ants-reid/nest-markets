-- Default scoring configuration seed
-- Loaded by scripts/db/seed.sh

INSERT INTO scoring_configs (
  id,
  config_name,
  momentum_weight,
  risk_weight,
  news_weight,
  execution_weight,
  is_active,
  created_at
) VALUES (
  uuid_generate_v4(),
  'default',
  0.40,
  0.30,
  0.10,
  0.20,
  true,
  NOW()
)
ON CONFLICT (config_name) DO NOTHING;
