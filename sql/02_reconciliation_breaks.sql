-- Every trade or confirmation that does not match, largest value first.
SELECT break_type, trade_id, conf_id, trade_ref, trade_date, isin, cpty_id,
       our_side, broker_side, our_qty, broker_qty, our_price, broker_price,
       our_settle, broker_settle, notional_gbp
FROM v_recon
WHERE break_type <> 'MATCHED'
ORDER BY notional_gbp DESC;
