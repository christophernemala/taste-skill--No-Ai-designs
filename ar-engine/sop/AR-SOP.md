# Accounts Receivable — Standard Operating Procedures

End-to-end order-to-cash SOPs for the monthly AR cycle. The aging, forecast,
statement and reminder steps are automated by this engine; the rest are the
manual workflows that surround it. Every workflow lists its owner, inputs,
steps and outputs so it can be handed to a new team member as-is.

**Governing principles**

1. **Age off contract terms, never system due dates.** Where terms were never
   configured in the ERP, the system due date equals the invoice date and the
   whole aging collapses into the oldest bucket. Due Date = Invoice Date +
   contract terms, always.
2. **Intercompany never mixes with external AR.** IC balances are reported on
   their own tab and excluded from every KPI, bucket and forecast.
3. **Nothing assumed passes silently.** Every derived or assumed payment term
   is flagged, counted and disclosed on the pack's integrity panel.
4. **A pack that does not reconcile is not issued.** The runner hard-stops if
   buckets or forecast do not tie to open AR.
5. **No automated outbound email to customers.** Reminders are generated as
   drafts for human review and sending. See "Policy guardrails" below.

---

## Workflow 1 — Monthly AR Aging (automated)

**Owner:** AR Analyst · **When:** Working day 2 after close
**Inputs:** current-month A/R Aging Detail extract; prior-month workbook (terms master)
**Automation:** `python3 run_month_end.py`

1. Export the A/R Aging Detail (SO/Project ID) report from the ERP as of
   month-end and place it in `data/`.
2. Place the prior month's issued workbook in `data/` — it is the payment
   terms master (terms are cumulative knowledge; losing this file means
   rebuilding 250+ customer terms from scratch).
3. Update `AS_OF` in `config.py` and run the pipeline.
4. Review the tie-out output. All hard checks must PASS. The soft check
   (external AR within ~20% of prior month) failing usually means the
   intercompany exclusion or the extract itself is wrong — investigate
   before anything else.
5. Review the Terms Master tab: every ASSUMED or Derived row needs the
   contract chased and next month's file updated.
6. Review Exceptions section A (near-duplicate names) and section B
   (unapplied cash) before circulating.

**Outputs:** 10-tab Excel pack, interactive HTML dashboard.

### The four data traps (why steps 4–6 exist)

| Trap | Symptom | Handling |
|---|---|---|
| Intercompany in the extract | AR overstated several-fold vs prior month | Excluded by configured name patterns; reported on its own tab |
| System due date = invoice date | Current ≈ 0, everything in Over 120 | Due date recomputed from contract terms |
| Terms live only in last month's file | New file has no terms column | Prior workbook carried forward as terms master |
| Unapplied cash netting buckets | Negative buckets, understated aging | Listed separately in Exceptions section B |

---

## Workflow 2 — Collections (semi-automated)

**Owner:** Collections / Credit Control · **When:** Continuous; refreshed each pack

Priority is assigned automatically per customer from the over-60 balance:

| Priority | Trigger | Default action |
|---|---|---|
| P1 - Escalate | over-60 ≥ 1,000,000 | Escalate to CFO / legal review |
| P2 - Call this week | over-60 ≥ 250,000 | Collector call + statement |
| P3 - Email reminder | over-60 > 0 | Send reminder with SOA |
| P4 - Monitor | none | No action |

Escalation ladder by days past due:

| DPD tier | Action | Escalates when |
|---|---|---|
| 1–30 | Tier-1 reminder + statement (drafts auto-generated) | No response in 5 days |
| 31–60 | Tier-2 follow-up + phone call | No payment date agreed |
| 61–90 | Tier-3 formal demand, credit-hold warning | No payment in 10 business days |
| 91+ | Tier-4 final notice; credit hold; legal review | Per credit committee |

Process: work the reminder drafts in `output/reminders/` top-down from
`_summary.txt` (sorted worst-first). Personalise, attach the matching
statement PDF, send from the AR mailbox, and log the contact in the
collections log (customer, date, method, response, next action, owner).
Payment plans require AR-manager approval and a written internal record.

---

## Workflow 3 — Cash Application

**Owner:** Cash Application / AR Accountant · **When:** Daily; zero unapplied at close

Application sequence: exact match → remittance-advice match → oldest-first
(FIFO) → suspense (maximum 5 business days). Categories and resolutions:

| Category | Resolution |
|---|---|
| Unapplied receipt (customer known) | Match to open invoices; request remittance advice |
| Unidentified receipt | Investigate bank detail; suspense; escalate > 10 days |
| Short payment | Confirm dispute or deduction; debit note if invalid |
| Overpayment | Apply to oldest invoice or refund |
| Advance payment | Customer advance account; match when invoiced |

