-- Trade reconciliation database (SQLite). All data is simulated.
DROP TABLE IF EXISTS report_params;
CREATE TABLE report_params (report_date TEXT, price_tolerance REAL);
INSERT INTO report_params VALUES ('2026-10-30', 0.0005);   -- 0.05% price tolerance

CREATE TABLE securities (
    isin TEXT PRIMARY KEY, name TEXT, market TEXT, currency TEXT,
    sector TEXT, settlement_cycle INTEGER                    -- business days: 1 = T+1, 2 = T+2
);
CREATE TABLE counterparties (
    cpty_id TEXT PRIMARY KEY, cpty_name TEXT, country TEXT, lei TEXT, is_active INTEGER
);
CREATE TABLE calendar (cal_date TEXT PRIMARY KEY, bd_index INTEGER);   -- business days only
CREATE TABLE prices   (isin TEXT, price_date TEXT, close_price REAL);
CREATE TABLE fx_rates (rate_date TEXT, currency TEXT, rate_to_gbp REAL);

-- Front-office booking system (our view)
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY, trade_date TEXT, isin TEXT, side TEXT, quantity INTEGER,
    price REAL, currency TEXT, cpty_id TEXT, book TEXT, trader TEXT, settle_date TEXT
);
-- Broker confirmations (their view)
CREATE TABLE confirmations (
    conf_id TEXT PRIMARY KEY, trade_ref TEXT, trade_date TEXT, isin TEXT, side TEXT,
    quantity INTEGER, price REAL, cpty_id TEXT, settle_date TEXT
);
CREATE TABLE settlements (
    trade_id TEXT, due_date TEXT, actual_settle_date TEXT, status TEXT, fail_reason TEXT
);
CREATE TABLE opening_positions (book TEXT, isin TEXT, quantity INTEGER);

CREATE INDEX ix_conf_ref    ON confirmations (trade_ref);
CREATE INDEX ix_prices      ON prices (isin, price_date);
CREATE INDEX ix_fx          ON fx_rates (currency, rate_date);

-- Trade-by-trade match of our bookings against broker confirmations.
-- FULL OUTER JOIN keeps trades with no confirmation AND confirmations with no trade.
CREATE VIEW v_recon AS
SELECT
    t.trade_id, c.conf_id, c.trade_ref,
    COALESCE(t.trade_date, c.trade_date)                     AS trade_date,
    COALESCE(t.isin, c.isin)                                 AS isin,
    COALESCE(t.cpty_id, c.cpty_id)                           AS cpty_id,
    t.book,
    t.side AS our_side,  c.side AS broker_side,
    t.quantity AS our_qty, c.quantity AS broker_qty,
    t.price AS our_price, c.price AS broker_price,
    t.settle_date AS our_settle, c.settle_date AS broker_settle,
    CASE
        WHEN t.trade_id IS NULL                       THEN 'UNBOOKED_CONFIRMATION'
        WHEN c.conf_id  IS NULL                       THEN 'MISSING_CONFIRMATION'
        WHEN t.isin <> c.isin                         THEN 'SECURITY_BREAK'
        WHEN t.cpty_id IS NULL OR t.cpty_id <> c.cpty_id THEN 'COUNTERPARTY_BREAK'
        WHEN t.side <> c.side                         THEN 'SIDE_BREAK'
        WHEN t.quantity <> c.quantity                 THEN 'QUANTITY_BREAK'
        WHEN ABS(t.price - c.price) / c.price > (SELECT price_tolerance FROM report_params)
                                                      THEN 'PRICE_BREAK'
        WHEN t.settle_date <> c.settle_date           THEN 'SETTLE_DATE_BREAK'
        ELSE 'MATCHED'
    END AS break_type,
    -- trade value converted to GBP at the trade-date FX rate
    ROUND(COALESCE(t.quantity, c.quantity) * COALESCE(t.price, c.price) * fx.rate_to_gbp, 2) AS notional_gbp
FROM trades t
FULL OUTER JOIN confirmations c ON c.trade_ref = t.trade_id
LEFT JOIN securities s ON s.isin = COALESCE(c.isin, t.isin)
LEFT JOIN fx_rates fx  ON fx.currency = COALESCE(s.currency, t.currency)
                      AND fx.rate_date = COALESCE(t.trade_date, c.trade_date);
