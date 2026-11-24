BEGIN;

CREATE SCHEMA dw_manual;

CREATE TABLE dw_manual.dim_carrier (
    carrier_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrier_code VARCHAR(8) NOT NULL UNIQUE,
    carrier_name VARCHAR(80)
);

CREATE TABLE dw_manual.dim_depot (
    depot_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    depot_id INTEGER NOT NULL,
    city VARCHAR(60),
    manager_name VARCHAR(80),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL
);

CREATE UNIQUE INDEX dim_depot_current_uq
    ON dw_manual.dim_depot (depot_id) WHERE is_current;

CREATE TABLE dw_manual.dim_ship_date (
    ship_date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL
);

CREATE TABLE dw_manual.fact_shipments (
    shipment_id BIGINT PRIMARY KEY,
    carrier_code VARCHAR(8),
    depot_id INTEGER,
    shipped_at TIMESTAMPTZ,
    weight_kg NUMERIC(10,3),
    freight_cost NUMERIC(12,2),
    carrier_key BIGINT REFERENCES dw_manual.dim_carrier (carrier_key),
    depot_key BIGINT REFERENCES dw_manual.dim_depot (depot_key),
    ship_date_key INTEGER REFERENCES dw_manual.dim_ship_date (ship_date_key)
);

COMMIT;
