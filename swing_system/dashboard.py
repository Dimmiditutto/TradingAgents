"""
dashboard.py  —  MTF Swing System
Genera HTML standalone con:
  Tab SCAN     : segnali, filtri, distribuzione score
  Tab BACKTEST : 12 KPI, equity chart SVG, breakdown per evento/score/durata
  Tab POSIZIONI: tracker in-memory (no localStorage)
"""

from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def _c(sc):
    if sc >= 85: return "#00e676"
    if sc >= 75: return "#69f0ae"
    if sc >= 65: return "#ffee58"
    if sc >= 55: return "#ffa726"
    return "#ef9a9a"

def _badge(t, cls): return f'<span class="badge {cls}">{t}</span>'

def _dir_b(d):
    return _badge(f"▲ {d}" if d=="LONG" else f"▼ {d}", "bl" if d=="LONG" else "br")

def _evt_b(e):
    if not e: return _badge("—","bn")
    cls = {
        "CHoCH_UP": "bc-u",
        "CHoCH_DOWN": "bc-d",
        "BOS_UP": "bb-u",
        "BOS_DOWN": "bb-d",
        "TF": "bs-tf",
        "CP": "bs-cp",
        "MOM": "bs-mom",
        "MR": "bs-mr",
    }.get(e, "bn")
    return _badge(e.replace("_", " "), cls)

def _mb(v, c="#4fc3f7"):
    w = max(0, min(100, float(v or 0)))
    return f'<div class="mb"><div class="mbf" style="width:{w:.0f}%;background:{c}"></div><span class="mbl">{w:.0f}</span></div>'

def _f(v, d=2):
    try: return f"{float(v):.{d}f}"
    except: return "—"


# ── equity chart SVG ─────────────────────────────────────────────────────────

def _equity_svg(series, W=680, H=210):
    if not series or len(series) < 2:
        return '<p style="color:#4a5568;padding:20px">Nessun dato equity.</p>'
    vals  = [s["equity"] for s in series]
    dates = [s["date"]   for s in series]
    n     = len(vals)
    mn, mx = min(vals), max(vals)
    rng   = max(mx - mn, 0.01)
    PL, PR, PT, PB = 52, 16, 18, 30
    iw, ih = W-PL-PR, H-PT-PB

    def px(i): return PL + i/(max(n-1,1))*iw
    def py(v): return PT + (1-(v-mn)/rng)*ih

    pts  = " ".join(f"{px(i):.1f},{py(v):.1f}" for i,v in enumerate(vals))
    fill = f"{PL:.0f},{PT+ih:.0f} {pts} {px(n-1):.1f},{PT+ih:.0f}"
    lc   = "#00e676" if vals[-1] >= 100 else "#ff5252"
    fc   = "rgba(0,230,118,0.07)" if vals[-1] >= 100 else "rgba(255,82,82,0.07)"

    y_ax = "".join(
        f'<text x="{PL-5}" y="{py(mn+rng*k/3)+4:.0f}" text-anchor="end" font-size="9" fill="#555">{mn+rng*k/3:.1f}</text>'
        f'<line x1="{PL}" y1="{py(mn+rng*k/3):.0f}" x2="{PL+iw}" y2="{py(mn+rng*k/3):.0f}" stroke="#1c2535" stroke-width="0.5"/>'
        for k in range(4)
    )
    x_ax = "".join(
        f'<text x="{px(int(k*(n-1)/3)):.0f}" y="{H-6}" text-anchor="middle" font-size="9" fill="#555">{dates[int(k*(n-1)/3)][:7]}</text>'
        for k in range(4)
    )
    base = f'<line x1="{PL}" y1="{py(100):.1f}" x2="{PL+iw}" y2="{py(100):.1f}" stroke="#333" stroke-width="0.8" stroke-dasharray="4,3"/>'
    end_x, end_y = f"{px(n-1):.1f}", f"{py(vals[-1]):.1f}"

    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%">'
        + y_ax + x_ax + base
        + f'<polygon points="{fill}" fill="{fc}"/>'
        + f'<polyline points="{pts}" fill="none" stroke="{lc}" stroke-width="1.8"/>'
        + f'<circle cx="{end_x}" cy="{end_y}" r="4" fill="{lc}"/>'
        + f'<text x="{float(end_x)+7}" y="{float(end_y)+4:.0f}" font-size="10" fill="{lc}" font-weight="700">{vals[-1]:.2f}</text>'
        + '</svg>'
    )


