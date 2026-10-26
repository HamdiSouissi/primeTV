-- =============================================================================
-- PrimeTV — initialisation PostgreSQL
-- Extensions utiles à la recherche (accents, fautes de frappe) et au monitoring.
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

COMMENT ON DATABASE primetv IS 'PrimeTV — catalogue IPTV, EPG et profils';

-- Le schéma applicatif est créé automatiquement par SQLAlchemy au démarrage
-- (AUTO_CREATE_SCHEMA=true). Pour une gestion versionnée, voir docs/DEVELOPER_GUIDE.md.
