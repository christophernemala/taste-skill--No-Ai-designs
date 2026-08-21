"""Per-customer Statement of Account on company letterhead.

Generates one print-ready A4 HTML statement per external customer with a
positive open balance, plus an index page. Print to PDF from any browser
(Ctrl+P, A4, default margins) — the layout is tuned for that.

The letterhead block (address, TRN, bank details, logo) comes from
config.LETTERHEAD. Placeholders are printed as-is so an unfinished
letterhead is visible, not silently blank — replace them in config.py
before circulating statements externally.
"""
import base64
import datetime as dt
import html
import json
import re
from collections import defaultdict

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
import config as cfg

STYLE = """
*{box-sizing:border-box;margin:0;padding:0}
body{font:11pt/1.45 Georgia,'Times New Roman',serif;color:#1a2433;background:#fff}
.page{width:210mm;min-height:280mm;margin:0 auto;padding:16mm 18mm;position:relative}
.lh{display:flex;justify-content:space-between;align-items:flex-start;
 border-bottom:2.5pt solid #0B1F3A;padding-bottom:5mm;margin-bottom:7mm}
.lh .co{font-size:15pt;font-weight:bold;color:#0B1F3A;letter-spacing:.4pt}
.lh .addr{font-size:8.5pt;color:#4a5a70;margin-top:2mm;line-height:1.55}
.lh img{max-height:18mm;max-width:50mm}
h1{font-size:13pt;color:#0B1F3A;letter-spacing:2pt;text-transform:uppercase;
 text-align:center;margin:2mm 0 1mm}
.sub{text-align:center;font-size:9pt;color:#4a5a70;margin-bottom:6mm}
.meta{display:flex;justify-content:space-between;margin-bottom:6mm;font-size:9.5pt}
.meta .box{border:1pt solid #c9d3df;padding:3.5mm 5mm;width:48%}
.meta .box b{display:block;font-size:8pt;color:#00857f;text-transform:uppercase;
 letter-spacing:1pt;margin-bottom:1.5mm;font-family:Arial,sans-serif}
table{width:100%;border-collapse:collapse;font-size:8.6pt;font-family:Arial,sans-serif}
th{background:#0B1F3A;color:#fff;padding:2.6mm 2mm;text-align:center;font-size:7.6pt;
 letter-spacing:.5pt;text-transform:uppercase}
td{padding:2.2mm 2mm;border-bottom:.5pt solid #dde4ec;text-align:center;
 font-variant-numeric:tabular-nums}
td.l{text-align:left}
td.r{text-align:right}
tr.tot td{background:#eef2f7;font-weight:bold;border-top:1.5pt solid #0B1F3A;border-bottom:none}
.neg{color:#a33}
.aging{margin-top:7mm}
.aging h2{font-size:9pt;color:#0B1F3A;letter-spacing:1.5pt;text-transform:uppercase;
 margin-bottom:2.5mm;font-family:Arial,sans-serif}
.pay{margin-top:8mm;display:flex;justify-content:space-between;gap:6mm;font-size:8.8pt}
.pay .bank{border:1pt solid #c9d3df;padding:4mm 5mm;flex:1}
.pay .bank b{display:block;font-size:8pt;color:#00857f;text-transform:uppercase;
 letter-spacing:1pt;margin-bottom:2mm;font-family:Arial,sans-serif}
.pay .bank div{line-height:1.7}
.note{flex:1;color:#4a5a70;font-size:8.6pt;line-height:1.6;padding-top:1mm}
.foot{position:absolute;bottom:10mm;left:18mm;right:18mm;border-top:1pt solid #c9d3df;
 padding-top:2.5mm;font-size:7.6pt;color:#7a8aa0;text-align:center;font-family:Arial,sans-serif}
@media print{.page{margin:0;width:auto}.noprint{display:none}}
.noprint{background:#0B1F3A;color:#fff;padding:10px;text-align:center;font-family:Arial,sans-serif;
 font-size:12px}
.noprint a{color:#7fd9d4}
"""


def _slug(name):
    return re.sub(r"[^\w\-]+", "_", name).strip("_")[:60]


def _money(v):
    if v < 0:
        return f'<span class="neg">({abs(v):,.2f})</span>'
    return f"{v:,.2f}"


def _logo_tag():
    lf = cfg.LETTERHEAD.get("logo_file")
    if lf and _P(lf).exists():
        b64 = base64.b64encode(_P(lf).read_bytes()).decode()
        ext = _P(lf).suffix.lstrip(".") or "png"
        return f'<img src="data:image/{ext};base64,{b64}" alt="logo">'
    return ""


