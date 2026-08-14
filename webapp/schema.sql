-- PostgreSQL schema for the Inventory & Order Management web app.
-- Idempotent: safe to re-run (uses IF NOT EXISTS). Run via: flask init-db

-- =========================================================================
-- Users (authentication). Small team, simple login/password.
-- =========================================================================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,                   -- Werkzeug PBKDF2 hash
    display_name  TEXT,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,  -- admins can manage users & reset data
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================================================================
-- Products
-- =========================================================================
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    base_price    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    image         BYTEA,                           -- stored as binary (portable across hosts)
    image_ext     TEXT,                            -- '.png'/'.jpg' ... for the serving route
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_variants (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    color         TEXT NOT NULL DEFAULT '',
    size          TEXT NOT NULL DEFAULT '',
    UNIQUE (product_id, color, size)
);

-- =========================================================================
-- Orders. Declared before stock_out (which references it).
-- Stock is reduced only when an order is shipped (status='shipped').
-- =========================================================================
CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name TEXT NOT NULL,
    order_date    DATE NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'shipped')),
    shipped_date  DATE,
    total         NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- =========================================================================
-- Stock movement log (append-only). Stock is always derived:
--   current = SUM(stock_in.quantity) - SUM(stock_out.quantity)
-- =========================================================================
CREATE TABLE IF NOT EXISTS stock_in (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    color         TEXT NOT NULL DEFAULT '',
    size          TEXT NOT NULL DEFAULT '',
    quantity      INTEGER NOT NULL DEFAULT 0,
    unit_cost     NUMERIC(12, 2) NOT NULL DEFAULT 0,
    date          DATE NOT NULL,
    note          TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS stock_out (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    color         TEXT NOT NULL DEFAULT '',
    size          TEXT NOT NULL DEFAULT '',
    quantity      INTEGER NOT NULL DEFAULT 0,
    date          DATE NOT NULL,
    customer_name TEXT NOT NULL DEFAULT '',
    note          TEXT NOT NULL DEFAULT '',
    order_id      INTEGER REFERENCES orders (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
    color         TEXT NOT NULL DEFAULT '',
    size          TEXT NOT NULL DEFAULT '',
    quantity      INTEGER NOT NULL DEFAULT 0,
    unit_price    NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- Indexes for the common query paths.
CREATE INDEX IF NOT EXISTS idx_stock_in_product  ON stock_in (product_id);
CREATE INDEX IF NOT EXISTS idx_stock_out_product ON stock_out (product_id);
CREATE INDEX IF NOT EXISTS idx_stock_out_order   ON stock_out (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders (status, shipped_date);
