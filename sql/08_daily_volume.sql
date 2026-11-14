-- Daily traded value in GBP with a 5-day moving average and day-on-day change.
WITH daily AS (
    SELECT trade_date, COUNT(*) AS trades, SUM(notional_gbp) AS notional_gbp
    FROM v_recon
    WHERE trade_id IS NOT NULL
    GROUP BY trade_date
)
SELECT trade_date, trades,
       ROUND(notional_gbp, 0)                                                   AS notional_gbp,
       ROUND(AVG(notional_gbp) OVER (ORDER BY trade_date ROWS 4 PRECEDING), 0)  AS moving_avg_5d,
       ROUND(100.0 * (notional_gbp - LAG(notional_gbp) OVER (ORDER BY trade_date))
                   / LAG(notional_gbp) OVER (ORDER BY trade_date), 1)           AS dod_change_pct
FROM daily
ORDER BY trade_date;
