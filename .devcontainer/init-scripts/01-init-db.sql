-- FundCast Database Initialization Script
-- This script sets up the development database with required extensions and initial data

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create additional databases for testing
CREATE DATABASE fundcast_test;

-- Switch to the test database and set up extensions there too
\c fundcast_test;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Switch back to main database
\c fundcast_dev;

-- Create custom types that might be needed
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('user', 'founder', 'investor', 'compliance', 'admin');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'offering_status') THEN
        CREATE TYPE offering_status AS ENUM ('draft', 'submitted', 'under_review', 'approved', 'active', 'closed', 'cancelled');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'market_type') THEN
        CREATE TYPE market_type AS ENUM ('binary', 'categorical', 'scalar');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'market_status') THEN
        CREATE TYPE market_status AS ENUM ('active', 'resolved', 'cancelled', 'paused');
    END IF;
END
$$;

-- Create some utility functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a function to generate nanoids (for shorter IDs)
CREATE OR REPLACE FUNCTION generate_nanoid(size int DEFAULT 21)
RETURNS text AS $$
DECLARE
    alphabet text := '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
    id text := '';
    i int;
    pos int;
BEGIN
    FOR i IN 1..size LOOP
        pos := 1 + cast(random() * (length(alphabet) - 1) as int);
        id := id || substr(alphabet, pos, 1);
    END LOOP;
    RETURN id;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Create development-specific configurations
INSERT INTO pg_settings (name, setting, category) VALUES 
    ('log_statement', 'all', 'Logging')
ON CONFLICT DO NOTHING;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE fundcast_dev TO postgres;
GRANT ALL PRIVILEGES ON DATABASE fundcast_test TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Create indexes for common search patterns (will be useful when tables are created)
-- These will be created by SQLAlchemy, but having them here as reference

-- Performance optimization settings for development
ALTER DATABASE fundcast_dev SET log_statement = 'all';
ALTER DATABASE fundcast_dev SET log_min_duration_statement = 0;
ALTER DATABASE fundcast_dev SET shared_preload_libraries = 'pg_stat_statements';

-- Create a view for monitoring query performance (if pg_stat_statements is available)
CREATE OR REPLACE VIEW query_performance AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY total_time DESC;

-- Print initialization status
DO $$
BEGIN
    RAISE NOTICE '✅ FundCast database initialization completed successfully!';
    RAISE NOTICE '📊 Extensions enabled: uuid-ossp, vector, pg_trgm, btree_gin, btree_gist';
    RAISE NOTICE '🗄️ Databases created: fundcast_dev, fundcast_test';
    RAISE NOTICE '🔧 Custom types and functions created';
    RAISE NOTICE '🚀 Ready for development!';
END
$$;