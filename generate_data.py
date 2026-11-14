"""
Generate SIMULATED trade data for the reconciliation project.

Nothing here is real: securities, counterparties, ISINs, LEIs, prices and
trades are all invented. Known issues are planted on purpose so the SQL
checks can be tested against an answer key (printed at the end).

Usage:  python generate_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

REPORT_DATE = date(2026, 10, 30)


# ---------------------------------------------------------------- calendar
def business_days(start, end):
    d, out = start, []
    while d <= end:
        if d.weekday() < 5:          # weekends only; holidays ignored for simplicity
            out.append(d)
        d += timedelta(days=1)
    return out


CAL = business_days(date(2026, 9, 1), date(2026, 11, 30))
BD_INDEX = {d: i for i, d in enumerate(CAL)}
TRADE_DAYS = [d for d in CAL if date(2026, 10, 1) <= d <= REPORT_DATE]


def add_bd(d, n):
    return CAL[BD_INDEX[d] + n]


# ---------------------------------------------------------------- reference data
def isin_check_digit(body):
    digits = "".join(str(int(c, 36)) for c in body)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return str((10 - total % 10) % 10)


def make_isin(country, num):
    body = f"{country}{num:09d}"
    return body + isin_check_digit(body)


MARKETS = {  # market: (country, currency, settlement cycle in business days)
    "LSE":   ("GB", "GBP", 2),
    "NYSE":  ("US", "USD", 1),
    "XETRA": ("DE", "EUR", 2),
}
SEC_NAMES = {
    "LSE":   [("Northbridge Energy plc", "Energy", 4.20), ("Thames Retail Group plc", "Consumer", 2.85),
              ("Albion Bank plc", "Financials", 6.10), ("Kestrel Pharma plc", "Healthcare", 18.40),
              ("Highland Mining plc", "Materials", 9.75)],
    "NYSE":  [("Summit Cloud Inc", "Technology", 142.00), ("Redwood Health Corp", "Healthcare", 88.50),
              ("Atlas Motors Inc", "Industrials", 61.20), ("Bluewater Foods Inc", "Consumer", 37.80),
              ("Pioneer Payments Inc", "Financials", 205.00)],
    "XETRA": [("Rhein Chemie AG", "Materials", 54.30), ("Nordlicht Solar AG", "Energy", 23.60),
              ("Alpen Logistik AG", "Industrials", 71.90), ("Hansa Versicherung AG", "Financials", 112.40),
              ("Bavaria Tech AG", "Technology", 96.10)],
}
securities = []
n = 100
for mkt, names in SEC_NAMES.items():
    country, ccy, cycle = MARKETS[mkt]
    for name, sector, px in names:
        n += 1
        securities.append(dict(isin=make_isin(country, 4_200_000 + n), name=name, market=mkt,
                               currency=ccy, sector=sector, settlement_cycle=cycle, base_price=px))

CPTY = [("CP01", "Alpha Securities Ltd", "GB", 1), ("CP02", "Meridian Brokers Ltd", "GB", 1),
        ("CP03", "Granite Capital Markets", "US", 1), ("CP04", "Harbour Prime LLP", "GB", 1),
        ("CP05", "Lumen Clearing Ltd", "IE", 1), ("CP06", "Oakstone Securities", "US", 1),
        ("CP07", "Vertex Global Markets", "DE", 1), ("CP08", "Wexford Partners", "GB", 0)]
ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
counterparties = []
for cid, name, country, active in CPTY:
    lei = "".join(random.choice(ALNUM) for _ in range(18)) + "00"
    counterparties.append(dict(cpty_id=cid, cpty_name=name, country=country,
                               lei="" if cid == "CP06" else lei,    # planted: missing LEI
                               is_active=active))
CPTY_WEIGHTS = [20, 18, 15, 14, 12, 10, 11, 0]   # inactive CP08 only used when planted

# ---------------------------------------------------------------- prices & FX
prices, close = [], {}
for s in securities:
    px = s["base_price"]
    for d in CAL:
        if d > REPORT_DATE:
            break
        px = round(px * (1 + random.gauss(0.0004, 0.014)), 4)
        close[(s["isin"], d)] = px
        prices.append(dict(isin=s["isin"], price_date=d, close_price=px))

fx, fx_rate = [], {}
usd, eur = 0.755, 0.862
for d in CAL:
    if d > REPORT_DATE:
        break
    usd = round(usd * (1 + random.gauss(0, 0.003)), 5)
    eur = round(eur * (1 + random.gauss(0, 0.002)), 5)
    for ccy, rate in (("GBP", 1.0), ("USD", usd), ("EUR", eur)):
        fx_rate[(ccy, d)] = rate
        fx.append(dict(rate_date=d, currency=ccy, rate_to_gbp=rate))

# ---------------------------------------------------------------- trades (front-office booking)
BOOK = {"LSE": "EQ_UK", "NYSE": "EQ_US", "XETRA": "EQ_EU"}
TRADERS = {"EQ_UK": ["JMW", "SKO"], "EQ_US": ["RTD", "ALC"], "EQ_EU": ["MBH", "KLN"]}
trades, k = [], 0
for d in TRADE_DAYS:
    for _ in range(random.randint(45, 65)):
        k += 1
        s = random.choice(securities)
        book = BOOK[s["market"]]
        trades.append(dict(
            trade_id=f"T{k:06d}", trade_date=d, isin=s["isin"], side=random.choice(["BUY", "SELL"]),
            quantity=random.randint(1, 100) * 100,
            price=round(close[(s["isin"], d)] * (1 + random.uniform(-0.005, 0.005)), 4),
            currency=s["currency"],
            cpty_id=random.choices([c["cpty_id"] for c in counterparties], CPTY_WEIGHTS)[0],
            book=book, trader=random.choice(TRADERS[book]),
            settle_date=add_bd(d, s["settlement_cycle"])))

# confirmations start as perfect copies of the trades (the broker's view)
confs = [dict(conf_id=f"C{i + 1:06d}", trade_ref=t["trade_id"], trade_date=t["trade_date"], isin=t["isin"], side=t["side"],
              quantity=t["quantity"], price=t["price"], cpty_id=t["cpty_id"], settle_date=t["settle_date"])
         for i, t in enumerate(trades)]
conf_by_ref = {c["trade_ref"]: c for c in confs}

# ---------------------------------------------------------------- plant issues on DISJOINT trades
pool = random.sample(range(len(trades)), 120)
take = lambda n: [pool.pop() for _ in range(n)]
key = {}

ix = take(18)                                   # broker never confirmed
missing = {trades[i]["trade_id"] for i in ix}
key["MISSING_CONFIRMATION (no broker conf)"] = len(ix)

for i in take(12):                              # quantity differs
    c = conf_by_ref[trades[i]["trade_id"]]
    q = trades[i]["quantity"] + random.choice([-1, 1]) * random.randint(1, 10) * 100
    c["quantity"] = q if q > 0 else trades[i]["quantity"] + 100
key["QUANTITY_BREAK"] = 12

for i in take(10):                              # price outside 0.05% tolerance
    conf_by_ref[trades[i]["trade_id"]]["price"] = round(trades[i]["price"] * random.choice([0.99, 1.008, 1.012]), 4)
key["PRICE_BREAK"] = 10

for i in take(15):                              # tiny rounding difference: must still MATCH
    conf_by_ref[trades[i]["trade_id"]]["price"] = round(trades[i]["price"] * 1.0002, 4)
key["price within tolerance (should match)"] = 15

for i in take(4):                               # buy/sell swapped
    c = conf_by_ref[trades[i]["trade_id"]]
    c["side"] = "SELL" if trades[i]["side"] == "BUY" else "BUY"
key["SIDE_BREAK"] = 4

for i in take(8):                               # we booked the wrong settlement date
    t = trades[i]
    cycle = next(s["settlement_cycle"] for s in securities if s["isin"] == t["isin"])
    t["settle_date"] = add_bd(t["trade_date"], cycle + 1)
key["SETTLE_DATE_BREAK (wrong settlement cycle booked)"] = 8

for i in take(5):                               # counterparty left blank
    trades[i]["cpty_id"] = ""
key["COUNTERPARTY_BREAK (blank counterparty)"] = 5

bad_isins = [make_isin("GB", 4_299_991), make_isin("GB", 4_299_992), make_isin("US", 4_299_993), "GB04200101"]
for i, bad in zip(take(4), bad_isins):          # ISIN not in reference data / malformed
    trades[i]["isin"] = bad
key["SECURITY_BREAK (unknown or malformed ISIN)"] = 4

for i in take(3):                               # traded with an inactive counterparty
    trades[i]["cpty_id"] = "CP08"
    conf_by_ref[trades[i]["trade_id"]]["cpty_id"] = "CP08"
key["inactive counterparty (matches, but DQ flag)"] = 3

dups = []
for i in take(4):                               # booked twice
    k += 1
    dup = dict(trades[i]); dup["trade_id"] = f"T{k:06d}"
    dups.append(dup)
trades += dups
key["DUPLICATE booking (also shows as missing conf)"] = 4

confs = [c for c in confs if c["trade_ref"] not in missing]
for j in range(6):                              # broker conf we never booked
    s = random.choice(securities)
    d = random.choice(TRADE_DAYS[:-3])
    confs.append(dict(conf_id=f"C9{j:05d}", trade_ref=f"EXT-{random.randint(10000, 99999)}", trade_date=d, isin=s["isin"],
                      side=random.choice(["BUY", "SELL"]), quantity=random.randint(1, 50) * 100,
                      price=round(close[(s["isin"], d)], 4), cpty_id=random.choice(["CP01", "CP02", "CP04"]),
                      settle_date=add_bd(d, s["settlement_cycle"])))
key["UNBOOKED_CONFIRMATION (broker conf, no trade)"] = 6

# ---------------------------------------------------------------- settlements
FAIL_P = {"CP02": 0.12}                         # Meridian fails far more often
REASONS = ["INSUFFICIENT_SECURITIES", "SSI_MISMATCH", "LATE_CONFIRMATION", "CASH_SHORTFALL"]
sec_cycle = {s["isin"]: s["settlement_cycle"] for s in securities}
settlements = []
for t in trades[: len(trades) - len(dups)]:
    if t["trade_id"] in missing or t["isin"] not in sec_cycle or not t["cpty_id"]:
        continue
    due = add_bd(t["trade_date"], sec_cycle[t["isin"]])
    if due > REPORT_DATE:
        continue
    failed = random.random() < FAIL_P.get(t["cpty_id"], 0.02)
    actual = due
    if failed:
        late = add_bd(due, random.randint(1, 4))
        actual = late if late <= REPORT_DATE else ""
    settlements.append(dict(trade_id=t["trade_id"], due_date=due, actual_settle_date=actual,
                            status="FAILED" if failed else "SETTLED",
                            fail_reason=random.choice(REASONS) if failed else ""))

# ---------------------------------------------------------------- opening positions
opening = [dict(book=BOOK[s["market"]], isin=s["isin"], quantity=random.randint(50, 300) * 100)
           for s in securities]


# ---------------------------------------------------------------- write
def write(name, rows):
    with open(DATA / f"{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


random.shuffle(confs)
write("securities", [{k2: v for k2, v in s.items() if k2 != "base_price"} for s in securities])
write("counterparties", counterparties)
write("calendar", [dict(cal_date=d, bd_index=i) for i, d in enumerate(CAL)])
write("prices", prices)
write("fx_rates", fx)
write("trades", trades)
write("confirmations", confs)
write("settlements", settlements)
write("opening_positions", opening)

print(f"Simulated {len(trades):,} trades, {len(confs):,} confirmations, "
      f"{len(settlements):,} settlements ({sum(s['status'] == 'FAILED' for s in settlements)} failed)")
print("\nANSWER KEY - planted issues the SQL should find:")
for k2, v in key.items():
    print(f"  {v:>3}  {k2}")