# ── score distribution mini-chart ────────────────────────────────────────────

def _dist_svg(signals):
    buckets = [0]*5
    for s in signals:
        sc = float(s.get("score",0) or 0)
        i  = min(int((sc-50)//10), 4)
        if 0 <= i < 5: buckets[i] += 1
    mx   = max(buckets) or 1
    bw, gap, H = 48, 10, 88
    colors = ["#ef9a9a","#ffa726","#ffee58","#69f0ae","#00e676"]
    labels = ["50s","60s","70s","80s","90s"]
    bars   = []
    for i,(v,l,c) in enumerate(zip(buckets,labels,colors)):
        bh = max(int(v/mx*60), 2 if v else 0)
        x  = gap + i*(bw+gap)
        y  = H-24-bh
        bars += [
            f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{c}" opacity=".85" rx="3"/>',
            f'<text x="{x+bw//2}" y="{H-10}" text-anchor="middle" font-size="9" fill="#666">{l}</text>',
            f'<text x="{x+bw//2}" y="{y-3}" text-anchor="middle" font-size="9" fill="#ccc">{v or ""}</text>',
        ]
    tw = gap + 5*(bw+gap)
    return f'<svg viewBox="0 0 {tw} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{tw}px">{"".join(bars)}</svg>'


# ── signal row ────────────────────────────────────────────────────────────────

def _sig_row(s, rank):
    sc  = float(s.get("score",0) or 0)
    ep  = float(s.get("entry_price",0) or 0)
    sl_ = float(s.get("stop_loss",0) or 0)
    t1  = float(s.get("target1",0) or 0)
    rr  = float(s.get("risk_reward",0) or 0)
    di  = s.get("direction","")
    tk  = s.get("ticker","")
    wt  = str(s.get("weekly_trend","") or "")
    dt  = str(s.get("daily_trend","") or "")
    wt_short = wt[:3] if wt else "—"
    dt_short = dt[:3] if dt else "—"
    wc  = "var(--g)" if wt=="UPTREND" else ("var(--r)" if wt=="DOWNTREND" else "var(--mu)")
    dc  = "var(--g)" if dt=="UPTREND" else ("var(--r)" if dt=="DOWNTREND" else "var(--mu)")
    return f"""<tr class="sr" data-dir="{di}" data-sc="{sc:.0f}">
  <td class="rk">#{rank}</td><td class="tk">{tk}</td>
  <td>{_dir_b(di)}</td>
  <td class="sc" style="color:{_c(sc)}">{sc:.1f}</td>
  <td class="sb">{_mb(s.get("score_structure",0),"#7e57c2")}{_mb(s.get("score_trend",0),"#26c6da")}{_mb(s.get("score_momentum",0),"#ab47bc")}</td>
  <td>{_evt_b(s.get("structure_event",""))}</td>
  <td class="nu">{ep:.2f}</td>
  <td class="nu" style="color:var(--r)">{sl_:.2f}</td>
  <td class="nu" style="color:var(--g)">{t1:.2f}</td>
  <td class="nu" style="color:var(--y);font-weight:700">{rr:.2f}</td>
  <td class="nu">{_f(s.get("adx"),1)}</td>
  <td class="nu">{_f(s.get("rsi"),1)}</td>
  <td class="nu">{_f(s.get("volume_ratio"),1)}x</td>
  <td class="nu">{_f(s.get("atr_pct"),2)}%</td>
  <td style="text-align:center;font-size:11px"><span style="color:{wc}">{wt_short}</span><br><span style="color:{dc}">{dt_short}</span></td>
  <td><button class="btn-tr" onclick="addPos('{tk}','{di}',{ep:.4f},{sl_:.4f},{t1:.4f},{sc:.1f})">+Track</button></td>
</tr>"""


# ── kpi card ──────────────────────────────────────────────────────────────────

def _kpi(label, value, color="#fff", sub=""):
    return (f'<div class="kpi-card">'
            f'<div class="kpi-v" style="color:{color}">{value}</div>'
            f'<div class="kpi-l">{label}</div>'
            + (f'<div class="kpi-s">{sub}</div>' if sub else "")
            + '</div>')


# ── breakdown table ───────────────────────────────────────────────────────────

def _bdt(data, title):
    if not data: return ""
    rows = ""
    for k,v in sorted(data.items()):
        pnl = v.get("total_pnl_r",0)
        pc  = "color:var(--g)" if pnl>=0 else "color:var(--r)"
        rows += (f'<tr><td>{k or "—"}</td>'
                 f'<td class="nu">{v.get("count",0)}</td>'
                 f'<td class="nu" style="color:{_c(v.get("win_rate",0))}">{v.get("win_rate",0):.1f}%</td>'
                 f'<td class="nu">{v.get("avg_rr",0):+.2f}</td>'
                 f'<td class="nu" style="{pc}">{pnl:+.2f}R</td></tr>')
    return (f'<div class="bds"><div class="bdt">{title}</div>'
            f'<table class="btt"><thead><tr><th></th>'
            f'<th class="nu">n</th><th class="nu">WR</th><th class="nu">RR</th><th class="nu">PnL</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')


# ── backtest tab HTML ─────────────────────────────────────────────────────────

def _bt_tab(stats):
    if not stats or "error" in stats:
        msg = (stats or {}).get("error","Backtest non eseguito.")
        return (f'<p style="color:var(--mu);padding:32px 0">{msg}<br>'
                f'Esegui: <code>python screener.py backtest --synthetic</code></p>')

    s  = stats["summary"]
    eq = stats.get("equity_series",[])

    def sign_c(v): return "#00e676" if v>=0 else "#ff5252"
    def pf_c(v):
        if v>=1.5: return "#00e676"
        if v>=1.0: return "#ffee58"
        return "#ff5252"
    def sh_c(v):
        if v>=1.0: return "#00e676"
        if v>=0.5: return "#ffee58"
        return "#ff5252"

    kpis = [
        _kpi("Trade Totali",  str(s["total_trades"])),
        _kpi("Win Rate",      f"{s['win_rate_pct']:.1f}%",  _c(s["win_rate_pct"])),
        _kpi("Profit Factor", f"{s['profit_factor']:.2f}", pf_c(s["profit_factor"])),
        _kpi("Avg R/R",       f"{s['avg_rr']:+.2f}",       sign_c(s["avg_rr"])),
        _kpi("Total PnL",     f"{s['total_pnl_pct']:+.2f}%",sign_c(s["total_pnl_pct"]),
             f"{s['years_tested']:.1f} anni"),
        _kpi("CAGR",          f"{s['cagr_pct']:+.2f}%",    sign_c(s["cagr_pct"])),
        _kpi("Sharpe",        f"{s['sharpe']:.2f}",        sh_c(s["sharpe"])),
        _kpi("Sortino",       f"{s['sortino']:.2f}",       sh_c(s["sortino"]/1.5)),
        _kpi("Max Drawdown",  f"{s['max_drawdown_pct']:.2f}%","#ff5252"),
        _kpi("Avg Drawdown",  f"{s['avg_drawdown_pct']:.2f}%","#ffa726"),
        _kpi("Durata media",  f"{s['avg_hold_days']:.1f}g"),
        _kpi("Rischio/trade", f"{s['risk_per_trade']:.1f}%", sub="del capitale"),
    ]

    bd = (
        _bdt(stats.get("by_event",     {}), "Per evento strutturale") +
        _bdt(stats.get("by_direction", {}), "Per direzione") +
        _bdt(stats.get("by_score_bucket",{}), "Per score bucket") +
        _bdt(stats.get("by_duration",  {}), "Per durata hold") +
        _bdt(stats.get("by_exit_reason",{}), "Per exit reason")
    )

    return f"""
<div class="kpi-grid">{"".join(kpis)}</div>
<div class="card" style="margin-top:20px">
  <div class="bdt">Equity Curve — base 100, rischio {s['risk_per_trade']:.0f}%/trade</div>
  <div style="padding:6px 0">{_equity_svg(eq)}</div>
</div>
<div class="bd-grid" style="margin-top:18px">{bd}</div>
"""


# ── main generator ────────────────────────────────────────────────────────────

def generate_dashboard(signals, bt_stats=None, title="MTF Swing Screener"):
    ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n      = len(signals)
    n_l    = sum(1 for s in signals if s.get("direction")=="LONG")
    n_s    = n - n_l
    n_ch   = sum(1 for s in signals if "CHoCH" in (s.get("structure_event") or ""))
    n_bo   = sum(1 for s in signals if "BOS"   in (s.get("structure_event") or ""))
    avg_sc = sum(float(s.get("score",0) or 0) for s in signals)/max(n,1)
    avg_rr = sum(float(s.get("risk_reward",0) or 0) for s in signals)/max(n,1)

    rows    = "\n".join(_sig_row(s,i+1) for i,s in enumerate(signals[:60]))
    no_sig  = ('<tr><td colspan="16" style="text-align:center;color:var(--mu);padding:32px">'
               'Nessun segnale. Esegui: <code>python screener.py scan --synthetic</code>'
               '</td></tr>') if not rows.strip() else ""
    dsv     = _dist_svg(signals)
    bt_html = _bt_tab(bt_stats)

    CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;800&family=IBM+Plex+Mono:wght@300;400;600&display=swap');
:root{--bg:#07090e;--s1:#0d1117;--s2:#111922;--bd:#1c2535;
  --tx:#c9d1d9;--mu:#4a5568;
  --g:#00e676;--r:#ff5252;--y:#ffee58;--b:#40c4ff;--p:#ce93d8;
  --font:'IBM Plex Mono',monospace}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--tx);font-family:var(--font);font-size:13px}
