"""Standalone dark interactive HTML dashboard, built from the engine JSON.

Slicers (customer search, entity, transaction type, terms status, terms days,
aging-bucket and risk chips, invoice-date timeline), KPI cards, seven charts,
sortable customer and invoice tables. Everything recalculates client-side from
the current selection. Chart.js from CDN, data embedded inline, no server.
"""
import json
from collections import defaultdict

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
import config as cfg


def build(D=None):
    if D is None:
        D = json.load(open(cfg.ENGINE_JSON))
    BUCK = D["buckets"]
    TER = D["terms"]
    ML = D["month_labels"]
    OUT = cfg.OUT_DIR / f"AR Aging Dashboard - {D['asof_label']}.html"

    def entity(doc):
        d = doc or ""
        for pat, name in cfg.ENTITY_PATTERNS.items():
            if pat in d:
                return name
        return cfg.ENTITY_DEFAULT

    cust_open = defaultdict(float)
    cust_old = defaultdict(int)
    c_b = defaultdict(lambda: [0.0] * 6)
    for r in D["invoices"]:
        cust_open[r["customer"]] += r["open_bal"]
        cust_old[r["customer"]] = max(cust_old[r["customer"]], r["age"])
        c_b[r["customer"]][BUCK.index(r["bucket"])] += r["open_bal"]

    def risk_cat(c):
        o = cust_open[c]
        b = c_b[c]
        if o <= 0:
            return "Credit Balance"
        p = (b[3] + b[4] + b[5]) / o
        if p >= 0.75 or cust_old[c] > 365:
            return "Critical"
        if p >= 0.40 or cust_old[c] > 180:
            return "High"
        if p >= 0.15 or cust_old[c] > 90:
            return "Medium"
        return "Low"

    rows = []
    for r in D["invoices"]:
        rows.append({
            "c": r["customer"], "t": r["txn_type"], "d": r["doc_no"], "so": r["so"],
            "p": r["project"], "id": r["txn_date"], "dd": r["due"], "a": r["age"],
            "v": round(r["open_bal"], 2), "b": r["bucket"], "tm": r["terms"],
            "ts": ("Confirmed" if TER[r["customer"]]["status"] == "Confirmed"
                   else ("Derived" if TER[r["customer"]]["status"].startswith("Derived") else "Assumed")),
            "e": entity(r["doc_no"]), "rk": risk_cat(r["customer"]),
            "fm": r["fc_month"], "fw": r["fc_week"] or 0,
        })

    ic_total = sum(x["open_bal"] for x in D["ic"])
    ic_accounts = len({x["customer"] for x in D["ic"]})
    prior_total = sum(D["prior_balances"].values())
    payload = {
        "rows": rows, "buckets": BUCK,
        "priorTotal": round(prior_total, 2), "icTotal": round(ic_total, 2),
        "icAccounts": ic_accounts,
        "priorBal": {k: round(v, 2) for k, v in D["prior_balances"].items()},
        "nearPairs": D["near_pairs"], "dupGroups": D["dup_groups"],
        "ml": ML, "priorLabel": D["prior_label"], "cur": D["currency"],
        "company": D["company"], "asof": D["asof_label"],
    }

    html = _TEMPLATE.replace("__PAYLOAD__", json.dumps(payload))
    OUT.write_text(html, encoding="utf-8")
    print("Saved:", OUT)
    print("rows embedded:", len(rows))
    return OUT


