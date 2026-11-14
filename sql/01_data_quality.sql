-- Data-quality scorecard for the booking system: completeness, validity,
-- uniqueness, timeliness and accuracy. One row per check.
WITH checks AS (
    SELECT 'Completeness' AS dimension, 'Trade has a counterparty' AS check_name,
           COUNT(*) AS rows_checked, SUM(cpty_id IS NULL) AS rows_failed
    FROM trades
    UNION ALL
    SELECT 'Completeness', 'Counterparty has an LEI',
           COUNT(*), SUM(lei IS NULL)
    FROM counterparties
    UNION ALL
    SELECT 'Validity', 'ISIN is 12 characters and exists in security master',
           COUNT(*), SUM(s.isin IS NULL OR LENGTH(t.isin) <> 12)
    FROM trades t LEFT JOIN securities s ON s.isin = t.isin
    UNION ALL
    SELECT 'Validity', 'Counterparty is active',
           COUNT(*), SUM(c.is_active = 0)
    FROM trades t JOIN counterparties c ON c.cpty_id = t.cpty_id
    UNION ALL
    SELECT 'Uniqueness', 'No duplicate bookings (same date, ISIN, side, qty, price, cpty)',
           (SELECT COUNT(*) FROM trades),
           (SELECT COALESCE(SUM(n - 1), 0) FROM (
                SELECT COUNT(*) AS n FROM trades
                GROUP BY trade_date, isin, side, quantity, price, cpty_id
                HAVING COUNT(*) > 1))
    UNION ALL
    SELECT 'Timeliness', 'Settlement date follows market cycle (T+1 US, T+2 UK/EU)',
           COUNT(*), SUM(t.settle_date <> exp_d.cal_date)
    FROM trades t
    JOIN securities s   ON s.isin = t.isin
    JOIN calendar td    ON td.cal_date = t.trade_date
    JOIN calendar exp_d ON exp_d.bd_index = td.bd_index + s.settlement_cycle
    UNION ALL
    SELECT 'Accuracy', 'Trade price within 2% of that day''s closing price',
           COUNT(*), SUM(ABS(t.price - p.close_price) / p.close_price > 0.02)
    FROM trades t JOIN prices p ON p.isin = t.isin AND p.price_date = t.trade_date
)
SELECT dimension, check_name, rows_checked, rows_failed,
       ROUND(100.0 * (rows_checked - rows_failed) / rows_checked, 2) AS pass_rate_pct,
       CASE WHEN rows_failed = 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM checks;
