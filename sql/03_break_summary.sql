-- How many records fall into each match status, and the value at stake.
SELECT break_type,
       COUNT(*)                                             AS records,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)   AS pct_of_records,
       ROUND(SUM(notional_gbp), 0)                          AS notional_gbp
FROM v_recon
GROUP BY break_type
ORDER BY (break_type = 'MATCHED') DESC, records DESC;
