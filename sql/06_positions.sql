-- End-of-period position per book and security: opening + buys - sells,
-- valued at the report-date close in GBP, with each line's share of its book.
WITH flows AS (
    SELECT book, isin,
           SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) AS net_traded
    FROM trades
    GROUP BY book, isin
),
pos AS (
    SELECT o.book, o.isin, s.name, s.currency,
           o.quantity                              AS opening_qty,
           COALESCE(f.net_traded, 0)               AS net_traded,
           o.quantity + COALESCE(f.net_traded, 0)  AS closing_qty
    FROM opening_positions o
    JOIN securities s  ON s.isin = o.isin
    LEFT JOIN flows f  ON f.book = o.book AND f.isin = o.isin
)
SELECT p.book, p.isin, p.name, p.opening_qty, p.net_traded, p.closing_qty,
       pr.close_price, p.currency,
       ROUND(p.closing_qty * pr.close_price * fx.rate_to_gbp, 0)               AS market_value_gbp,
       ROUND(100.0 * p.closing_qty * pr.close_price * fx.rate_to_gbp
             / SUM(p.closing_qty * pr.close_price * fx.rate_to_gbp) OVER (PARTITION BY p.book), 1)
                                                                             AS pct_of_book
FROM pos p
JOIN report_params rp
JOIN prices pr   ON pr.isin = p.isin AND pr.price_date = rp.report_date
JOIN fx_rates fx ON fx.currency = p.currency AND fx.rate_date = rp.report_date
ORDER BY p.book, market_value_gbp DESC;
