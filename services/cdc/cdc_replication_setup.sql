-- SUBOP — PostgreSQL logical replication setup for CDC (M7W22T2)
-- Runs automatically on a clean volume via /docker-entrypoint-initdb.d/.
-- Every statement is idempotent, so it is also safe to run by hand:
--   psql -h localhost -p 5433 -U subop -d subop -f services/cdc/cdc_replication_setup.sql

\set ON_ERROR_STOP on

\getenv cdc_user SUBOP_CDC_USER
\getenv cdc_password SUBOP_CDC_PASSWORD
\getenv cdc_schema SUBOP_CDC_SCHEMA
\getenv cdc_publication SUBOP_CDC_PUBLICATION

-- -----------------------------------------------------------------------------
-- 1. Dedicated replication role
-- Separate from the application user on purpose: CDC credentials are read-only
-- plus REPLICATION, so a leaked CDC credential cannot write to the warehouse.
-- -----------------------------------------------------------------------------
SELECT format(
    'CREATE ROLE %I WITH LOGIN REPLICATION PASSWORD %L',
    :'cdc_user', :'cdc_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'cdc_user')
\gexec

-- -----------------------------------------------------------------------------
-- 2. CDC source schema
-- Separate from the warehouse schema so warehouse writes are never captured as
-- change events. SUBOP_CONN_PG_MAIN and SUBOP_CONN_DW_MAIN point at the same
-- database, so without this separation the publication would feed its own output
-- back into the pipeline.
-- -----------------------------------------------------------------------------
SELECT format('CREATE SCHEMA IF NOT EXISTS %I', :'cdc_schema')
\gexec

SELECT format('SET search_path TO %I, public', :'cdc_schema')
\gexec

-- -----------------------------------------------------------------------------
-- 3. CDC source table
-- Mirrors Architecture Section 5.2's worked example (UPDATE orders SET
-- status='shipped'), so Week 25's latency measurement instruments the exact
-- scenario the architecture specified.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id          BIGSERIAL PRIMARY KEY,
    customer_id BIGINT         NOT NULL,
    status      VARCHAR(32)    NOT NULL DEFAULT 'pending',
    amount      NUMERIC(12, 2) NOT NULL,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- REPLICA IDENTITY FULL puts the complete old row in the WAL on UPDATE/DELETE.
-- The default (primary key only) would leave Week 23's normaliser with just an
-- id in `before`, breaking the {op, table, before, after, ts_ms} contract.
-- Cost: larger WAL volume. Acceptable at demo scale; revisit before pilot.
ALTER TABLE orders REPLICA IDENTITY FULL;

-- Seed rows so Debezium's initial snapshot and Omer's smoke verification have
-- something to read.
INSERT INTO orders (customer_id, status, amount)
SELECT * FROM (VALUES
    (1001, 'pending',   149.90),
    (1002, 'paid',      82.50),
    (1003, 'shipped',  310.00)
) AS seed(customer_id, status, amount)
WHERE NOT EXISTS (SELECT 1 FROM orders);

-- -----------------------------------------------------------------------------
-- 4. Publication
-- Explicit table list, never FOR ALL TABLES — that would capture warehouse
-- writes too. Debezium must run with publication.autocreate.mode=disabled in
-- Week 23 so it uses this publication rather than creating its own.
-- -----------------------------------------------------------------------------
SELECT format(
    'CREATE PUBLICATION %I FOR TABLE %I.orders',
    :'cdc_publication', :'cdc_schema'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = :'cdc_publication')
\gexec

-- -----------------------------------------------------------------------------
-- 5. Grants
-- -----------------------------------------------------------------------------
SELECT format('GRANT USAGE ON SCHEMA %I TO %I', :'cdc_schema', :'cdc_user')
\gexec

SELECT format(
    'GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I',
    :'cdc_schema', :'cdc_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO %I',
    :'cdc_schema', :'cdc_user'
)
\gexec

-- -----------------------------------------------------------------------------
-- Verification (run manually after `docker compose down -v && docker compose up -d`)
--   SHOW wal_level;                    -- expect: logical
--   SELECT pubname, puballtables FROM pg_publication;
--   SELECT * FROM pg_publication_tables;
--   SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'subop_cdc';
-- -----------------------------------------------------------------------------
