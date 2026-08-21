"""Collection reminder email DRAFTS, one per overdue customer.

This module deliberately does NOT send anything. It writes plain-text draft
files into output/reminders/ for a human to review, personalise, and send
from the company mailbox. Automated outbound email to customers requires
explicit company sign-off — see sop/AR-SOP.md, section "Policy guardrails".

Tier is chosen from the customer's worst material overdue bucket, following
the collections escalation ladder:

  Tier 1 (0-30 past due)   — gentle reminder + statement
  Tier 2 (31-60)           — firm follow-up, call to agree a date
  Tier 3 (61-90)           — formal demand, escalation warning
  Tier 4 (91+)             — final notice before credit hold / legal review

Each draft names the open documents, amounts and due dates so the recipient
can act without asking for a breakdown.
"""
import datetime as dt
import json
import re
from collections import defaultdict

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
import config as cfg

MATERIALITY = 1000  # ignore overdue balances below this (report currency)


def _slug(name):
    return re.sub(r"[^\w\-]+", "_", name).strip("_")[:60]


def _tier(buckets):
    """Worst overdue bucket holding a material balance -> tier 1-4, or 0."""
    if buckets[4] + buckets[5] >= MATERIALITY:
        return 4
    if buckets[3] >= MATERIALITY:
        return 3
    if buckets[2] >= MATERIALITY:
        return 2
    if buckets[1] >= MATERIALITY:
        return 1
    return 0


def _doc_lines(docs, cur):
    lines = []
    for x in sorted(docs, key=lambda d: d["due"] or "9999"):
        if x["open_bal"] <= 0 or x["age"] <= 0:
            continue
        due = dt.date.fromisoformat(x["due"]).strftime("%d-%b-%Y") if x["due"] else "-"
        lines.append(f"  {x['doc_no'] or '(no ref)':<26} due {due}   "
                     f"{x['age']:>4} days overdue   {cur} {x['open_bal']:>14,.2f}")
    return "\n".join(lines)


def _body(tier, cust, overdue, total, cur, docs, asof_label, contact_email, company):
    doc_block = _doc_lines(docs, cur)
    common = (f"Dear Sir / Madam,\n\n")
    close = (f"\nIf any of these invoices have already been settled or are under dispute, "
             f"please share the payment reference or dispute details and we will update our "
             f"records immediately.\n\n"
             f"Kind regards,\n{cfg.PREPARED_BY}\n{company}\n{contact_email}\n")

    if tier == 1:
        subject = f"Payment reminder - {cur} {overdue:,.2f} now due - {company}"
        body = (common +
                f"This is a friendly reminder that the following invoice(s) on your account "
                f"have fallen due as of {asof_label}:\n\n{doc_block}\n\n"
                f"Total now due: {cur} {overdue:,.2f} "
                f"(total outstanding including items not yet due: {cur} {total:,.2f}).\n\n"
                f"A statement of account is attached for your reconciliation. We would "
                f"appreciate settlement at your earliest convenience." + close)
    elif tier == 2:
        subject = f"Second reminder - overdue balance {cur} {overdue:,.2f} - {company}"
        body = (common +
                f"Further to our previous reminder, the following invoice(s) remain unpaid "
                f"as of {asof_label}:\n\n{doc_block}\n\n"
                f"Total overdue: {cur} {overdue:,.2f}.\n\n"
                f"Please confirm the expected payment date this week. Our collections team "
                f"will call to agree a settlement plan if payment is not already in process." + close)
    elif tier == 3:
        subject = f"Formal demand - overdue balance {cur} {overdue:,.2f} - {company}"
        body = (common +
                f"Despite previous reminders, the following invoice(s) remain unpaid and are "
                f"now more than 60 days past due as of {asof_label}:\n\n{doc_block}\n\n"
                f"Total overdue: {cur} {overdue:,.2f}.\n\n"
                f"We must ask for settlement, or a written payment plan, within 10 business "
                f"days of this notice. Failing that, the account will be escalated to senior "
                f"management and further credit may be placed on hold." + close)
    else:
        subject = f"FINAL NOTICE - overdue balance {cur} {overdue:,.2f} - {company}"
        body = (common +
                f"This is a final notice regarding the following invoice(s), which are more "
                f"than 90 days past due as of {asof_label}:\n\n{doc_block}\n\n"
                f"Total overdue: {cur} {overdue:,.2f}.\n\n"
                f"Unless payment or an agreed payment plan is received within 7 business days, "
                f"the account will be placed on credit hold and referred for legal review. We "
                f"would much prefer to resolve this amicably - please contact us without delay." + close)
    return subject, body


def build(D=None):
    if D is None:
        D = json.load(open(cfg.ENGINE_JSON))
    out_dir = cfg.OUT_DIR / "reminders"
    out_dir.mkdir(parents=True, exist_ok=True)
    CUR = D["currency"]
    BUCK = D["buckets"]

    by_cust = defaultdict(list)
    for r in D["invoices"]:
        by_cust[r["customer"]].append(r)

    written = []
    for cust, docs in sorted(by_cust.items()):
        buckets = [0.0] * 6
        for x in docs:
            buckets[BUCK.index(x["bucket"])] += x["open_bal"]
        total = sum(buckets)
        overdue = total - buckets[0]
        tier = _tier(buckets)
        if tier == 0 or overdue < MATERIALITY:
            continue
        subject, body = _body(tier, cust, overdue, total, CUR, docs,
                              D["asof_label"], cfg.LETTERHEAD["email"], D["company"])
        draft = (f"DRAFT - REVIEW BEFORE SENDING - NOT SENT AUTOMATICALLY\n"
                 f"{'=' * 60}\n"
                 f"To      : [{cust} - AR contact]\n"
                 f"From    : {cfg.LETTERHEAD['email']}\n"
                 f"Subject : {subject}\n"
                 f"Attach  : statements/SOA_{_slug(cust)}.html (print to PDF first)\n"
                 f"Tier    : {tier}\n"
                 f"{'=' * 60}\n\n{body}")
        fname = f"tier{tier}_{_slug(cust)}.txt"
        (out_dir / fname).write_text(draft, encoding="utf-8")
        written.append((tier, cust, overdue))

    # run summary for the collections log
    summary = ["Tier  Overdue " + CUR.rjust(14) + "  Customer",
               "-" * 60]
    for tier, cust, overdue in sorted(written, key=lambda x: (-x[0], -x[2])):
        summary.append(f"  {tier}   {overdue:>14,.2f}  {cust}")
    (out_dir / "_summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"Saved: {out_dir}  ({len(written)} reminder drafts + _summary.txt)")
    print("NOTE: drafts only - nothing is sent. Review, personalise, send from the company mailbox.")
    return out_dir


if __name__ == "__main__":
    build()
