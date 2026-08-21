# Monthly Runbook — AR Pack

The 15-minute checklist for producing one month's pack. For the full
procedures and rationale, see [AR-SOP.md](AR-SOP.md).

## 1. Collect inputs (2 files)

| File | Goes to | Notes |
|---|---|---|
| A/R Aging Detail SO/Project ID export (as of month-end) | `data/ARAgingDetailSOProjectID.xlsx` | Headers on row 7, data from row 8 — the raw ERP export, untouched |
| Last month's issued workbook | `data/prior_month.xlsx` | This is the **terms master**. Sheet `SOA`: customer col 1, terms col 7, balance col 10 |

## 2. Point the config at the new month

Edit `config.py`:

```python
AS_OF = dt.date(2026, 8, 31)   # the new month-end
```

Nothing else changes month to month.

## 3. Run

```bash
python3 run_month_end.py
```

First time on a new machine: `pip install -r requirements.txt`.
To rehearse without real data: `python3 run_month_end.py --sample`.

## 4. Review before issuing (do not skip)

- [ ] All hard tie-outs PASS (the run stops on failure — if it stopped, fix the data, don't force it)
- [ ] Soft check: external AR within ~20% of prior month — if it fails, check the intercompany exclusion **first**
- [ ] Terms Master tab: chase every ASSUMED / Derived row's contract
- [ ] Exceptions section A: near-duplicate names — reallocate wrongly-booked payments, never merge masters blindly
- [ ] Exceptions section B: unapplied cash — hand to cash application
- [ ] Dashboard opens and renders in a browser

## 5. Issue and work the outputs

| Output | Goes to |
|---|---|
| `AR Aging Report - <date>.xlsx` | Management circulation |
| `AR Aging Dashboard - <date>.html` | Management / self-serve slicing |
| `output/statements/` | Print to PDF, attach to reminders |
| `output/reminders/` | Collections: review, personalise, **send manually** from the AR mailbox, worst-first per `_summary.txt` |

## 6. Close the loop for next month

- Save the issued workbook where next month's run can reach it — it becomes
  the new terms master.
- Any newly confirmed contract terms: they're already in the issued workbook's
  Terms Master tab, so carrying the file forward carries the knowledge forward.
