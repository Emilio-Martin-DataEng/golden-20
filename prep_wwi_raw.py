"""Fold the BigQuery-ready Kimball CSVs (prep_wwi_bq.py output) back into an
OLTP-shaped `wwi_raw` dataset, modelled on the real WideWorldImporters Sales
schema. Same numbers, no star: the traps are the ones the real source has.

  - invoice_lines.extended_price INCLUDES tax (as in WWI OLTP).
  - orders/order_lines are demand, not revenue; not every order is invoiced.
  - customer_transactions mixes invoices, credit notes and (negative) payments.
  - invoices.customer_id is NULL where the Kimball side had Unknown.

Usage:
    python -I prep_wwi_raw.py <bq_csv_dir> <out_dir>
"""
import csv, sys
from pathlib import Path

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def read(name):
    with open(SRC / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, cols, rows):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"{name}: {len(rows)}")


def current(rows, id_col):
    """SCD2 dimension -> one row per business key (latest version)."""
    by_id = {}
    for r in sorted(rows, key=lambda r: r["valid_from"]):
        if r[id_col] != "0":
            by_id[r[id_col]] = r
    return by_id


cust_dim, item_dim, emp_dim = read("dim_customer"), read("dim_stock_item"), read("dim_employee")
cust = {r["customer_key"]: r["wwi_customer_id"] for r in cust_dim if r["customer_key"] != "0"}
item = {r["stock_item_key"]: r["wwi_stock_item_id"] for r in item_dim if r["stock_item_key"] != "0"}
emp = {r["employee_key"]: r["wwi_employee_id"] for r in emp_dim if r["employee_key"] != "0"}
ttype = {r["transaction_type_key"]: r["wwi_transaction_type_id"] for r in read("dim_transaction_type")}

cur = current(cust_dim, "wwi_customer_id")
bill_id = {r["customer"]: k for k, r in cur.items()}
write("customers", ["customer_id", "customer_name", "bill_to_customer_id", "customer_category", "buying_group",
                    "primary_contact", "postal_code"],
      [[k, r["customer"], bill_id.get(r["bill_to_customer"], k), r["category"], r["buying_group"],
        r["primary_contact"], r["postal_code"]] for k, r in cur.items()])

cur = current(item_dim, "wwi_stock_item_id")
write("stock_items", ["stock_item_id", "stock_item_name", "color", "brand", "size", "unit_package", "tax_rate",
                      "unit_price", "recommended_retail_price", "is_chiller_stock"],
      [[k, r["stock_item"], r["color"], r["brand"], r["size"], r["selling_package"], r["tax_rate"],
        r["unit_price"], r["recommended_retail_price"], r["is_chiller_stock"]] for k, r in cur.items()])

# WWI's DW carries two versions of type 13 (Contra, Customer Contra); keep the latest.
cur = current(read("dim_transaction_type"), "wwi_transaction_type_id")
write("transaction_types", ["transaction_type_id", "transaction_type_name"],
      [[k, r["transaction_type"]] for k, r in cur.items()])

cur = current(emp_dim, "wwi_employee_id")
write("people", ["person_id", "full_name", "preferred_name", "is_salesperson"],
      [[k, r["employee"], r["preferred_name"], r["is_salesperson"]] for k, r in cur.items()])

# Sales: Kimball line grain -> invoices header + invoice_lines.
invoices, lines = {}, []
for r in read("fact_sale"):
    inv = r["wwi_invoice_id"]
    invoices.setdefault(inv, [inv, cust.get(r["customer_key"], ""), cust.get(r["bill_to_customer_key"], ""),
                              emp.get(r["salesperson_key"], ""), r["invoice_date_key"], r["delivery_date_key"]])
    lines.append([r["sale_key"], inv, item.get(r["stock_item_key"], ""), r["description"], r["package"],
                  r["quantity"], r["unit_price"], r["tax_rate"], r["tax_amount"], r["profit"],
                  r["total_including_tax"]])
write("invoices", ["invoice_id", "customer_id", "bill_to_customer_id", "salesperson_person_id", "invoice_date",
                   "confirmed_delivery_date"], list(invoices.values()))
write("invoice_lines", ["invoice_line_id", "invoice_id", "stock_item_id", "description", "package", "quantity",
                        "unit_price", "tax_rate", "tax_amount", "line_profit", "extended_price"], lines)

orders, olines = {}, []
for r in read("fact_order"):
    o = r["wwi_order_id"]
    orders.setdefault(o, [o, cust.get(r["customer_key"], ""), emp.get(r["salesperson_key"], ""),
                          emp.get(r["picker_key"], ""), r["wwi_backorder_id"], r["order_date_key"]])
    olines.append([r["order_key"], o, item.get(r["stock_item_key"], ""), r["description"], r["package"],
                   r["quantity"], r["unit_price"], r["tax_rate"], r["picked_date_key"]])
write("orders", ["order_id", "customer_id", "salesperson_person_id", "picked_by_person_id", "backorder_order_id",
                 "order_date"], list(orders.values()))
write("order_lines", ["order_line_id", "order_id", "stock_item_id", "description", "package", "quantity",
                      "unit_price", "tax_rate", "picking_completed_when"], olines)

write("customer_transactions",
      ["customer_transaction_id", "customer_id", "transaction_type_id", "invoice_id", "transaction_date",
       "amount_excluding_tax", "tax_amount", "transaction_amount", "outstanding_balance", "is_finalized"],
      [[r["wwi_customer_transaction_id"], cust.get(r["customer_key"], ""), ttype[r["transaction_type_key"]],
        r["wwi_invoice_id"], r["date_key"], r["total_excluding_tax"], r["tax_amount"], r["total_including_tax"],
        r["outstanding_balance"], r["is_finalized"]]
       for r in read("fact_transaction") if r["wwi_customer_transaction_id"]])

# Self-check: raw revenue must reconcile to the Kimball fact.
kimball = round(sum(float(r["total_excluding_tax"]) for r in read("fact_sale")), 2)
raw = round(sum(float(l[10]) - float(l[8]) for l in lines), 2)
assert abs(kimball - raw) < 0.01, (kimball, raw)
print("revenue reconciles:", raw)
