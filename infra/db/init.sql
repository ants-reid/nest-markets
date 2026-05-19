-- Market Hunter database initialization
-- Run automatically by Docker entrypoint on first container start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant privileges (already created by POSTGRES_USER env var)
GRANT ALL PRIVILEGES ON DATABASE markethunter TO markethunter;
