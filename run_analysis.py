"""
Build trade_recon.db from the CSVs in data/, run every query in sql/,
save each result to results/, print the key findings and draw three charts.

Usage:
    python generate_data.py     # (re)create the simulated data
    python run_analysis.py      # build the database and run the analysis
"""
import csv
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
DATA, SQL, RESULTS = ROOT / "data", ROOT / "sql", ROOT / "results"
RESULTS.mkdir(exist_ok=True)
DB = ROOT / "trade_recon.db"
TABLES = ["securities", "counterparties", "calendar", "prices", "fx_rates",
          "trades", "confirmations", "settlements", "opening_positions"]
BLUE = "#2F5F9E"


def load(conn):
    conn.executescript((SQL / "00_schema.sql").read_text())
    for table in TABLES:
        with open(DATA / f"{table}.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        conn.executemany(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [tuple(r[c] if r[c] != "" else None for c in cols) for r in rows],   # blank -> NULL
        )
    conn.commit()


def run(conn, path):
    cur = conn.execute(path.read_text())
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(RESULTS / f"{path.stem}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return cols, rows


def main():
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    load(conn)

    out = {}
    for path in sorted(SQL.glob("0[1-9]_*.sql")):
        out[path.stem] = run(conn, path)
        print(f"{path.stem}: {len(out[path.stem][1])} rows -> results/{path.stem}.csv")

    print("\nKPI SUMMARY")
    for kpi, value in out["09_kpi_summary"][1]:
        print(f"- {kpi}: {value}")

    print("\nBREAKS BY TYPE")
    for bt, n, pct, gbp in out["03_break_summary"][1]:
        print(f"- {bt:<22} {n:>5}  ({pct}%)  GBP {gbp:,.0f}")

    print("\nDATA-QUALITY CHECKS FAILED")
    for dim, check, rows, failed, rate, res in out["01_data_quality"][1]:
        if res == "FAIL":
            print(f"- [{dim}] {check}: {failed} of {rows}")

    esc = [r for r in out["04_break_ageing"][1] if r[-1] == "ESCALATE"]
    print(f"\n{len(esc)} breaks to escalate (3+ business days old and GBP 250k+)")
    for r in out["05_settlement_fails"][1]:
        if r[7]:
            print(f"{r[1]}: fail rate {r[4]}% ({r[3]} of {r[2]}) -> {r[7]}")

    # ---- charts ------------------------------------------------------------
    breaks = [r for r in out["03_break_summary"][1] if r[0] != "MATCHED"]
    plt.figure(figsize=(8, 4.2))
    plt.barh([r[0].replace("_", " ").title() for r in breaks][::-1], [r[1] for r in breaks][::-1], color=BLUE)
    plt.title("Reconciliation breaks by type - Oct 2026 (simulated)")
    plt.xlabel("Number of breaks")
    plt.tight_layout()
    plt.savefig(RESULTS / "breaks_by_type.png", dpi=120)
    plt.close()

    vol = out["08_daily_volume"][1]
    plt.figure(figsize=(8, 4))
    days = [r[0][5:] for r in vol]
    plt.bar(days, [r[2] / 1e6 for r in vol], color="#A9C1E0", label="Daily traded value")
    plt.plot(days, [r[3] / 1e6 for r in vol], color=BLUE, linewidth=2, label="5-day moving average")
    plt.ylabel("GBP millions")
    plt.ylim(0, max(r[2] for r in vol) / 1e6 * 1.3)
    plt.title("Daily traded value - Oct 2026 (simulated)")
    plt.xticks(rotation=60, fontsize=8)
    plt.legend(loc="upper left", ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(RESULTS / "daily_volume.png", dpi=120)
    plt.close()

    fails = out["05_settlement_fails"][1]
    plt.figure(figsize=(8, 4))
    plt.bar([r[1].replace(" ", "\n", 1) for r in fails], [r[4] for r in fails],
            color=["#C0392B" if r[7] else BLUE for r in fails])
    plt.axhline(5, color="grey", linestyle="--", linewidth=1)
    plt.text(len(fails) - 0.5, 5.2, "5% threshold", ha="right", fontsize=8, color="grey")
    plt.ylabel("Fail rate (%)")
    plt.title("Settlement fail rate by counterparty - Oct 2026 (simulated)")
    plt.xticks(fontsize=7)
    plt.tight_layout()
    plt.savefig(RESULTS / "settlement_fails.png", dpi=120)
    plt.close()
    print("\nCharts saved to results/")
    conn.close()


if __name__ == "__main__":
    main()
