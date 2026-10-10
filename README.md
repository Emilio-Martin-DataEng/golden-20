# golden-20

Is your AI dashboard right? 20 business questions with answers proven two independent ways.

## Result

Claude (Opus 5.5) via claude.ai and the BigQuery connector, on the raw tables, 2026-10-09: **20 / 20**. See [results/](results/2026-10-09-claude-opus-5.5.md).

The same method on a client's call-out data, three models: [I gave Claude Dashboards a 17-question exam](https://www.factsmith.co.za/insights/claude-dashboards-golden-questions/).

## Method

- Each golden answer is one query on a Kimball star (`wwi`) and an independent query on OLTP-shaped raw tables (`wwi_raw`). It counts only if both agree.
- The raw tables keep the traps of the real source: tax-inclusive extended price, orders that are not revenue, mixed customer transactions, and NULL customers.

## Quick start

Uses a free BigQuery sandbox. You need Python 3.10+, the gcloud SDK and a project.

1. Build the star CSVs: `python prep_wwi_bq.py data out/wwi`
2. Fold them into the raw tables: `python prep_wwi_raw.py out/wwi out/wwi_raw`
3. Create both datasets and load every CSV.

   bash:

   ```bash
   P=your-project
   bq --project_id=$P mk --dataset wwi
   bq --project_id=$P mk --dataset wwi_raw
   for d in wwi wwi_raw; do
     for f in out/$d/*.csv; do
       bq --project_id=$P load --autodetect --source_format=CSV --skip_leading_rows=1 --replace $d.$(basename $f .csv) $f
     done
   done
   ```

   PowerShell:

   ```powershell
   $P = "your-project"
   bq "--project_id=$P" mk --dataset wwi
   bq "--project_id=$P" mk --dataset wwi_raw
   foreach ($d in "wwi", "wwi_raw") {
     Get-ChildItem "out/$d/*.csv" | ForEach-Object {
       bq "--project_id=$P" load --autodetect --source_format=CSV --skip_leading_rows=1 --replace "$d.$($_.BaseName)" $_.FullName
     }
   }
   ```

4. Compute the golden answers: `python golden20.py out/golden20.csv your-project`. Every row should say `raw_agrees` yes.
5. Check them against the committed answers: `git diff --no-index golden20.csv out/golden20.csv` should print nothing.

## Test your own tool

- Give it `wwi_raw` only.
- Ask the 20 questions verbatim, with no definitions.
- Record its first answer in `answers.csv` (header `qid,answer,note`). Put any alternatives it offered in the note column. Write two-part answers as `label | number`.
- Run `python score.py golden20.csv answers.csv`. It prints a markdown scorecard and exits 0 only if every answer matches.

## Known data caveats

From Claude's own run:

- 2025 starts on 11 May, so every "2025" answer covers a partial year.
- There is a single customer category.
- The bill-to on invoices disagrees with the customer master.
- Open invoices are dated on the anchor day.
- Some payments cover invoices dated before the data starts.

## Data

A derivative of Microsoft's Wide World Importers (MIT), see `data/LICENSE-WWI.txt`. `prep_wwi_bq.py` assigns payment methods and customers to invoices that WWI left unassigned (deterministically) and shifts every date so the data ends on the anchor (default 2026-10-09). The questions are written for that anchor.

---

Want this on your own numbers? FactSmith: https://www.factsmith.co.za

MIT licence, see [LICENSE](LICENSE).