The engine surfaces every unmatched receipt and credit memo in Exceptions
section B with the customer's net position. **Watch the near-duplicate names
in section A**: a payment on one customer master and the invoice on another
looks like an overdue invoice plus a mystery credit. Pair and reallocate —
never merge masters without confirming they are the same legal entity.

---

## Workflow 4 — Customer Credit Review

**Owner:** Credit Control · **When:** New customers; annually; on trigger events

Score payment history (35%), financial strength (25%), industry risk (15%),
tenure (10%), trade references (10%), dispute rate (5%); map the weighted
score to a grade:

| Grade | Score | Terms | Limit basis |
|---|---|---|---|
| A+ | 4.5–5.0 | Net 60 | ≤ 15% of customer revenue |
| A | 3.5–4.4 | Net 45 | ≤ 10% |
| B | 2.5–3.4 | Net 30 | ≤ 5% |
| C | 1.5–2.4 | Net 15 / prepay | ≤ 2% or secured |
| D | < 1.5 | Prepayment only | none |

Trigger events: risk category reaching Critical in the pack, DPD > 60 on a
material balance, credit-limit breach, adverse market news. Output is a
credit review memo with proposed terms/limit and an approver signature.
**All credit decisions require review by a qualified finance professional.**

---

## Workflow 5 — DSO Tracking

**Owner:** AR Manager · **When:** Monthly, from the issued pack

`DSO = (ending AR / period revenue) × days`. Track alongside Best AR Days
(current + 1–30 only) — the gap between them is the collection drag. When DSO
moves more than ~3 days, attribute it: revenue timing, term-mix shift, bucket
deterioration, dispute volume, or cash-application lag.

---

## Workflow 6 — Bad Debt Provision (IFRS 9 simplified / ASC 326)

**Owner:** AR Accountant → Controller → CFO sign-off · **When:** Quarterly minimum

Use a provision matrix on the pack's aging buckets: historical loss rate per
bucket, plus a forward-looking macro overlay, applied to the bucket balance.
The Over 120 bucket is the write-off assessment population — items there are
**not** written off automatically; write-offs need credit-committee approval.
Roll the provision forward each period (opening, P&L movement, write-offs,
recoveries, FX, closing). **Provision calculations require review by a
qualified finance professional before posting.**

---

## Workflow 7 — AR Reconciliation

**Owner:** AR Accountant · **When:** Every close, before the pack is issued

GL AR balance − subledger total = zero after listed reconciling items, each
with reference, amount and resolution date. The engine's tie-out that
external + intercompany equals the raw extract total is the subledger side
of this; the GL side is manual.

---

## Workflow 8 — Month-End AR Close Checklist

| # | Task | Owner | Day |
|---|---|---|---|
| 1 | Final invoicing run complete | Billing | D-1 |
| 2 | Subledger locked | AR Manager | D-1 |
| 3 | Cash application complete, zero unapplied | Cash App | D-1 |
| 4 | Extract pulled, engine run, tie-outs PASS | AR Analyst | D+2 |
| 5 | Terms Master reviewed (assumed/derived chased) | Credit Control | D+2 |
| 6 | Exceptions reviewed (names, unapplied, DQ) | AR Analyst | D+2 |
| 7 | GL-to-subledger reconciliation | AR Accountant | D+3 |
| 8 | Intercompany confirmed with counterparties | IC Team | D+3 |
| 9 | DSO calculated, variance explained | AR Manager | D+3 |
| 10 | Provision calculated and posted | AR Accountant | D+3 |
| 11 | CFO sign-off on provision / write-offs | CFO | D+4 |
| 12 | Pack issued (workbook + dashboard) | AR Analyst | D+4 |
| 13 | Statements + reminder drafts worked | Collections | D+5 |

---

## Policy guardrails

These are deliberate design constraints, not gaps:

1. **No auto-send.** The engine writes reminder *drafts* only. Automated
   outbound email to customers needs explicit sign-off from company
   management/IT before it is ever wired up — sending financial demands
   from an unsanctioned system creates real legal and reputational risk.
2. **No credentials, no API keys.** The pipeline runs entirely on local
   files. Nothing leaves the machine. (The dashboard loads Chart.js from a
   CDN when opened in a browser; for a fully offline environment, vendor
   the file locally.)
3. **Real AR data never enters version control.** `data/` and `output/` are
   git-ignored. Only the code and synthetic sample data generator are
   committed.
4. **Human judgement stays visible.** Collector overrides live in dedicated
   columns next to the deterministic baseline — never blended into it.
5. **Approvals stay human.** Credit decisions, write-offs, provisions and
   payment plans require named approvers per the workflows above.
