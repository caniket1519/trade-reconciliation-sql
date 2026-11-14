-- Gross traded value by counterparty with share and cumulative share
-- (concentration). Flags any counterparty above 20% of the total. Where our
-- booking has no counterparty, the broker confirmation fills the gap.
WITH by_cpty AS (
    SELECT COALESCE(r.cpty_id, 'UNKNOWN') AS cpty_id,
           COUNT(*)                        AS trades,
           SUM(r.notional_gbp)             AS gross_gbp
    FROM v_recon r
    WHERE r.trade_id IS NOT NULL
    GROUP BY COALESCE(r.cpty_id, 'UNKNOWN')
)
SELECT b.cpty_id, COALESCE(c.cpty_name, 'Not recorded') AS cpty_name, b.trades,
       ROUND(b.gross_gbp, 0)                                                     AS gross_gbp,
       ROUND(100.0 * b.gross_gbp / SUM(b.gross_gbp) OVER (), 1)                  AS pct_of_total,
       ROUND(100.0 * SUM(b.gross_gbp) OVER (ORDER BY b.gross_gbp DESC
                                            ROWS UNBOUNDED PRECEDING)
                   / SUM(b.gross_gbp) OVER (), 1)                                AS cumulative_pct,
       CASE WHEN b.gross_gbp / SUM(b.gross_gbp) OVER () > 0.20
            THEN 'CONCENTRATION' ELSE '' END                                     AS flag
FROM by_cpty b
LEFT JOIN counterparties c ON c.cpty_id = b.cpty_id
ORDER BY b.gross_gbp DESC;
