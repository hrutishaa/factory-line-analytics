"""Line Health control-room dashboard -> reports/dashboard.html (custom HTML/CSS + Plotly with custom template)."""
import json, duckdb, numpy as np
import plotly.graph_objects as go
from .config import DB, REPORTS
from .stats import p_chart

BG, CARD, GRID, INK, MUTED = "#121417", "#1a1d21", "#2a2e34", "#e8e6e3", "#8a8f98"
ACC, AMBER, GREEN = "#ff3b30", "#ffb020", "#30d158"
FONT = "Inter, system-ui, sans-serif"; MONO = "JetBrains Mono, monospace"
MODE_NAMES = {"TWF": "Tool wear", "HDF": "Heat dissipation", "PWF": "Power", "OSF": "Overstrain", "RNF": "Random"}

def layout(**kw):
    base = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=44, r=12, t=8, b=36),
                font=dict(family=FONT, color=MUTED, size=11), showlegend=False, hovermode="x unified",
                hoverlabel=dict(bgcolor=CARD, bordercolor=GRID, font=dict(family=MONO, color=INK)),
                xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(family=MONO)),
                yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(family=MONO)))
    base.update(kw); return base

def spark(y, color):
    f = go.Figure(go.Scatter(y=list(y), mode="lines", line=dict(color=color, width=1.6), fill="tozeroy",
                             fillcolor=color + "22", hoverinfo="skip"))
    f.update_layout(layout(margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False)))
    return f

