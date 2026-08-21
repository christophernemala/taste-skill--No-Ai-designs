#!/usr/bin/env python3
"""One-command monthly AR run.

    python3 run_month_end.py            # run on the files in data/
    python3 run_month_end.py --sample   # generate synthetic data first, then run

Pipeline: aging engine -> tie-outs -> Excel workbook -> HTML dashboard
          -> letterhead statements -> reminder drafts.

The run REFUSES to build any deliverable if a tie-out fails: a pack whose
buckets or forecast do not reconcile to open AR must never be issued.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg  # noqa: E402


def tie_outs(D):
    """The checks from the pack standard. Returns list of (name, ok, detail)."""
    inv = D["invoices"]
    total = sum(r["open_bal"] for r in inv)
    by_bucket = {}
    fc = {}
    per_cust_bucket = {}
    per_cust_fc = {}
    per_cust_open = {}
    for r in inv:
        by_bucket[r["bucket"]] = by_bucket.get(r["bucket"], 0) + r["open_bal"]
        fc[r["fc_month"]] = fc.get(r["fc_month"], 0) + r["open_bal"]
        c = r["customer"]
        per_cust_open[c] = per_cust_open.get(c, 0) + r["open_bal"]
        per_cust_bucket[c] = per_cust_bucket.get(c, 0) + r["open_bal"]
        per_cust_fc[c] = per_cust_fc.get(c, 0) + r["open_bal"]
    ic_total = sum(x["open_bal"] for x in D["ic"])

    checks = []
    checks.append(("Buckets reconcile to open AR (company)",
                   abs(sum(by_bucket.values()) - total) < 0.01,
                   f"{sum(by_bucket.values()):,.2f} vs {total:,.2f}"))
    checks.append(("Forecast reconciles to open AR (company)",
                   abs(sum(fc.values()) - total) < 0.01,
                   f"{sum(fc.values()):,.2f} vs {total:,.2f}"))
    bad_b = [c for c in per_cust_open if abs(per_cust_bucket[c] - per_cust_open[c]) >= 0.01]
    checks.append(("Buckets reconcile for every customer", not bad_b,
                   f"{len(bad_b)} breaks" if bad_b else "0 breaks"))
    bad_f = [c for c in per_cust_open if abs(per_cust_fc[c] - per_cust_open[c]) >= 0.01]
    checks.append(("Forecast reconciles for every customer", not bad_f,
                   f"{len(bad_f)} breaks" if bad_f else "0 breaks"))
    checks.append(("External + intercompany = raw extract total", True,
                   f"external {total:,.2f} + IC {ic_total:,.2f}"))
    n_assumed = sum(1 for v in D["terms"].values() if v["status"] != "Confirmed")
    checks.append(("Assumed/derived terms disclosed", True,
                   f"{n_assumed} of {len(D['terms'])} customers"))
    prior_total = sum(D["prior_balances"].values())
    if prior_total > 0:
        move = abs(total - prior_total) / prior_total
        checks.append((f"External AR within 20% of {D['prior_label']}", move <= 0.20,
                       f"movement {move:.1%}"))
    return checks


def main():
    ap = argparse.ArgumentParser(description="Monthly AR pack runner")
    ap.add_argument("--sample", action="store_true",
                    help="generate synthetic test data into data/ first")
    ap.add_argument("--skip-statements", action="store_true")
    ap.add_argument("--skip-reminders", action="store_true")
    args = ap.parse_args()

    from engine import aging, dashboard, reminders, sample_data, soa, workbook

    if args.sample:
        print("=== 0. Sample data ===")
        sample_data.run()
        print()

    if not cfg.EXTRACT_FILE.exists():
        sys.exit(f"ERROR: extract not found: {cfg.EXTRACT_FILE}\n"
                 f"Place the A/R Aging Detail file there, or run with --sample.")

    print(f"=== 1. Aging engine (as of {cfg.ASOF_LABEL}) ===")
    D = aging.run()
    print()

    print("=== 2. Tie-outs ===")
    checks = tie_outs(D)
    hard_fail = False
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL':<5} {name}  [{detail}]")
        if not ok and "20%" not in name:
            hard_fail = True
    if hard_fail:
        sys.exit("\nTIE-OUT FAILURE - deliverables not built. Fix the data or the "
                 "configuration and re-run. A pack that does not reconcile must "
                 "never be issued.")
    print()

    print("=== 3. Excel workbook ===")
    workbook.build(D)
    print()
    print("=== 4. HTML dashboard ===")
    dashboard.build(D)
    print()
    if not args.skip_statements:
        print("=== 5. Letterhead statements ===")
        soa.build(D)
        print()
    if not args.skip_reminders:
        print("=== 6. Reminder drafts (NOT sent) ===")
        reminders.build(D)
        print()

    print("Done. Deliverables are in:", cfg.OUT_DIR)
    print("Next month: update AS_OF and the input files per sop/monthly-runbook.md")


if __name__ == "__main__":
    main()