code{background:var(--s2);padding:2px 6px;border-radius:3px;font-family:var(--font)}
.hdr{background:linear-gradient(135deg,#0d1117,#0f1820,#0d1117);
  border-bottom:1px solid var(--bd);padding:20px 28px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.hdr-t{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;color:#fff;letter-spacing:.04em}
.hdr-t span{color:var(--g)}
.hdr-s{font-size:10px;color:var(--mu);margin-top:3px}
.stat-bar{display:flex;gap:10px;flex-wrap:wrap;padding:12px 28px;border-bottom:1px solid var(--bd)}
.stat{background:var(--s2);border:1px solid var(--bd);border-radius:5px;
  padding:8px 14px;text-align:center;min-width:80px}
.stat-v{font-size:18px;font-weight:700;color:#fff}
.stat-l{font-size:9px;color:var(--mu);margin-top:1px;text-transform:uppercase;letter-spacing:.12em}
.tabs{display:flex;border-bottom:1px solid var(--bd);padding:0 28px}
.tab{padding:10px 18px;cursor:pointer;font-family:var(--font);font-size:12px;
  font-weight:600;letter-spacing:.08em;border-bottom:2px solid transparent;
  color:var(--mu);transition:all .15s}
.tab:hover{color:var(--tx)}
.tab.act{color:#fff;border-bottom-color:var(--b)}
.tc{display:none;padding:20px 28px 48px}
.tc.act{display:block}
.fbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
.fb{padding:4px 12px;border-radius:3px;cursor:pointer;font-family:var(--font);
  font-size:11px;font-weight:600;letter-spacing:.08em;
  border:1px solid var(--bd);background:var(--s2);color:var(--mu);transition:all .15s}
.fb:hover{color:#fff;border-color:var(--b);background:rgba(64,196,255,.08)}
.fb.act{border-color:var(--b);color:var(--b)}
.fb.act-g{border-color:var(--g);background:rgba(0,230,118,.1);color:var(--g)}
.fb.act-r{border-color:var(--r);background:rgba(255,82,82,.1);color:var(--r)}
input[type=range]{accent-color:var(--b);vertical-align:middle;width:100px}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead tr{border-bottom:2px solid var(--bd)}
th{padding:8px 6px;text-align:left;font-size:9px;letter-spacing:.15em;
   text-transform:uppercase;color:var(--mu);white-space:nowrap}
td{padding:8px 6px;border-bottom:1px solid rgba(28,37,53,.7);vertical-align:middle}
.sr{transition:background .1s}
.sr:hover td{background:rgba(255,255,255,.025)}
.rk{color:var(--mu);font-size:10px;width:28px}
.tk{font-weight:700;color:#fff;font-size:14px;min-width:55px}
.sc{font-size:15px;min-width:48px}
.nu{text-align:right;min-width:65px}
.sb{min-width:110px}
.badge{display:inline-block;padding:2px 7px;border-radius:3px;
  font-size:10px;font-weight:600;letter-spacing:.05em;white-space:nowrap}
.bl{background:rgba(0,230,118,.18);color:var(--g)}
.br{background:rgba(255,82,82,.18);color:var(--r)}
.bc-u{background:rgba(0,230,118,.12);color:#a5d6a7}
.bc-d{background:rgba(255,82,82,.12);color:#ef9a9a}
.bb-u{background:rgba(64,196,255,.1);color:var(--b)}
.bb-d{background:rgba(206,147,216,.1);color:var(--p)}
.bn{background:rgba(255,255,255,.05);color:var(--mu)}
.bs-tf{background:rgba(0,230,118,.12);color:#a5d6a7}
.bs-cp{background:rgba(64,196,255,.12);color:#81d4fa}
.bs-mom{background:rgba(255,235,59,.12);color:#fff59d}
.bs-mr{background:rgba(255,138,128,.12);color:#ffccbc}
.mb{display:flex;align-items:center;gap:4px;margin-bottom:2px;height:13px}
.mbf{height:5px;border-radius:2px;min-width:2px}
.mbl{font-size:9px;color:var(--mu);min-width:20px}
.btn-tr{padding:3px 9px;border-radius:3px;cursor:pointer;font-family:var(--font);
  font-size:10px;font-weight:600;border:1px solid var(--bd);background:var(--s2);
  color:var(--mu);transition:all .15s;white-space:nowrap}
.btn-tr:hover{border-color:var(--b);color:var(--b)}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:10px}
.kpi-card{background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:12px 14px;text-align:center}
.kpi-v{font-size:20px;font-weight:700;line-height:1.2}
.kpi-l{font-size:9px;color:var(--mu);margin-top:3px;text-transform:uppercase;letter-spacing:.12em}
.kpi-s{font-size:9px;color:var(--mu);margin-top:2px}
.card{background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:16px}
.bd-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.bds{background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:14px}
.bdt{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px}
.btt{width:100%;border-collapse:collapse;font-size:12px}
.btt th{font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--mu);padding:4px 6px}
.btt td{padding:5px 6px;border-bottom:1px solid rgba(28,37,53,.5)}
.btt tr:last-child td{border-bottom:none}
.pos-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  padding:10px 0;border-bottom:1px solid rgba(28,37,53,.6)}
.pos-row:last-child{border-bottom:none}
.pos-tk{font-weight:700;color:#fff;min-width:55px}
.pos-empty{color:var(--mu);padding:20px 0;font-size:12px}
.btn-act{padding:7px 18px;border-radius:4px;cursor:pointer;font-family:var(--font);
  font-size:12px;font-weight:600;border:1px solid var(--b);
  background:rgba(64,196,255,.08);color:var(--b);transition:all .15s;margin-top:12px}
.btn-act:hover{background:rgba(64,196,255,.18)}
.btn-del{padding:3px 8px;border-radius:3px;cursor:pointer;font-family:var(--font);
  font-size:10px;border:1px solid var(--mu);background:transparent;
  color:var(--mu);transition:all .15s;margin-left:auto}
.btn-del:hover{border-color:var(--r);color:var(--r)}
.form-grid{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;align-items:flex-end;
  background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:14px}
label.fl{font-size:10px;color:var(--mu);display:flex;flex-direction:column;gap:3px}
label.fl input,label.fl select{background:var(--bg);border:1px solid var(--bd);border-radius:3px;
  color:var(--tx);font-family:var(--font);font-size:12px;padding:5px 8px;
  outline:none;width:108px}
label.fl input:focus{border-color:var(--b)}
.hidden{display:none!important}
"""

    JS = """
function showTab(id,el){
  document.querySelectorAll('.tc').forEach(t=>t.classList.remove('act'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('act'));
  document.getElementById('tc-'+id).classList.add('act');
  el.classList.add('act');
}
let _dir=null,_evt=null,_minSc=0;
function applyF(){
  document.querySelectorAll('tr.sr').forEach(r=>{
    const d=r.dataset.dir, sc=parseFloat(r.dataset.sc||0);
    const et=r.querySelector('.bc-u,.bc-d,.bb-u,.bb-d,.bs-tf,.bs-cp,.bs-mom,.bs-mr');
    const ev=et?et.textContent:'';
    let ok=true;
    if(_dir&&d!==_dir)ok=false;
    if(_evt&&!ev.includes(_evt))ok=false;
    if(sc<_minSc)ok=false;
    r.classList.toggle('hidden',!ok);
  });
}
function fAll(){_dir=null;_evt=null;
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('act','act-g','act-r'));
  document.getElementById('fb-all').classList.add('act');applyF();}
function fDir(d){_dir=_dir===d?null:d;
  ['fb-long','fb-short'].forEach(id=>document.getElementById(id).classList.remove('act-g','act-r'));
  if(_dir==='LONG')document.getElementById('fb-long').classList.add('act-g');
  if(_dir==='SHORT')document.getElementById('fb-short').classList.add('act-r');applyF();}
function fEvt(e){_evt=_evt===e?null:e;
  ['fb-ch','fb-bo'].forEach(id=>document.getElementById(id).classList.remove('act'));
  if(_evt==='CHoCH')document.getElementById('fb-ch').classList.add('act');
  if(_evt==='BOS')document.getElementById('fb-bo').classList.add('act');applyF();}
function fSc(v){_minSc=parseInt(v);
  document.getElementById('sc-lbl').textContent='Score \u2265 '+v;applyF();}

let positions=[];
function addPos(tk,dir,entry,stop,t1,score){
  if(positions.find(p=>p.tk===tk&&p.dir===dir)){alert(tk+' '+dir+' già presente');return;}
  positions.push({id:Date.now(),tk,dir,entry,stop,t1,score,date:new Date().toLocaleDateString('it-IT')});
  renderPos();
  showTab('positions',document.querySelectorAll('.tab')[2]);
}
function delPos(id){positions=positions.filter(p=>p.id!==id);renderPos();}
function clearPos(){if(confirm('Cancellare tutto?')){positions=[];renderPos();}}
function toggleForm(){document.getElementById('form-pos').classList.toggle('hidden');}
function saveForm(){
  const tk=document.getElementById('f-tk').value.trim().toUpperCase();
  const dir=document.getElementById('f-dir').value;
  const ep=parseFloat(document.getElementById('f-ep').value);
  const sl=parseFloat(document.getElementById('f-sl').value);
  const t1=parseFloat(document.getElementById('f-t1').value);
  const sc=parseFloat(document.getElementById('f-sc').value||0);
  if(!tk||isNaN(ep)||isNaN(sl)||isNaN(t1)){alert('Compila Ticker, Entry, Stop, T1');return;}
  addPos(tk,dir,ep,sl,t1,sc);
  ['f-tk','f-ep','f-sl','f-t1','f-sc'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('form-pos').classList.add('hidden');
}
function renderPos(){
  const el=document.getElementById('pos-list');
  document.getElementById('pos-n').textContent=positions.length;
  if(!positions.length){el.innerHTML='<div class="pos-empty">Nessuna posizione aperta.</div>';return;}
  el.innerHTML=positions.map(p=>{
    const risk=Math.abs(p.entry-p.stop),rew=Math.abs(p.t1-p.entry);
    const rr=(rew/Math.max(risk,1e-6)).toFixed(2);
    const db=p.dir==='LONG'?'<span class="badge bl">▲ LONG</span>':'<span class="badge br">▼ SHORT</span>';
    return `<div class="pos-row">
      <span class="pos-tk">${p.tk}</span>${db}
      <span style="color:var(--mu);font-size:11px">entry=${p.entry.toFixed(2)}</span>
      <span style="color:var(--r);font-size:11px">stop=${p.stop.toFixed(2)}</span>
      <span style="color:var(--g);font-size:11px">T1=${p.t1.toFixed(2)}</span>
      <span style="color:var(--y);font-size:11px;font-weight:700">R/R=${rr}</span>
      <span style="color:var(--mu);font-size:10px">score=${p.score}</span>
      <span style="color:var(--mu);font-size:10px">${p.date}</span>
      <button class="btn-del" onclick="delPos(${p.id})">✕</button>
    </div>`;
  }).join('');
}
renderPos();
"""

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>

<div class="hdr">
  <div>
    <div class="hdr-t">MTF Swing <span>Screener</span></div>
    <div class="hdr-s">Aggiornato: {ts}&nbsp;|&nbsp;Azioni USA — S&amp;P 500 / Nasdaq</div>
  </div>
  <div style="font-size:10px;color:var(--mu)">Alpha Vantage API&nbsp;|&nbsp;Daily + Weekly MTF</div>
</div>

<div class="stat-bar">
  <div class="stat"><div class="stat-v">{n}</div><div class="stat-l">Segnali</div></div>
  <div class="stat"><div class="stat-v" style="color:var(--g)">{n_l}</div><div class="stat-l">Long</div></div>
  <div class="stat"><div class="stat-v" style="color:var(--r)">{n_s}</div><div class="stat-l">Short</div></div>
  <div class="stat"><div class="stat-v" style="color:var(--y)">{avg_sc:.1f}</div><div class="stat-l">Score medio</div></div>
  <div class="stat"><div class="stat-v">{avg_rr:.2f}</div><div class="stat-l">R/R medio</div></div>
  <div class="stat"><div class="stat-v" style="color:var(--g)">{n_ch}</div><div class="stat-l">CHoCH</div></div>
  <div class="stat"><div class="stat-v" style="color:var(--b)">{n_bo}</div><div class="stat-l">BOS</div></div>
</div>

<div class="tabs">
  <div class="tab act" onclick="showTab('scan',this)">📡 Scan</div>
  <div class="tab" onclick="showTab('backtest',this)">📊 Backtest</div>
  <div class="tab" onclick="showTab('positions',this)">🗂 Posizioni</div>
</div>

<!-- SCAN TAB -->
<div id="tc-scan" class="tc act">
  <div class="fbar">
    <button class="fb act" id="fb-all" onclick="fAll()">Tutti</button>
    <button class="fb" id="fb-long" onclick="fDir('LONG')">▲ Long</button>
    <button class="fb" id="fb-short" onclick="fDir('SHORT')">▼ Short</button>
    <button class="fb" id="fb-ch" onclick="fEvt('CHoCH')">CHoCH</button>
    <button class="fb" id="fb-bo" onclick="fEvt('BOS')">BOS</button>
    <input type="range" min="0" max="100" value="0" oninput="fSc(this.value)">
    <span id="sc-lbl" style="font-size:11px;color:var(--mu)">Score ≥ 0</span>
  </div>
  <div class="tw">
    <table>
      <thead><tr>
        <th>#</th><th>Ticker</th><th>Dir</th><th>Score</th>
        <th>Str / Trd / Mom</th><th>Evento</th>
        <th class="nu">Entry</th><th class="nu">Stop</th><th class="nu">T1</th>
        <th class="nu">R/R</th><th class="nu">ADX</th><th class="nu">RSI</th>
        <th class="nu">Vol</th><th class="nu">ATR%</th><th>W/D</th><th></th>
      </tr></thead>
      <tbody>{rows}{no_sig}</tbody>
    </table>
  </div>
  <div style="margin-top:24px">
    <div class="bdt" style="margin-bottom:8px">Distribuzione Score</div>
    {dsv}
  </div>
</div>

<!-- BACKTEST TAB -->
<div id="tc-backtest" class="tc">{bt_html}</div>

<!-- POSITIONS TAB -->
<div id="tc-positions" class="tc">
  <div style="font-size:11px;color:var(--mu);margin-bottom:16px;max-width:600px">
    Aggiungi posizioni con il bottone <strong>+Track</strong> nel tab Scan,
    oppure manualmente qui sotto. I dati restano in memoria per questa sessione.
  </div>
  <button class="btn-act" onclick="toggleForm()">+ Aggiungi manualmente</button>
  <div id="form-pos" class="form-grid hidden">
    <label class="fl">Ticker <input id="f-tk" placeholder="AAPL" maxlength="6"></label>
    <label class="fl">Direzione
      <select id="f-dir">
        <option value="LONG">▲ LONG</option>
        <option value="SHORT">▼ SHORT</option>
      </select>
    </label>
    <label class="fl">Entry    <input id="f-ep" type="number" step="0.01" placeholder="150.00"></label>
    <label class="fl">Stop     <input id="f-sl" type="number" step="0.01" placeholder="145.00"></label>
    <label class="fl">Target 1 <input id="f-t1" type="number" step="0.01" placeholder="158.00"></label>
    <label class="fl">Score    <input id="f-sc" type="number" step="0.1"  placeholder="72.5"></label>
    <button class="btn-act" onclick="saveForm()" style="margin-top:0;align-self:flex-end">Salva</button>
  </div>
  <div class="card" style="margin-top:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-size:12px;font-weight:600;color:#fff">
        Posizioni aperte (<span id="pos-n">0</span>)
      </span>
      <button class="btn-del" onclick="clearPos()" style="border-color:var(--r);color:var(--r)">
        Cancella tutto
      </button>
    </div>
    <div id="pos-list"><div class="pos-empty">Nessuna posizione aperta.</div></div>
  </div>
</div>

<script>{JS}</script>
</body>
</html>"""

    ts_f = datetime.now().strftime("%Y%m%d_%H%M")
    out  = OUTPUT_DIR / f"dashboard_{ts_f}.html"
    out.write_text(html, encoding="utf-8")
    return out


# ── self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random, sys
    sys.path.insert(0, ".")
    from backtest import compute_stats, Trade

    random.seed(42)
    np.random.seed(7)

    tickers = ["AAPL","NVDA","MSFT","META","GOOGL","JPM","TSLA","AMD","AMZN","AVGO",
               "LLY","UNH","CAT","HD","XOM","GS","NKE","ABBV","HON","CVX"]
    events  = ["BOS_UP","CHoCH_UP","BOS_DOWN","CHoCH_DOWN","","BOS_UP","CHoCH_UP"]
    signals = []
    for t in tickers:
        ep  = random.uniform(80, 650)
        atr = ep * random.uniform(0.012, 0.032)
        d   = "LONG" if random.random() > 0.3 else "SHORT"
        signals.append({
            "ticker": t, "direction": d,
            "score":            round(random.uniform(60, 94), 1),
            "score_structure":  round(random.uniform(45, 100), 1),
            "score_trend":      round(random.uniform(35, 100), 1),
            "score_momentum":   round(random.uniform(25, 100), 1),
            "score_volatility": round(random.uniform(40, 100), 1),
            "score_volume":     round(random.uniform(30, 100), 1),
            "structure_event":  random.choice(events),
            "entry_price":  round(ep, 2),
            "stop_loss":    round(ep + atr*(-1.5 if d=="LONG" else 1.5), 2),
            "target1":      round(ep + atr*(2.0 if d=="LONG" else -2.0), 2),
            "risk_reward":  round(random.uniform(1.1, 3.2), 2),
            "adx":          round(random.uniform(18, 50), 1),
            "rsi":          round(random.uniform(30, 72), 1),
            "volume_ratio": round(random.uniform(0.8, 2.8), 2),
            "atr_pct":      round(random.uniform(1.0, 4.0), 2),
            "weekly_trend": random.choice(["UPTREND","UPTREND","DOWNTREND","UNDEFINED"]),
            "daily_trend":  random.choice(["UPTREND","UPTREND","DOWNTREND","UNDEFINED"]),
        })
    signals.sort(key=lambda s: s["score"], reverse=True)

    # Demo backtest stats
    n_t   = 150
    dates = pd.bdate_range("2023-01-02", periods=n_t)
    pnl_r = np.random.normal(0.18, 0.88, n_t)
    equity = 100 * np.cumprod(1 + pnl_r/100)
    eq_series = [{"date": str(d.date()), "equity": round(float(e),3)}
                 for d,e in zip(dates, equity)]

    demo_trades = []
    evts = ["BOS_UP","CHoCH_UP","BOS_DOWN","CHoCH_DOWN","BOS_UP","CHoCH_UP"]
    dirs = ["LONG","LONG","LONG","SHORT","LONG","LONG","SHORT"]
    for i in range(n_t):
        demo_trades.append(Trade(
            ticker="DEMO", direction=dirs[i % len(dirs)],
            entry_date=dates[i], entry_price=100.0,
            stop_loss=98.5, target1=102.7, target2=106.0,
            score=float(60 + (i*7) % 35),
            structure_event=evts[i % len(evts)],
            volume_ratio=1.4, adx=28.0, atr_pct=2.1,
            exit_date=dates[min(i+4, n_t-1)],
            exit_price=float(100 + pnl_r[i]),
            exit_reason=["T1","T1","STOP","T2","TIMEOUT"][i % 5],
            pnl_pct=round(float(pnl_r[i]), 3),
            rr_realized=round(float(pnl_r[i])/1.5, 2),
            n_bars_held=int(2 + i % 6),
            won=pnl_r[i] > 0,
        ))

    bt = compute_stats(demo_trades, risk_per_trade_pct=1.0)
    path = generate_dashboard(signals, bt_stats=bt)
    print(f"✓ Dashboard: {path}")
    print(f"  file://{path.absolute()}")
