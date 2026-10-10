"""Turn the FactSmith WWI CSVs into BigQuery-ready CSVs.

Replays 004 (payment seed), 005 (customer seed) and 006 (re-anchor to a fixed
date) in Python, because the BigQuery sandbox has no DML. Usage:
    python prep_wwi_bq.py <data_dir> <out_dir> [anchor=2026-10-09]
The questions in golden20.py are written for the default anchor.
"""
import csv, gzip, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ANCHOR = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else date(2026, 10, 9)
OUT.mkdir(parents=True, exist_ok=True)

# Column lists come straight from 002_load.sql so they can't drift.
COLS = {m[0]: [c.strip().strip('"') for c in m[1].split(",")]
        for m in re.findall(r'\\copy "([^"]+)" \(([^)]*)\)', (SRC / "002_load.sql").read_text())}
NAMES = {"City": "dim_city", "Customer": "dim_customer", "Date": "dim_date", "Employee": "dim_employee",
         "Payment Method": "dim_payment_method", "Stock Item": "dim_stock_item", "Supplier": "dim_supplier",
         "Transaction Type": "dim_transaction_type", "Movement": "fact_movement", "Order": "fact_order",
         "Purchase": "fact_purchase", "Sale": "fact_sale", "Stock Holding": "fact_stock_holding",
         "Transaction": "fact_transaction"}
FACT_DATES = {"Sale": ["Invoice Date Key", "Delivery Date Key"], "Order": ["Order Date Key", "Picked Date Key"],
              "Movement": ["Date Key"], "Purchase": ["Date Key"], "Transaction": ["Date Key"]}


def read(table):
    with gzip.open(SRC / f"{table.replace(' ', '_')}.csv.gz", "rt", newline="", encoding="utf-8") as f:
        return [dict(zip(COLS[table], r)) for r in csv.reader(f)]


data = {t: read(t) for t in COLS}
delta = ANCHOR - max(date.fromisoformat(r["Invoice Date Key"]) for r in data["Sale"])

# 004 + 005: deterministic seeds on customer invoices.
n_cust = sum(1 for r in data["Customer"] if r["Customer Key"] != "0")
for r in data["Transaction"]:
    if r["Transaction Type Key"] != "1":
        continue
    k = int(r["Transaction Key"])
    if r["Payment Method Key"] == "0":
        r["Payment Method Key"] = str(1 + k % 3)
    if r["Customer Key"] == "0" and k % 20:
        r["Customer Key"] = r["Bill To Customer Key"] = str(1 + k % n_cust)
# 005 (2026-10-09 extension): same invoice, same customer in Sale and Movement;
# Order seeded on its own order ID.
inv = {r["WWI Invoice ID"]: r for r in data["Transaction"]
       if r["Transaction Type Key"] == "1" and r["Customer Key"] != "0"}
for t in ("Sale", "Movement"):
    for r in data[t]:
        if r["Customer Key"] == "0" and r["WWI Invoice ID"] in inv:
            r["Customer Key"] = inv[r["WWI Invoice ID"]]["Customer Key"]
            if t == "Sale":
                r["Bill To Customer Key"] = inv[r["WWI Invoice ID"]]["Bill To Customer Key"]
for r in data["Order"]:
    o = int(r["WWI Order ID"])
    if r["Customer Key"] == "0" and o % 20:
        r["Customer Key"] = str(1 + o % n_cust)

# 006: shift fact dates and closed SCD bounds; rebuild the Date dimension.
for t, cols in FACT_DATES.items():
    for r in data[t]:
        for c in cols:
            if r[c]:
                r[c] = (date.fromisoformat(r[c]) + delta).isoformat()
for t in COLS:
    if "Valid To" not in COLS[t]:
        continue
    for r in data[t]:
        if not r["Valid To"].startswith("9999-12-31"):
            for c in ("Valid From", "Valid To"):
                r[c] = (datetime.fromisoformat(r[c]) + delta).isoformat(sep=" ")

data["Date"] = []
d, end = date(2013, 1, 1) + delta, date(2016, 12, 31) + delta
while d <= end:
    fy = d.year + (d.month >= 11)
    mon, short = d.strftime("%B"), d.strftime("%b")
    data["Date"].append(dict(zip(COLS["Date"], [
        d.isoformat(), d.day, d.day, mon, short, d.month, f"CY{d.year}-{short}", d.year, f"CY{d.year}",
        (d.month + 1) % 12 + 1, f"FY{fy}-{short}", fy, f"FY{fy}", d.isocalendar()[1]])))
    d += timedelta(days=1)

for t, rows in data.items():
    with open(OUT / f"{NAMES[t]}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([c.lower().replace(" ", "_") for c in COLS[t]])
        w.writerows([r[c] for c in COLS[t]] for r in rows)
    print(f"{NAMES[t]}: {len(rows)}")
print("delta days:", delta.days, "| sale max:", max(r["Invoice Date Key"] for r in data["Sale"]))