def build(D=None):
    if D is None:
        D = json.load(open(cfg.ENGINE_JSON))
    out_dir = cfg.OUT_DIR / "statements"
    out_dir.mkdir(parents=True, exist_ok=True)
    CUR = D["currency"]
    BUCK = D["buckets"]
    lh = cfg.LETTERHEAD

    by_cust = defaultdict(list)
    for r in D["invoices"]:
        by_cust[r["customer"]].append(r)

    head = f"""
<div class="lh">
  <div>
    <div class="co">{html.escape(D['company'])}</div>
    <div class="addr">{'<br>'.join(html.escape(a) for a in lh['address_lines'])}<br>
    Tel {html.escape(lh['phone'])} &nbsp;|&nbsp; {html.escape(lh['email'])} &nbsp;|&nbsp; TRN {html.escape(lh['trn'])}</div>
  </div>
  {_logo_tag()}
</div>"""

    bank = "".join(f"<div>{html.escape(b)}</div>" for b in lh["bank_details"])
    index_rows = []

    for cust in sorted(by_cust):
        docs = sorted(by_cust[cust], key=lambda x: (x["txn_date"] or "9999", x["doc_no"]))
        total = sum(x["open_bal"] for x in docs)
        if total <= 0:
            continue
        buckets = [0.0] * 6
        for x in docs:
            buckets[BUCK.index(x["bucket"])] += x["open_bal"]
        overdue = total - buckets[0]
        terms = D["terms"][cust]["terms"]

        body_rows = ""
        for x in docs:
            d = dt.date.fromisoformat(x["txn_date"]).strftime("%d-%b-%Y") if x["txn_date"] else "-"
            du = dt.date.fromisoformat(x["due"]).strftime("%d-%b-%Y") if x["due"] else "-"
            body_rows += (f"<tr><td class='l'>{html.escape(x['doc_no'] or '-')}</td>"
                          f"<td>{html.escape(x['txn_type'])}</td>"
                          f"<td class='l'>{html.escape(x['po_no'] or '-')}</td>"
                          f"<td>{d}</td><td>{du}</td><td>{x['age']}</td>"
                          f"<td>{html.escape(x['bucket'])}</td>"
                          f"<td class='r'>{_money(x['open_bal'])}</td></tr>")

        aging_cells_h = "".join(f"<th>{b}</th>" for b in BUCK) + "<th>Total</th>"
        aging_cells_v = "".join(f"<td class='r'>{_money(v)}</td>" for v in buckets) + \
                        f"<td class='r'><b>{_money(total)}</b></td>"

        page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>SOA - {html.escape(cust)}</title><style>{STYLE}</style></head><body>
<div class="noprint">Statement of Account &mdash; print to PDF with Ctrl+P (A4). <a href="index.html">Back to index</a></div>
<div class="page">
{head}
<h1>Statement of Account</h1>
<div class="sub">As of {D['asof_label']} &nbsp;|&nbsp; All amounts in {CUR}</div>
<div class="meta">
  <div class="box"><b>Customer</b>{html.escape(cust)}</div>
  <div class="box"><b>Summary</b>
    Payment terms: Net {terms} days<br>
    Open documents: {len(docs)}<br>
    Total outstanding: <b>{CUR} {total:,.2f}</b><br>
    Of which overdue: {CUR} {overdue:,.2f}</div>
</div>
<table>
<thead><tr><th>Document No.</th><th>Type</th><th>Your PO Ref.</th><th>Invoice Date</th>
<th>Due Date</th><th>Days Overdue</th><th>Aging</th><th>Amount ({CUR})</th></tr></thead>
<tbody>{body_rows}
<tr class="tot"><td class="l" colspan="7">TOTAL OUTSTANDING</td><td class="r">{_money(total)}</td></tr>
</tbody></table>
<div class="aging">
<h2>Aging Summary</h2>
<table><thead><tr>{aging_cells_h}</tr></thead><tbody><tr>{aging_cells_v}</tr></tbody></table>
</div>
<div class="pay">
  <div class="bank"><b>Payment Details</b>{bank}</div>
  <div class="note">Kindly arrange settlement of the overdue amounts at your earliest convenience,
  quoting the document numbers above with your remittance advice to {html.escape(lh['email'])}.
  If any invoice listed has already been paid or is under dispute, please share the payment
  reference or dispute details so our records can be updated.</div>
</div>
<div class="foot">{html.escape(D['company'])} &mdash; Statement of Account as of {D['asof_label']} &mdash;
generated by {html.escape(cfg.PREPARED_BY)}. This statement reflects open items in our ledger at the
date shown and is subject to reconciliation.</div>
</div></body></html>"""

        fname = f"SOA_{_slug(cust)}.html"
        (out_dir / fname).write_text(page, encoding="utf-8")
        index_rows.append((cust, total, overdue, len(docs), fname))

    # index page
    idx_rows = "".join(
        f"<tr><td class='l'><a href='{f}'>{html.escape(c)}</a></td>"
        f"<td class='r'>{_money(t)}</td><td class='r'>{_money(o)}</td><td>{n}</td></tr>"
        for c, t, o, n, f in sorted(index_rows, key=lambda x: -x[1]))
    idx = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Statements of Account - {D['asof_label']}</title><style>{STYLE}</style></head><body>
<div class="page">
{head}
<h1>Statements of Account &mdash; Index</h1>
<div class="sub">As of {D['asof_label']} &nbsp;|&nbsp; {len(index_rows)} customers with open balances &nbsp;|&nbsp; {CUR}</div>
<table><thead><tr><th>Customer</th><th>Total Outstanding</th><th>Overdue</th><th>Docs</th></tr></thead>
<tbody>{idx_rows}</tbody></table>
</div></body></html>"""
    (out_dir / "index.html").write_text(idx, encoding="utf-8")
    print(f"Saved: {out_dir}  ({len(index_rows)} statements + index.html)")
    return out_dir


if __name__ == "__main__":
    build()
