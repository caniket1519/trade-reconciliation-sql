-- One-page KPI summary for management.
SELECT 'Trades booked' AS kpi, CAST(COUNT(*) AS TEXT) AS value FROM trades
UNION ALL
SELECT 'Broker confirmations received', CAST(COUNT(*) AS TEXT) FROM confirmations
UNION ALL
SELECT 'Auto-match rate (%)',
       CAST(ROUND(100.0 * SUM(break_type = 'MATCHED') / COUNT(*), 1) AS TEXT) FROM v_recon
UNION ALL
SELECT 'Open breaks', CAST(SUM(break_type <> 'MATCHED') AS TEXT) FROM v_recon
UNION ALL
SELECT 'Value of open breaks (GBP)',
       printf('%,d', CAST(SUM(CASE WHEN break_type <> 'MATCHED' THEN notional_gbp END) AS INTEGER)) FROM v_recon
UNION ALL
SELECT 'Settlement fail rate (%)',
       CAST(ROUND(100.0 * SUM(status = 'FAILED') / COUNT(*), 1) AS TEXT) FROM settlements
UNION ALL
SELECT 'Fails still unsettled', CAST(SUM(status = 'FAILED' AND actual_settle_date IS NULL) AS TEXT) FROM settlements;
