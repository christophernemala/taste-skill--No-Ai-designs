# AR Engine — Monthly Receivables Pack

One command turns a raw ERP A/R Aging Detail export into the complete
month-end receivables pack:

- **10-tab formatted Excel workbook** — dashboard, aging summary,
  customer summary, collection forecast, invoice-level SOA, payment terms
  master, exceptions, intercompany, methodology, raw data
- **Interactive HTML dashboard** — slicers, KPI cards, seven charts,
  sortable tables; a single self-contained file, no server
- **Per-customer statements of account** on company letterhead, print-ready A4
- **Tiered collection reminder drafts** (drafts only — nothing is ever sent
  automatically)
- **3-month deterministic collection forecast**, weekly within month 1

No API keys, no external services, no credentials. Input files in, deliverables
out, entirely on your machine.

## Quickstart

```bash
pip install -r requirements.txt
python3 run_month_end.py --sample     # full rehearsal on synthetic data
```

Real month: drop the two input files into `data/`, set `AS_OF` in
`config.py`, run `python3 run_month_end.py`. Details in
[sop/monthly-runbook.md](sop/monthly-runbook.md).

## Why this exists

A consolidated ERP aging extract is not a clean aging file. This engine
handles the four traps that silently produce a wrong report:

1. **Intercompany hiding in the extract** — can dwarf external AR; excluded
   by configured name patterns and reported on its own auditable tab.
2. **System due dates that are not real due dates** — where terms were never
   configured, the ERP defaults due date to invoice date. Due dates are
   recomputed from contract terms.
3. **Terms that only exist in last month's workbook** — the prior file is the
   terms master; a four-level resolution hierarchy (exact → normalised →
   derived → assumed) is applied and every non-confirmed term is disclosed.
4. **Unapplied cash netting against buckets** — negative open balances are
   listed separately with the customer's net position, plus near-duplicate
   customer-name detection for payments booked to the wrong master.

The run **refuses to build deliverables if the tie-outs fail**: buckets and
forecast must reconcile to open AR for every customer.

## Layout

```
ar-engine/
├── config.py            # the only file that changes month to month
├── run_month_end.py     # one-command pipeline with hard tie-out gates
├── requirements.txt     # openpyxl — that's all
├── engine/
│   ├── aging.py         # core: parse, IC split, terms, buckets, forecast
│   ├── workbook.py      # 10-tab Excel builder
│   ├── dashboard.py     # standalone interactive HTML dashboard
│   ├── soa.py           # letterhead statements of account
│   ├── reminders.py     # tiered reminder email drafts (never auto-sent)
│   └── sample_data.py   # synthetic data reproducing all four traps
├── sop/
│   ├── AR-SOP.md        # complete order-to-cash SOPs (8 workflows)
│   └── monthly-runbook.md
├── data/                # inputs (git-ignored — real AR data never committed)
└── output/              # deliverables (git-ignored)
```

## Security & policy posture

- **Local-only.** No network calls at run time. (The dashboard references
  Chart.js from a CDN when opened in a browser; vendor it for offline use.)
- **Drafts, not sends.** Reminder emails are files a human reviews and sends.
  Wiring up automated sending requires management/IT sign-off first.
- **No real data in git.** `data/` and `output/` are ignored; the committed
  sample generator uses entirely fictional customers.
- **Judgement stays visible.** Collector forecast overrides sit beside the
  deterministic baseline in their own columns.

Before pointing this at production data or circulating statements externally,
fill in the letterhead placeholders in `config.py` and get the pack format
approved by your finance management.