_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AR Aging Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#070d16; --panel:#0e1826; --panel2:#142236; --line:#1e304a; --txt:#e6eef7; --mut:#7f98b3;
  --acc:#00d1c1; --gold:#e5b83b; --red:#ff5f56; --amb:#ffa726; --grn:#37d67a; --blu:#54a0ff;
}
body{background:var(--bg);color:var(--txt);font:14px/1.45 'Segoe UI',system-ui,-apple-system,sans-serif;
 padding:18px;background-image:radial-gradient(1100px 600px at 12% -10%,#12263f 0%,transparent 60%),
 radial-gradient(900px 500px at 90% 0%,#0d2b2a 0%,transparent 55%)}
.wrap{max-width:1780px;margin:0 auto}
header{text-align:center;padding:20px 14px 22px;border:1px solid var(--line);border-radius:16px;
 background:linear-gradient(160deg,#0f1c2e,#0a1421);margin-bottom:16px}
header h1{font-size:26px;font-weight:800;letter-spacing:.5px}
header h2{font-size:15px;font-weight:700;color:var(--acc);margin-top:6px;letter-spacing:2.5px}
header p{color:var(--mut);font-size:12.5px;margin-top:8px}
.badge{display:inline-block;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:700;
 border:1px solid var(--acc);color:var(--acc);margin:0 4px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 14px;text-align:center;
 position:relative;overflow:hidden;transition:.2s}
.kpi:hover{transform:translateY(-3px);border-color:var(--acc)}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--k,var(--acc))}
.kpi .l{font-size:10.5px;letter-spacing:1.3px;color:var(--mut);font-weight:700;text-transform:uppercase}
.kpi .v{font-size:25px;font-weight:800;margin:8px 0 4px;color:var(--k,var(--acc));font-variant-numeric:tabular-nums}
.kpi .s{font-size:11px;color:var(--mut)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px}
.panel h3{font-size:12px;letter-spacing:2px;color:var(--acc);font-weight:800;margin-bottom:13px;
 text-transform:uppercase;text-align:center}
.slicers{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:14px}
.sl label{display:block;font-size:10.5px;letter-spacing:1.2px;color:var(--mut);font-weight:700;
 margin-bottom:6px;text-transform:uppercase;text-align:center}
select,input[type=text]{width:100%;background:var(--panel2);color:var(--txt);border:1px solid var(--line);
 border-radius:9px;padding:9px 10px;font-size:12.5px;text-align:center;font-family:inherit}
select:focus,input:focus{outline:none;border-color:var(--acc)}
select[multiple]{height:112px;text-align:left;padding:6px}
select[multiple] option{padding:4px 7px;border-radius:5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-top:8px}
.chip{padding:5px 12px;border-radius:18px;border:1px solid var(--line);background:var(--panel2);
 font-size:11.5px;font-weight:700;cursor:pointer;user-select:none;transition:.15s}
.chip:hover{border-color:var(--acc)}
.chip.on{background:var(--acc);color:#04202c;border-color:var(--acc)}
.tl{margin-top:6px}
.tl .rng{display:flex;align-items:center;gap:12px}
input[type=range]{flex:1;accent-color:var(--acc);height:5px}
.tlab{font-size:12px;font-weight:700;color:var(--acc);min-width:104px;text-align:center;
 background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:5px 6px}
.grid2{display:grid;grid-template-columns:1.35fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
canvas{max-height:290px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:var(--panel2);color:var(--acc);font-size:10.5px;letter-spacing:.8px;font-weight:800;
 padding:10px 7px;text-align:center;text-transform:uppercase;position:sticky;top:0;cursor:pointer;
 border-bottom:2px solid var(--acc);white-space:nowrap}
th:hover{color:#fff}
td{padding:8px 7px;text-align:center;border-bottom:1px solid #16283e;font-variant-numeric:tabular-nums}
tbody tr:nth-child(even){background:#0b1524}
tbody tr:hover{background:#16293f}
.tw{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:11px}
.l{text-align:left!important}
.neg{color:var(--red);font-weight:700}
.pos{font-weight:700}
.tag{padding:2.5px 9px;border-radius:12px;font-size:10.5px;font-weight:800;display:inline-block;white-space:nowrap}
.t-Critical{background:#3a1114;color:#ff8b84;border:1px solid #7a2b2b}
.t-High{background:#3a2710;color:#ffbe5c;border:1px solid #7a5a1f}
.t-Medium{background:#2b3110;color:#d6e05c;border:1px solid #5e6a1f}
.t-Low{background:#0f2f1f;color:#5ce09a;border:1px solid #1f6a45}
.t-CreditBalance{background:#10283a;color:#7fc9ff;border:1px solid #23557a}
.t-Confirmed{background:#0f2f1f;color:#5ce09a;border:1px solid #1f6a45}
.t-Derived{background:#3a2710;color:#ffbe5c;border:1px solid #7a5a1f}
.t-Assumed{background:#3a1114;color:#ff8b84;border:1px solid #7a2b2b}
.bar{height:7px;border-radius:4px;background:#16283e;overflow:hidden;margin-top:4px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--blu))}
.foot{text-align:center;color:var(--mut);font-size:11.5px;padding:16px 0 6px;line-height:1.9}
.btn{padding:8px 16px;border-radius:9px;border:1px solid var(--acc);background:transparent;color:var(--acc);
 font-weight:800;font-size:11.5px;cursor:pointer;letter-spacing:1px}
.btn:hover{background:var(--acc);color:#04202c}
.note{font-size:11.5px;color:var(--mut);text-align:center;margin-top:9px}
.warn{border-left:3px solid var(--amb);background:#1d1608;padding:10px 13px;border-radius:8px;
 font-size:12px;margin-top:10px;color:#ffd79a}
@media(max-width:1180px){.grid2,.grid3{grid-template-columns:1fr}}
</style></head><body><div class="wrap">

<header>
  <h1 id="hCompany"></h1>
  <h2>ACCOUNTS RECEIVABLE AGING &amp; COLLECTION DASHBOARD</h2>
  <p id="hSub"></p>
  <div style="margin-top:10px">
    <span class="badge">INTERCOMPANY EXCLUDED</span>
    <span class="badge" id="bTerms"></span>
    <span class="badge" id="bRows"></span>
  </div>
</header>

<div class="kpis" id="kpis"></div>

<div class="panel">
  <h3>Slicers &amp; Timeline</h3>
  <div class="slicers">
    <div class="sl"><label>Customer search</label><input type="text" id="fSearch" placeholder="type any part of the name..."></div>
    <div class="sl"><label>Customer</label><select id="fCust"><option value="">All customers</option></select></div>
    <div class="sl"><label>Entity</label><select id="fEnt" multiple></select></div>
    <div class="sl"><label>Transaction type</label><select id="fType" multiple></select></div>
    <div class="sl"><label>Terms status</label><select id="fTs" multiple></select></div>
    <div class="sl"><label>Payment terms (days)</label><select id="fTm" multiple></select></div>
  </div>
  <div style="margin-top:15px">
    <label style="display:block;font-size:10.5px;letter-spacing:1.2px;color:var(--mut);font-weight:700;margin-bottom:7px;text-transform:uppercase;text-align:center">Aging bucket</label>
    <div class="chips" id="cBucket"></div>
  </div>
  <div style="margin-top:14px">
    <label style="display:block;font-size:10.5px;letter-spacing:1.2px;color:var(--mut);font-weight:700;margin-bottom:7px;text-transform:uppercase;text-align:center">Risk category</label>
    <div class="chips" id="cRisk"></div>
  </div>
  <div class="tl" style="margin-top:16px">
    <label style="display:block;font-size:10.5px;letter-spacing:1.2px;color:var(--mut);font-weight:700;margin-bottom:7px;text-transform:uppercase;text-align:center">Timeline &mdash; invoice date range</label>
    <div class="rng">
      <span class="tlab" id="lFrom"></span>
      <input type="range" id="rFrom" min="0" max="100" value="0">
      <input type="range" id="rTo" min="0" max="100" value="100">
      <span class="tlab" id="lTo"></span>
    </div>
  </div>
  <div style="text-align:center;margin-top:15px"><button class="btn" id="reset">RESET ALL SLICERS</button></div>
  <div class="note" id="filterNote"></div>
</div>

<div class="grid2">
  <div class="panel"><h3>AR by aging bucket</h3><canvas id="chBucket"></canvas></div>
  <div class="panel"><h3>Aging mix</h3><canvas id="chMix"></canvas></div>
</div>

<div class="grid2">
  <div class="panel"><h3>Top 15 customers by open AR</h3><canvas id="chTop"></canvas></div>
  <div class="panel"><h3>Collection forecast &mdash; weekly &amp; monthly</h3><canvas id="chFc"></canvas></div>
</div>

<div class="grid3">
  <div class="panel"><h3>Exposure by entity</h3><canvas id="chEnt"></canvas></div>
  <div class="panel"><h3>Risk concentration</h3><canvas id="chRisk"></canvas></div>
  <div class="panel"><h3>Terms data quality</h3><canvas id="chTerms"></canvas></div>
</div>

<div class="panel">
  <h3>Customer summary <span style="color:var(--mut);font-weight:600;letter-spacing:0">(click any header to sort)</span></h3>
  <div class="tw"><table id="tCust"><thead><tr>
    <th data-k="c" class="l">Customer</th><th data-k="tm">Terms</th><th data-k="ts">Terms Status</th>
    <th data-k="open">Open AR</th><th data-k="cur">Current</th><th data-k="pd">Past Due</th>
    <th data-k="o90">Over 90</th><th data-k="pct">Overdue %</th><th data-k="old">Oldest (d)</th>
    <th data-k="n">Docs</th><th data-k="neg">Unapplied</th><th data-k="rk">Risk</th>
    <th data-k="mom">MoM</th></tr></thead><tbody></tbody></table></div>
</div>

<div class="panel">
  <h3>Invoice detail <span style="color:var(--mut);font-weight:600;letter-spacing:0">(first 400 rows of current selection)</span></h3>
  <div class="tw"><table id="tInv"><thead><tr>
    <th data-k="c" class="l">Customer</th><th data-k="t">Type</th><th data-k="d">Document No.</th>
    <th data-k="so">Sales Order</th><th data-k="p">Project ID</th><th data-k="id">Invoice Date</th>
    <th data-k="tm">Terms</th><th data-k="dd">Due Date</th><th data-k="a">Age (d)</th>
    <th data-k="v">Open Balance</th><th data-k="b">Bucket</th><th data-k="fm">Forecast</th>
    </tr></thead><tbody></tbody></table></div>
</div>

<div class="panel">
  <h3>Exceptions &mdash; similar customer names &amp; unapplied cash</h3>
  <div id="exBox"></div>
</div>

<div class="foot" id="foot"></div>
</div>

<script>
const DATA = __PAYLOAD__;
const R = DATA.rows, BUCK = DATA.buckets, ML = DATA.ml;
const fmt = n => (n<0?'(':'')+Math.abs(Math.round(n)).toLocaleString('en-US')+(n<0?')':'');
const pct = n => (n*100).toFixed(1)+'%';
const C = {acc:'#00d1c1',gold:'#e5b83b',red:'#ff5f56',amb:'#ffa726',grn:'#37d67a',blu:'#54a0ff',
           mut:'#7f98b3',line:'#1e304a',pur:'#a55eea',pnk:'#ff6b9d'};
const BCOL = [C.grn,C.blu,C.acc,C.gold,C.amb,C.red];
const HAS_CHART = typeof Chart !== 'undefined';
if(HAS_CHART){
  Chart.defaults.color=C.mut; Chart.defaults.borderColor=C.line;
  Chart.defaults.font.family="'Segoe UI',system-ui,sans-serif"; Chart.defaults.font.size=11;
}else{
  document.querySelectorAll('canvas').forEach(cv=>{
    cv.insertAdjacentHTML('afterend','<div class="note">Charts unavailable (Chart.js CDN not reachable) - KPIs and tables below are unaffected.</div>');
  });
}

document.getElementById('hCompany').textContent=DATA.company.toUpperCase();
document.getElementById('hSub').innerHTML='As of <b>'+DATA.asof+'</b> &nbsp;|&nbsp; Currency <b>'+DATA.cur+
  '</b> &nbsp;|&nbsp; Aging driven by contract payment terms, not the system due date';
document.getElementById('bTerms').textContent='TERMS CARRIED FORWARD FROM '+DATA.priorLabel.toUpperCase();
document.getElementById('foot').innerHTML=
  'Source: A/R Aging Detail extract as of '+DATA.asof+' &mdash; intercompany balances excluded.<br>'+
  'Due Date = Invoice Date + contract payment terms. Age = '+DATA.asof+' less Due Date, floored at zero.<br>'+
  'Figures in '+DATA.cur+'.';

const dates = [...new Set(R.map(r=>r.id).filter(Boolean))].sort();
const S = {search:'',cust:'',ent:[],type:[],ts:[],tm:[],bucket:[],risk:[],from:0,to:dates.length-1};

function uniq(k){return [...new Set(R.map(r=>r[k]))].filter(v=>v!==''&&v!=null).sort((a,b)=>
  (typeof a==='number')?a-b:String(a).localeCompare(String(b)));}
function fillMulti(id,vals){const s=document.getElementById(id);
  s.innerHTML=vals.map(v=>`<option value="${v}">${v}</option>`).join('');}
fillMulti('fEnt',uniq('e')); fillMulti('fType',uniq('t'));
fillMulti('fTs',['Confirmed','Derived','Assumed']); fillMulti('fTm',uniq('tm'));
document.getElementById('fCust').innerHTML='<option value="">All customers</option>'+
  uniq('c').map(v=>`<option value="${v.replace(/"/g,'&quot;')}">${v}</option>`).join('');
document.getElementById('cBucket').innerHTML=BUCK.map(b=>`<div class="chip" data-v="${b}">${b}</div>`).join('');
document.getElementById('cRisk').innerHTML=['Critical','High','Medium','Low','Credit Balance']
  .map(b=>`<div class="chip" data-v="${b}">${b}</div>`).join('');
const rf=document.getElementById('rFrom'), rt=document.getElementById('rTo');
rf.max=rt.max=dates.length-1; rt.value=dates.length-1;

function filtered(){
  const f=dates[S.from], t=dates[S.to], q=S.search.toLowerCase();
  return R.filter(r=>
    (!q || r.c.toLowerCase().includes(q) || (r.d||'').toLowerCase().includes(q) || (r.so||'').toLowerCase().includes(q)) &&
    (!S.cust || r.c===S.cust) &&
    (!S.ent.length || S.ent.includes(r.e)) &&
    (!S.type.length || S.type.includes(r.t)) &&
    (!S.ts.length || S.ts.includes(r.ts)) &&
    (!S.tm.length || S.tm.includes(String(r.tm))) &&
    (!S.bucket.length || S.bucket.includes(r.b)) &&
    (!S.risk.length || S.risk.includes(r.rk)) &&
    (!r.id || (r.id>=f && r.id<=t)));
}
const CH={};
function chart(id,cfg){ if(!HAS_CHART) return; if(CH[id]) CH[id].destroy(); CH[id]=new Chart(document.getElementById(id),cfg); }

function render(){
  const F=filtered();
  const tot=F.reduce((a,r)=>a+r.v,0);
  const bs=BUCK.map(b=>F.filter(r=>r.b===b).reduce((a,r)=>a+r.v,0));
  const cur=bs[0], pd=tot-cur, o90=bs[4]+bs[5], o60=bs[3]+bs[4]+bs[5];
  const negs=F.filter(r=>r.v<0), neg=negs.reduce((a,r)=>a+r.v,0);
  const nC=new Set(F.map(r=>r.c)).size;
  document.getElementById('bRows').textContent=F.length.toLocaleString()+' DOCUMENTS IN VIEW';

  const kp=[
    ['Total Open AR',fmt(tot),C.acc,nC+' customers / '+F.length.toLocaleString()+' documents'],
    ['Current (not due)',fmt(cur),C.grn,tot?pct(cur/tot)+' of selection':'-'],
    ['Total Past Due',fmt(pd),C.amb,tot?pct(pd/tot)+' of selection':'-'],
    ['Over 60 Days',fmt(o60),C.gold,tot?pct(o60/tot)+' of selection':'-'],
    ['Over 90 Days',fmt(o90),C.red,'provision review population'],
    ['Unapplied Cr / Cash',fmt(neg),C.pur,negs.length+' documents to allocate'],
    ['MoM Movement',fmt(tot-DATA.priorTotal),C.blu,'vs '+DATA.priorLabel+' '+DATA.cur+' '+fmt(DATA.priorTotal)],
    ['Intercompany Excluded',fmt(DATA.icTotal),C.pnk,DATA.icAccounts+' accounts, not in any KPI'],
  ];
  document.getElementById('kpis').innerHTML=kp.map(k=>
    `<div class="kpi" style="--k:${k[2]}"><div class="l">${k[0]}</div><div class="v">${k[1]}</div><div class="s">${k[3]}</div></div>`).join('');

  document.getElementById('filterNote').textContent =
    `Showing ${F.length.toLocaleString()} of ${R.length.toLocaleString()} documents  |  invoice dates ${dates[S.from]} to ${dates[S.to]}  |  ${DATA.cur} ${fmt(tot)}`;

  chart('chBucket',{type:'bar',data:{labels:BUCK,datasets:[{data:bs,backgroundColor:BCOL,borderRadius:6}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>DATA.cur+' '+fmt(c.raw)}}},
    scales:{y:{ticks:{callback:v=>fmt(v)},grid:{color:'#16283e'}},x:{grid:{display:false}}}}});

  chart('chMix',{type:'doughnut',data:{labels:BUCK,datasets:[{data:bs.map(Math.abs),backgroundColor:BCOL,borderColor:'#0e1826',borderWidth:2}]},
    options:{cutout:'58%',plugins:{legend:{position:'bottom',labels:{boxWidth:11,padding:9,font:{size:10.5}}},
    tooltip:{callbacks:{label:c=>c.label+': '+DATA.cur+' '+fmt(c.raw)}}}}});

  const byC={}; F.forEach(r=>byC[r.c]=(byC[r.c]||0)+r.v);
  const top=Object.entries(byC).sort((a,b)=>b[1]-a[1]).slice(0,15);
  chart('chTop',{type:'bar',data:{labels:top.map(t=>t[0].length>34?t[0].slice(0,34)+'...':t[0]),
    datasets:[{data:top.map(t=>t[1]),backgroundColor:C.acc,borderRadius:5}]},
    options:{indexAxis:'y',plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>DATA.cur+' '+fmt(c.raw)}}},
    scales:{x:{ticks:{callback:v=>fmt(v)},grid:{color:'#16283e'}},y:{grid:{display:false},ticks:{font:{size:9.5}}}}}});

  const fv=[1,2,3,4].map(w=>F.filter(r=>r.fm==='M1'&&r.fw===w).reduce((a,r)=>a+r.v,0))
    .concat(['M2','M3','Beyond'].map(m=>F.filter(r=>r.fm===m).reduce((a,r)=>a+r.v,0)));
  const fl=[ML.M1+' W1',ML.M1+' W2',ML.M1+' W3',ML.M1+' W4',ML.M2,ML.M3,ML.Beyond];
  chart('chFc',{type:'bar',data:{labels:fl,
    datasets:[{type:'bar',label:'Expected receipts',data:fv,backgroundColor:[C.grn,C.grn,C.grn,C.grn,C.blu,C.gold,C.red],borderRadius:5},
              {type:'line',label:'Cumulative',data:fv.map((_,i)=>fv.slice(0,i+1).reduce((a,b)=>a+b,0)),
               borderColor:C.acc,backgroundColor:'transparent',tension:.3,pointRadius:3,yAxisID:'y1'}]},
    options:{plugins:{legend:{labels:{boxWidth:11,font:{size:10.5}}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+DATA.cur+' '+fmt(c.raw)}}},
    scales:{y:{ticks:{callback:v=>fmt(v)},grid:{color:'#16283e'}},
            y1:{position:'right',ticks:{callback:v=>fmt(v)},grid:{display:false}},x:{grid:{display:false}}}}});

  const ents=[...new Set(F.map(r=>r.e))];
  chart('chEnt',{type:'polarArea',data:{labels:ents,datasets:[{data:ents.map(e=>Math.abs(F.filter(r=>r.e===e).reduce((a,r)=>a+r.v,0))),
    backgroundColor:[C.acc+'cc',C.blu+'cc',C.gold+'cc',C.pur+'cc']}]},
    options:{plugins:{legend:{position:'bottom',labels:{boxWidth:11,font:{size:10.5}}},
    tooltip:{callbacks:{label:c=>c.label+': '+DATA.cur+' '+fmt(c.raw)}}},scales:{r:{grid:{color:'#16283e'},ticks:{display:false}}}}});

  const rks=['Critical','High','Medium','Low','Credit Balance'];
  chart('chRisk',{type:'bar',data:{labels:rks,datasets:[{data:rks.map(k=>F.filter(r=>r.rk===k).reduce((a,r)=>a+r.v,0)),
    backgroundColor:[C.red,C.amb,C.gold,C.grn,C.blu],borderRadius:5}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>DATA.cur+' '+fmt(c.raw)}}},
    scales:{y:{ticks:{callback:v=>fmt(v)},grid:{color:'#16283e'}},x:{grid:{display:false},ticks:{font:{size:9.5}}}}}});

  const tss=['Confirmed','Derived','Assumed'];
  chart('chTerms',{type:'doughnut',data:{labels:tss.map(t=>t+' terms'),datasets:[{
    data:tss.map(t=>Math.abs(F.filter(r=>r.ts===t).reduce((a,r)=>a+r.v,0))),
    backgroundColor:[C.grn,C.amb,C.red],borderColor:'#0e1826',borderWidth:2}]},
    options:{cutout:'55%',plugins:{legend:{position:'bottom',labels:{boxWidth:11,font:{size:10.5}}},
    tooltip:{callbacks:{label:c=>c.label+': '+DATA.cur+' '+fmt(c.raw)}}}}});

  const agg={};
  F.forEach(r=>{
    const a=agg[r.c]||(agg[r.c]={c:r.c,tm:r.tm,ts:r.ts,rk:r.rk,open:0,cur:0,pd:0,o90:0,old:0,n:0,neg:0});
    a.open+=r.v; a.n++; if(r.b==='Current')a.cur+=r.v; else a.pd+=r.v;
    if(r.b==='91-120'||r.b==='Over 120')a.o90+=r.v;
    a.old=Math.max(a.old,r.a); if(r.v<0)a.neg+=r.v;
  });
  let cl=Object.values(agg).map(a=>({...a,pct:a.open?a.pd/a.open:0,
    mom:(DATA.priorBal[a.c]!==undefined)?a.open-DATA.priorBal[a.c]:null}));
  cl.sort((a,b)=>b.open-a.open);
  window._cl=cl;
  drawCust(cl);

  let il=[...F].sort((a,b)=>b.v-a.v);
  window._il=il;
  drawInv(il);

  const pairs=[];
  DATA.dupGroups.forEach(g=>{for(let i=0;i<g.length;i++)for(let j=i+1;j<g.length;j++)pairs.push([g[i],g[j],1,'Identical after removing legal suffix']);});
  DATA.nearPairs.forEach(p=>pairs.push([p[0],p[1],p[2],'Near-identical name']));
  const bal={}; R.forEach(r=>bal[r.c]=(bal[r.c]||0)+r.v);
  const negByC={}; R.filter(r=>r.v<0).forEach(r=>negByC[r.c]=(negByC[r.c]||0)+r.v);
  let h='<table><thead><tr><th class="l">Account A</th><th>Balance A</th><th class="l">Account B</th><th>Balance B</th><th>Similarity</th><th class="l">Match type</th><th class="l">Recommended action</th></tr></thead><tbody>';
  pairs.forEach(p=>{
    const risky=(negByC[p[0]]||negByC[p[1]]);
    h+=`<tr><td class="l">${p[0]}</td><td class="${(bal[p[0]]||0)<0?'neg':''}">${fmt(bal[p[0]]||0)}</td>`+
       `<td class="l">${p[1]}</td><td class="${(bal[p[1]]||0)<0?'neg':''}">${fmt(bal[p[1]]||0)}</td>`+
       `<td>${pct(p[2])}</td><td class="l">${p[3]}</td><td class="l">${risky?
         'Payment or credit likely booked to the wrong account &mdash; reallocate and net off':
         'Confirm these are separate legal entities; if not, merge in the system'}</td></tr>`;
  });
  h+='</tbody></table>';
  const totNeg=R.filter(r=>r.v<0).reduce((a,r)=>a+r.v,0);
  h+=`<div class="warn"><b>Unapplied cash &amp; credit memos:</b> ${R.filter(r=>r.v<0).length} documents totalling ${DATA.cur} ${fmt(totNeg)} are sitting unmatched against invoices at close. These depress the aging buckets they fall into. Full listing is on the <b>Exceptions &amp; Mismatches</b> tab of the Excel workbook, section B.</div>`;
  document.getElementById('exBox').innerHTML=h;
}

function drawCust(cl){
  document.querySelector('#tCust tbody').innerHTML=cl.map(a=>
    `<tr><td class="l">${a.c}</td><td>${a.tm}</td><td><span class="tag t-${a.ts}">${a.ts}</span></td>
     <td class="${a.open<0?'neg':'pos'}">${fmt(a.open)}</td><td>${fmt(a.cur)}</td>
     <td class="${a.pd<0?'neg':''}">${fmt(a.pd)}</td><td class="${a.o90<0?'neg':''}">${fmt(a.o90)}</td>
     <td>${pct(a.pct)}<div class="bar"><i style="width:${Math.min(100,Math.max(0,a.pct*100))}%"></i></div></td>
     <td>${a.old}</td><td>${a.n}</td><td class="${a.neg<0?'neg':''}">${a.neg?fmt(a.neg):'-'}</td>
     <td><span class="tag t-${a.rk.replace(' ','')}">${a.rk}</span></td>
     <td class="${a.mom<0?'neg':''}">${a.mom===null?'new':fmt(a.mom)}</td></tr>`).join('');
}
function drawInv(il){
  document.querySelector('#tInv tbody').innerHTML=il.slice(0,400).map(r=>
    `<tr><td class="l">${r.c}</td><td>${r.t}</td><td>${r.d||'-'}</td><td>${r.so||'-'}</td>
     <td>${r.p||'-'}</td><td>${r.id||'-'}</td><td>${r.tm}</td><td>${r.dd||'-'}</td><td>${r.a}</td>
     <td class="${r.v<0?'neg':'pos'}">${fmt(r.v)}</td><td>${r.b}</td>
     <td>${ML[r.fm]||r.fm}${r.fw?' W'+r.fw:''}</td></tr>`).join('');
}
function sortable(tid,store,draw){
  let dir={};
  document.querySelectorAll('#'+tid+' th').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; dir[k]=!dir[k];
    const arr=[...window[store]].sort((a,b)=>{
      const x=a[k],y=b[k];
      const r=(typeof x==='number'&&typeof y==='number')?x-y:String(x??'').localeCompare(String(y??''));
      return dir[k]?r:-r;});
    draw(arr);});
}
sortable('tCust','_cl',drawCust); sortable('tInv','_il',drawInv);

function ms(id,key){document.getElementById(id).onchange=e=>{
  S[key]=[...e.target.selectedOptions].map(o=>o.value); render();};}
ms('fEnt','ent'); ms('fType','type'); ms('fTs','ts'); ms('fTm','tm');
document.getElementById('fCust').onchange=e=>{S.cust=e.target.value;render();};
let t0; document.getElementById('fSearch').oninput=e=>{clearTimeout(t0);
  t0=setTimeout(()=>{S.search=e.target.value;render();},220);};
function chips(id,key){document.querySelectorAll('#'+id+' .chip').forEach(c=>c.onclick=()=>{
  c.classList.toggle('on');
  S[key]=[...document.querySelectorAll('#'+id+' .chip.on')].map(x=>x.dataset.v); render();});}
chips('cBucket','bucket'); chips('cRisk','risk');
function tl(){S.from=Math.min(+rf.value,+rt.value); S.to=Math.max(+rf.value,+rt.value);
  document.getElementById('lFrom').textContent=dates[S.from];
  document.getElementById('lTo').textContent=dates[S.to]; render();}
rf.oninput=tl; rt.oninput=tl;
document.getElementById('reset').onclick=()=>{
  Object.assign(S,{search:'',cust:'',ent:[],type:[],ts:[],tm:[],bucket:[],risk:[],from:0,to:dates.length-1});
  document.getElementById('fSearch').value=''; document.getElementById('fCust').value='';
  ['fEnt','fType','fTs','fTm'].forEach(i=>[...document.getElementById(i).options].forEach(o=>o.selected=false));
  document.querySelectorAll('.chip.on').forEach(c=>c.classList.remove('on'));
  rf.value=0; rt.value=dates.length-1; tl();};
document.getElementById('lFrom').textContent=dates[0];
document.getElementById('lTo').textContent=dates[dates.length-1];
render();
</script></body></html>"""


if __name__ == "__main__":
    build()
