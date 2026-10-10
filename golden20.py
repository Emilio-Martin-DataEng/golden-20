"""20 golden questions for the Claude Dashboards test. Each has a Kimball query
(dataset wwi, the source of truth) and an independent query on wwi_raw; both
must agree before the answer counts as golden. Writes a CSV.

Usage: python golden20.py <out_csv> <gcp_project> [star_dataset=wwi] [raw_dataset=wwi_raw]
(needs bq on PATH)
"""
import csv, json, os, subprocess, sys

PROJECT = sys.argv[2]
STAR = sys.argv[3] if len(sys.argv) > 3 else "wwi"
RAW = sys.argv[4] if len(sys.argv) > 4 else "wwi_raw"
P = f"`{PROJECT}`"
K, R = f"{P}.{STAR}", f"{P}.{RAW}"
SEP26 = "BETWEEN '2026-09-01' AND '2026-09-30'"
SEP25 = "BETWEEN '2025-09-01' AND '2025-09-30'"
Y25 = "BETWEEN '2025-01-01' AND '2025-12-31'"
KS = f"{K}.fact_sale s"
RL = f"{R}.invoice_lines l JOIN {R}.invoices i USING (invoice_id)"
REV = "(l.extended_price - l.tax_amount)"

Q = [
    ("Q01", "What was revenue in September 2026?",
     "Invoiced, excluding tax.",
     f"SELECT ROUND(SUM(total_excluding_tax),2) FROM {KS} WHERE invoice_date_key {SEP26}",
     f"SELECT ROUND(SUM{REV},2) FROM {RL} WHERE invoice_date {SEP26}"),
    ("Q02", "What was revenue in 2025?",
     "Calendar year 2025, invoiced, excluding tax.",
     f"SELECT ROUND(SUM(total_excluding_tax),2) FROM {KS} WHERE invoice_date_key {Y25}",
     f"SELECT ROUND(SUM{REV},2) FROM {RL} WHERE invoice_date {Y25}"),
    ("Q03", "What was gross profit in September 2026?",
     "Sum of line profit on invoices.",
     f"SELECT ROUND(SUM(profit),2) FROM {KS} WHERE invoice_date_key {SEP26}",
     f"SELECT ROUND(SUM(l.line_profit),2) FROM {RL} WHERE invoice_date {SEP26}"),
    ("Q04", "What was our gross margin in 2025?",
     "Profit / revenue excluding tax, as a percentage.",
     f"SELECT ROUND(100*SUM(profit)/SUM(total_excluding_tax),2) FROM {KS} WHERE invoice_date_key {Y25}",
     f"SELECT ROUND(100*SUM(l.line_profit)/SUM{REV},2) FROM {RL} WHERE invoice_date {Y25}"),
    ("Q05", "How many invoices did we issue in September 2026?",
     "Distinct invoices.",
     f"SELECT COUNT(DISTINCT wwi_invoice_id) FROM {KS} WHERE invoice_date_key {SEP26}",
     f"SELECT COUNT(*) FROM {R}.invoices WHERE invoice_date {SEP26}"),
    ("Q06", "What was the average invoice value in September 2026?",
     "Revenue excluding tax / distinct invoices.",
     f"SELECT ROUND(SUM(total_excluding_tax)/COUNT(DISTINCT wwi_invoice_id),2) FROM {KS} WHERE invoice_date_key {SEP26}",
     f"SELECT ROUND(SUM{REV}/COUNT(DISTINCT invoice_id),2) FROM {RL} WHERE invoice_date {SEP26}"),
    ("Q07", "How many units did we sell in September 2026?",
     "Invoiced quantity.",
     f"SELECT SUM(quantity) FROM {KS} WHERE invoice_date_key {SEP26}",
     f"SELECT SUM(l.quantity) FROM {RL} WHERE invoice_date {SEP26}"),
    ("Q08", "Which product earned the most revenue in 2025?",
     "Stock item by revenue excluding tax.",
     f"SELECT CONCAT(d.stock_item,' | ',CAST(ROUND(SUM(s.total_excluding_tax),2) AS STRING)) FROM {KS} JOIN {K}.dim_stock_item d USING (stock_item_key) WHERE invoice_date_key {Y25} GROUP BY d.stock_item ORDER BY SUM(s.total_excluding_tax) DESC LIMIT 1",
     f"SELECT CONCAT(si.stock_item_name,' | ',CAST(ROUND(SUM{REV},2) AS STRING)) FROM {RL} JOIN {R}.stock_items si USING (stock_item_id) WHERE invoice_date {Y25} GROUP BY si.stock_item_name ORDER BY SUM{REV} DESC LIMIT 1"),
    ("Q09", "Which buying group brought in the most revenue in 2025?",
     "Named buying groups only; customers with no group ('N/A') are not a group.",
     f"SELECT CONCAT(c.buying_group,' | ',CAST(ROUND(SUM(s.total_excluding_tax),2) AS STRING)) FROM {KS} JOIN {K}.dim_customer c USING (customer_key) WHERE invoice_date_key {Y25} AND c.buying_group <> 'N/A' GROUP BY c.buying_group ORDER BY SUM(s.total_excluding_tax) DESC LIMIT 1",
     f"SELECT CONCAT(c.buying_group,' | ',CAST(ROUND(SUM{REV},2) AS STRING)) FROM {RL} JOIN {R}.customers c USING (customer_id) WHERE invoice_date {Y25} AND c.buying_group <> 'N/A' GROUP BY c.buying_group ORDER BY SUM{REV} DESC LIMIT 1"),
    ("Q10", "Which customer category brought in the most revenue in 2025?",
     "Customer category by revenue excluding tax; unknown customers excluded.",
     f"SELECT CONCAT(c.category,' | ',CAST(ROUND(SUM(s.total_excluding_tax),2) AS STRING)) FROM {KS} JOIN {K}.dim_customer c USING (customer_key) WHERE invoice_date_key {Y25} AND customer_key <> 0 GROUP BY c.category ORDER BY SUM(s.total_excluding_tax) DESC LIMIT 1",
     f"SELECT CONCAT(c.customer_category,' | ',CAST(ROUND(SUM{REV},2) AS STRING)) FROM {RL} JOIN {R}.customers c USING (customer_id) WHERE invoice_date {Y25} GROUP BY c.customer_category ORDER BY SUM{REV} DESC LIMIT 1"),
    ("Q11", "How many customers bought from us in September 2026?",
     "Distinct known customers (delivery customer) with an invoice.",
     f"SELECT COUNT(DISTINCT customer_key) FROM {KS} WHERE invoice_date_key {SEP26} AND customer_key <> 0",
     f"SELECT COUNT(DISTINCT customer_id) FROM {R}.invoices WHERE invoice_date {SEP26}"),
    ("Q12", "What was the value of orders placed in September 2026?",
     "Orders by order date, excluding tax. Orders, not invoices.",
     f"SELECT ROUND(SUM(total_excluding_tax),2) FROM {K}.fact_order WHERE order_date_key {SEP26}",
     f"SELECT ROUND(SUM(ol.quantity*ol.unit_price),2) FROM {R}.order_lines ol JOIN {R}.orders o USING (order_id) WHERE o.order_date {SEP26}"),
    ("Q13", "How many orders were placed in September 2026?",
     "Distinct orders by order date.",
     f"SELECT COUNT(DISTINCT wwi_order_id) FROM {K}.fact_order WHERE order_date_key {SEP26}",
     f"SELECT COUNT(*) FROM {R}.orders WHERE order_date {SEP26}"),
    ("Q14", "How many orders placed in September 2026 had to be backordered?",
     "Orders with a backorder raised against them.",
     f"SELECT COUNT(DISTINCT wwi_order_id) FROM {K}.fact_order WHERE order_date_key {SEP26} AND wwi_backorder_id IS NOT NULL",
     f"SELECT COUNT(*) FROM {R}.orders WHERE order_date {SEP26} AND backorder_order_id IS NOT NULL"),
    ("Q15", "How much did customers pay us in September 2026?",
     "Customer payments received, as a positive amount.",
     f"SELECT ROUND(-SUM(t.total_including_tax),2) FROM {K}.fact_transaction t JOIN {K}.dim_transaction_type tt USING (transaction_type_key) WHERE tt.transaction_type = 'Customer Payment Received' AND t.date_key {SEP26}",
     f"SELECT ROUND(-SUM(transaction_amount),2) FROM {R}.customer_transactions WHERE transaction_type_id = 3 AND transaction_date {SEP26}"),
    ("Q16", "How much do customers owe us right now?",
     "Sum of outstanding balance on customer transactions.",
     f"SELECT ROUND(SUM(t.outstanding_balance),2) FROM {K}.fact_transaction t WHERE t.wwi_customer_transaction_id IS NOT NULL",
     f"SELECT ROUND(SUM(outstanding_balance),2) FROM {R}.customer_transactions"),
    ("Q17", "Which customer owes us the most right now?",
     "Known customer with the largest outstanding balance.",
     f"SELECT CONCAT(c.customer,' | ',CAST(ROUND(SUM(t.outstanding_balance),2) AS STRING)) FROM {K}.fact_transaction t JOIN {K}.dim_customer c USING (customer_key) WHERE t.wwi_customer_transaction_id IS NOT NULL AND customer_key <> 0 GROUP BY c.customer ORDER BY SUM(t.outstanding_balance) DESC LIMIT 1",
     f"SELECT CONCAT(c.customer_name,' | ',CAST(ROUND(SUM(t.outstanding_balance),2) AS STRING)) FROM {R}.customer_transactions t JOIN {R}.customers c USING (customer_id) GROUP BY c.customer_name ORDER BY SUM(t.outstanding_balance) DESC LIMIT 1"),
    ("Q18", "Who was our top salesperson by revenue in 2025?",
     "Salesperson on the invoice, revenue excluding tax.",
     f"SELECT CONCAT(e.employee,' | ',CAST(ROUND(SUM(s.total_excluding_tax),2) AS STRING)) FROM {KS} JOIN {K}.dim_employee e ON e.employee_key = s.salesperson_key WHERE invoice_date_key {Y25} GROUP BY e.employee ORDER BY SUM(s.total_excluding_tax) DESC LIMIT 1",
     f"SELECT CONCAT(p.full_name,' | ',CAST(ROUND(SUM{REV},2) AS STRING)) FROM {RL} JOIN {R}.people p ON p.person_id = i.salesperson_person_id WHERE invoice_date {Y25} GROUP BY p.full_name ORDER BY SUM{REV} DESC LIMIT 1"),
    ("Q19", "How much did revenue grow in September 2026 compared with September 2025?",
     "Percentage change, revenue excluding tax.",
     f"SELECT ROUND(100*(SUM(IF(invoice_date_key {SEP26},total_excluding_tax,0))/SUM(IF(invoice_date_key {SEP25},total_excluding_tax,0))-1),2) FROM {KS}",
     f"SELECT ROUND(100*(SUM(IF(invoice_date {SEP26},{REV},0))/SUM(IF(invoice_date {SEP25},{REV},0))-1),2) FROM {RL}"),
    ("Q20", "Which month of 2025 had the highest revenue?",
     "Calendar month by invoice date, revenue excluding tax.",
     f"SELECT CONCAT(m,' | ',CAST(v AS STRING)) FROM (SELECT SUBSTR(CAST(invoice_date_key AS STRING),1,7) m, ROUND(SUM(total_excluding_tax),2) v FROM {KS} WHERE invoice_date_key {Y25} GROUP BY m ORDER BY v DESC LIMIT 1)",
     f"SELECT CONCAT(m,' | ',CAST(v AS STRING)) FROM (SELECT SUBSTR(CAST(invoice_date AS STRING),1,7) m, ROUND(SUM{REV},2) v FROM {RL} WHERE invoice_date {Y25} GROUP BY m ORDER BY v DESC LIMIT 1)"),
]


def run(sql):
    out = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--quiet", "--use_legacy_sql=false",
                          "--format=json", sql], capture_output=True, text=True, shell=(os.name == "nt"))
    if out.returncode:
        return "ERROR: " + (out.stdout + out.stderr).strip()[:200]
    rows = json.loads(out.stdout)
    s = str(next(iter(rows[0].values()))) if rows else "(no rows)"
    try: s = f"{float(s):.2f}".rstrip("0").rstrip(".")
    except ValueError: pass
    return s


rows = []
for qid, q, defn, ksql, rsql in Q:
    k, r = run(ksql), run(rsql)
    print(qid, k, "| raw:", r, flush=True)
    rows.append([qid, q, defn, k, "yes" if k == r else "NO: " + r])
with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["qid", "question", "definition", "golden", "raw_agrees"])
    w.writerows(rows)