def run():
    con = duckdb.connect(str(DB), read_only=True)
    s = con.sql("SELECT * FROM v_shift_oee ORDER BY shift_id").df()
    par = con.sql("SELECT * FROM v_downtime_pareto").df()
    mt = con.sql("""SELECT e.mode_code, p.product_type, COUNT(*) n FROM fact_failure_event e JOIN fact_cycle c USING(udi)
                    JOIN dim_product p USING(product_id) GROUP BY ALL""").df()
    ms = con.sql("SELECT shift_id, mode_code, COUNT(*) n FROM fact_failure_event GROUP BY ALL").df()
    lh = json.loads((REPORTS / "line_health.json").read_text())
    m = json.loads((REPORTS / "model_metrics.json").read_text())["gbm_test"]
    pbar, lcl, ucl = p_chart(s); rate = s.failed_units / s.units; sig = (ucl - pbar) / 3
    x = s.shift_id.tolist(); stat = {d["shift_id"]: d["status"] for d in lh["status"]}
    col = {"green": GREEN, "amber": AMBER, "red": ACC}
    figs = {}
    # SPC with shaded bands
    spc = go.Figure()
    for k, a in [(3, "14"), (2, "1f")]:
        spc.add_trace(go.Scatter(x=x + x[::-1], y=list(pbar + k*sig) + list(np.clip(pbar - k*sig, 0, None))[::-1],
                                 fill="toself", fillcolor=AMBER + a, line=dict(width=0), hoverinfo="skip"))
    spc.add_trace(go.Scatter(x=x, y=ucl, line=dict(color=ACC, dash="dot", width=1), name="UCL"))
    spc.add_hline(y=pbar, line=dict(color=MUTED, width=1, dash="dash"))
    spc.add_trace(go.Scatter(x=x, y=rate, mode="lines+markers", name="failure rate", line=dict(color=INK, width=1.6),
                             marker=dict(size=9, color=[col[stat[i]] for i in x], line=dict(color=BG, width=2))))
    spc.update_layout(layout(yaxis=dict(tickformat=".0%", gridcolor=GRID, tickfont=dict(family=MONO)),
                             xaxis=dict(dtick=1, gridcolor=GRID, tickfont=dict(family=MONO), title="shift")))
    figs["spc"] = spc
    # Pareto
    cum = par.downtime_min.cumsum() / par.downtime_min.sum()
    pa = go.Figure([go.Bar(x=par.mode_code.map(MODE_NAMES), y=par.downtime_min, marker_color=[ACC] + [GRID]*4,
                           text=[f"{int(v):,}" for v in par.downtime_min], textposition="outside", textfont=dict(family=MONO, color=INK)),
                    go.Scatter(x=par.mode_code.map(MODE_NAMES), y=cum, yaxis="y2", mode="lines+markers", line=dict(color=AMBER, width=1.5))])
    pa.update_layout(layout(yaxis=dict(range=[0, float(par.downtime_min.max())*1.18], gridcolor=GRID, tickfont=dict(family=MONO)), yaxis2=dict(overlaying="y", side="right", range=[0, 1.05], tickformat=".0%", showgrid=False,
                                        tickfont=dict(family=MONO)), margin=dict(l=44, r=40, t=16, b=36)))
    figs["pareto"] = pa
    # failure mode x product type
    fm = go.Figure()
    for t, c in zip(["L", "M", "H"], [ACC, AMBER, MUTED]):
        d = mt[mt.product_type == t].set_index("mode_code").reindex(list(MODE_NAMES)).fillna(0)
        fm.add_trace(go.Bar(y=[MODE_NAMES[k] for k in d.index], x=d.n, orientation="h", name=f"type {t}", marker_color=c))
    fm.update_layout(layout(barmode="stack", showlegend=True, hovermode="y unified",
                            legend=dict(orientation="h", y=1.12, font=dict(family=MONO, color=INK))))
    figs["modes"] = fm
    # root-cause heatmap shift x mode
    hm = ms.pivot(index="mode_code", columns="shift_id", values="n").reindex(list(MODE_NAMES)).reindex(columns=x).fillna(0)
    rc = go.Figure(go.Heatmap(z=hm.values, x=x, y=[MODE_NAMES[k] for k in hm.index], showscale=False,
                              colorscale=[[0, CARD], [0.15, "#3a2a24"], [1, ACC]], xgap=2, ygap=2,
                              text=hm.values.astype(int), texttemplate="%{text}", textfont=dict(family=MONO, size=10)))
    rc.update_layout(layout(xaxis=dict(dtick=1, tickfont=dict(family=MONO), showgrid=False), yaxis=dict(showgrid=False), hovermode="closest"))
    figs["rootcause"] = rc
    figs["sp_yield"] = spark(s["yield"], GREEN); figs["sp_oee"] = spark(s.oee, AMBER)
    figs["sp_fail"] = spark(rate, ACC); figs["sp_cycle"] = spark(s.avg_cycle_min, MUTED)

    n_red = sum(v == "red" for v in stat.values()); n_amb = sum(v == "amber" for v in stat.values())
    kpis = [("First-pass yield", f"{s['yield'].mean():.2%}", "sp_yield", "20 shifts · 10,000 cycles"),
            ("OEE", f"{s.oee.mean():.1%}", "sp_oee", f"range {s.oee.min():.1%}–{s.oee.max():.1%} · modelled"),
            ("Failure rate", f"{pbar:.2%}", "sp_fail", "p̄ across all cycles"),
            ("Avg cycle time", f"{s.avg_cycle_min.mean():.2f}<small>min</small>", "sp_cycle", "tool-wear proxy"),
            ("Out-of-control", f"{n_red}<small>shifts</small>", None, f"+{n_amb} amber (WE4 run below center)")]
    kpi_html = "".join(f'<div class="card kpi"><div class="lbl">{l}</div><div class="num">{v}</div>'
        + (f'<div class="spark" id="{sid}"></div>' if sid else
           '<div class="chips mini">' + "".join(f'<i class="{stat[i]}"></i>' for i in x) + '</div>')
        + f'<div class="sub">{sub}</div></div>' for l, v, sid, sub in kpis)
    chips = "".join(f'<div class="chip {d["status"]}"><b>S{d["shift_id"]:02d}</b><span>{d["failure_rate"]:.1%}</span></div>' for d in lh["status"])
    alerts = "".join(f'''<div class="alert {a['severity']}"><div class="ah"><b>SHIFT {a['shift_id']:02d}</b><span>{a['severity'].upper()}</span></div>
        <div class="ar">{' · '.join(a['rules'])}</div>
        <div class="am">fail {a['failure_rate']:.1%} / UCL {a['ucl']:.1%} · top cause <b>{MODE_NAMES[a['top_cause']]}</b>
        {a['by_mode'][a['top_cause']]} ({a['mode_lift_vs_avg_shift'][a['top_cause']]}× avg)</div></div>''' for a in lh["alerts"])
    cm = f'''<div class="cm"><div></div><div class="h">pred OK</div><div class="h">pred FAIL</div>
      <div class="h">actual OK</div><div class="c">{m['tn']:,}</div><div class="c bad">{m['fp']}</div>
      <div class="h">actual FAIL</div><div class="c bad">{m['fn']}</div><div class="c good">{m['tp']}</div></div>'''
    model = f'''<div class="mstats"><div><span>Precision</span><b>{m['precision']:.1%}</b></div><div><span>Recall</span><b>{m['recall']:.1%}</b></div>
      <div><span>PR-AUC</span><b>{m['pr_auc']:.3f}</b></div><div><span>ROC-AUC</span><b>{m['roc_auc']:.3f}</b></div></div>{cm}
      <div class="sub">HistGradientBoosting · 2,000 held-out cycles · threshold {m['threshold']:.2f} (tuned on validation)</div>'''
    data = {k: json.loads(f.to_json()) for k, f in figs.items()}
    html = TEMPLATE.replace("{{KPIS}}", kpi_html).replace("{{CHIPS}}", chips).replace("{{ALERTS}}", alerts)\
        .replace("{{MODEL}}", model).replace("{{DATA}}", json.dumps(data)).replace("{{NALERT}}", str(len(lh["alerts"])))
    (REPORTS / "dashboard.html").write_text(html)

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><title>Line Health · NPI Control Room</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#121417;--card:#1a1d21;--line:#2a2e34;--ink:#e8e6e3;--mut:#8a8f98;--acc:#ff3b30;--amb:#ffb020;--grn:#30d158}
*{box-sizing:border-box;margin:0}body{background:var(--bg);color:var(--ink);font-family:Inter,'DejaVu Sans',sans-serif;padding:28px 32px;width:1440px}
header{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:20px}
h1{font-size:22px;font-weight:700;letter-spacing:-.01em}h1 em{color:var(--acc);font-style:normal}
.meta{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:11px;color:var(--mut);text-align:right;line-height:1.6}
.live{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--acc);margin-right:6px;box-shadow:0 0 10px var(--acc)}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px 18px}
.card h2{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin-bottom:10px;display:flex;justify-content:space-between}
.card h2 span{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;letter-spacing:0;text-transform:none}
.kpis{grid-column:span 12;display:grid;grid-template-columns:repeat(5,1fr);gap:14px}
.kpi .lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.kpi .num{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:38px;font-weight:700;margin:6px 0 4px}.kpi small{font-size:14px;color:var(--mut);margin-left:6px}
.kpi:first-child{border-top:2px solid var(--acc)}
.spark{height:34px}.sub{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:10.5px;color:var(--mut);margin-top:6px}
.chips{display:grid;grid-template-columns:repeat(10,1fr);gap:6px}.chips.mini{grid-template-columns:repeat(20,1fr);gap:3px;height:34px;align-items:center}
.chips.mini i{height:22px;border-radius:2px}.chips.mini i.green{background:#30d15855}.chips.mini i.amber{background:var(--amb)}.chips.mini i.red{background:var(--acc)}
.chip{border:1px solid var(--line);border-left:3px solid;border-radius:4px;padding:6px 8px;font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:11px;display:flex;justify-content:space-between}
.chip.green{border-left-color:var(--grn)}.chip.amber{border-left-color:var(--amb);color:var(--amb)}.chip.red{border-left-color:var(--acc);background:#ff3b3014;color:var(--acc)}
.chip span{color:var(--mut)}
.alert{border-left:3px solid;padding:8px 10px;margin-bottom:8px;background:#ffffff05}.alert.red{border-color:var(--acc)}.alert.amber{border-color:var(--amb)}
.ah{display:flex;justify-content:space-between;font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:12px}.alert.red .ah span{color:var(--acc)}.alert.amber .ah span{color:var(--amb)}
.ar{font-size:11px;color:var(--ink);margin:3px 0}.am{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:10.5px;color:var(--mut)}.am b{color:var(--ink)}
.mstats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}.mstats span{display:block;font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.1em}
.mstats b{font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:22px}
.cm{display:grid;grid-template-columns:90px 1fr 1fr;gap:4px;font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:11px}
.cm .h{color:var(--mut);align-self:center;text-align:center}.cm .c{background:#ffffff08;padding:14px 0;text-align:center;font-size:20px;font-weight:700}
.cm .good{background:#30d15822;color:var(--grn)}.cm .bad{background:#ff3b301f;color:var(--acc)}
.s4{grid-column:span 4}.s5{grid-column:span 5}.s7{grid-column:span 7}.s8{grid-column:span 8}.s3{grid-column:span 3}
.plot{height:260px}
footer{margin-top:18px;font-family:'JetBrains Mono',ui-monospace,'DejaVu Sans Mono',monospace;font-size:10.5px;color:var(--mut)}
</style></head><body>
<header><div><h1>LINE HEALTH <em>//</em> NPI CONTROL ROOM</h1><div class="meta" style="text-align:left;margin-top:4px">AI4I 2020 · 10,000 cycles · 20 shifts × 500 cycles</div></div>
<div class="meta"><span class="live"></span>{{NALERT}} ALERTS OPEN<br>SPC: p-chart + Western Electric rules 1/2/4</div></header>
<div class="grid">
<div class="kpis">{{KPIS}}</div>
<div class="card s8"><h2>SPC · failure rate per shift <span>±2σ / ±3σ bands shaded</span></h2><div class="plot" id="spc"></div></div>
<div class="card s4"><h2>Alerts <span>rule violations</span></h2>{{ALERTS}}</div>
<div class="card s12" style="grid-column:span 12"><h2>Shift status <span>green · amber · red</span></h2><div class="chips">{{CHIPS}}</div></div>
<div class="card s7"><h2>Root-cause drilldown · failure events by shift × mode</h2><div class="plot" id="rootcause"></div></div>
<div class="card s5"><h2>Downtime Pareto <span>modelled repair minutes</span></h2><div class="plot" id="pareto"></div></div>
<div class="card s7"><h2>Failure modes by product type</h2><div class="plot" id="modes"></div></div>
<div class="card s5"><h2>Model alerts · failure predictor</h2>{{MODEL}}</div>
</div>
<footer>OEE, availability, cycle time and downtime are derived (no timestamps in source data); yield, failures, SPC and model metrics are measured.</footer>
<script>const D={{DATA}};for(const k in D){Plotly.newPlot(k,D[k].data,D[k].layout,{displayModeBar:false,responsive:true})}</script>
</body></html>"""

if __name__ == "__main__":
    run()
