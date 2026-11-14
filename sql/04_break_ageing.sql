-- Open breaks aged in business days and ranked for the ops team to work.
-- Old, high-value breaks are escalated.
WITH aged AS (
    SELECT r.break_type, COALESCE(r.trade_id, r.trade_ref) AS reference, r.trade_date,
           r.cpty_id, r.notional_gbp,
           rep.bd_index - td.bd_index AS age_bd
    FROM v_recon r
    JOIN calendar td  ON td.cal_date  = r.trade_date
    JOIN calendar rep ON rep.cal_date = (SELECT report_date FROM report_params)
    WHERE r.break_type <> 'MATCHED'
)
SELECT reference, break_type, trade_date, cpty_id, notional_gbp, age_bd,
       CASE WHEN age_bd <= 1 THEN '0-1 days'
            WHEN age_bd <= 3 THEN '2-3 days'
            ELSE '4+ days' END                                AS age_bucket,
       RANK() OVER (ORDER BY notional_gbp DESC)               AS value_rank,
       CASE WHEN age_bd >= 3 AND notional_gbp >= 250000 THEN 'ESCALATE' ELSE '' END AS action
FROM aged
ORDER BY action DESC, age_bd DESC, notional_gbp DESC;
