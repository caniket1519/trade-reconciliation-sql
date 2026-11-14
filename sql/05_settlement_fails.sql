-- Settlement fail rate by counterparty, ranked. Flags anyone above 5% on a
-- meaningful volume (20+ trades) and any trading with an inactive counterparty.
SELECT c.cpty_id, c.cpty_name,
       COUNT(*)                                                        AS trades_due,
       SUM(st.status = 'FAILED')                                       AS failed,
       ROUND(100.0 * SUM(st.status = 'FAILED') / COUNT(*), 1)          AS fail_rate_pct,
       SUM(st.status = 'FAILED' AND st.actual_settle_date IS NULL)     AS still_unsettled,
       RANK() OVER (ORDER BY 1.0 * SUM(st.status = 'FAILED') / COUNT(*) DESC) AS fail_rank,
       CASE WHEN c.is_active = 0 THEN 'INACTIVE - SHOULD NOT TRADE'
            WHEN COUNT(*) >= 20 AND 1.0 * SUM(st.status = 'FAILED') / COUNT(*) > 0.05
            THEN 'REVIEW COUNTERPARTY' ELSE '' END                     AS flag
FROM settlements st
JOIN trades t         ON t.trade_id = st.trade_id
JOIN counterparties c ON c.cpty_id  = t.cpty_id
GROUP BY c.cpty_id, c.cpty_name, c.is_active
ORDER BY fail_rate_pct DESC;
