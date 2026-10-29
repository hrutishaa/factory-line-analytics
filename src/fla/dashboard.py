"""Build self-contained interactive Plotly dashboard -> reports/dashboard.html (+ PNG snapshots)."""
import json, duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .config import DB, REPORTS, FIG

def run():
    con = duckdb.connect(str(DB), read_only=True)
    s = con.sql("SELECT * FROM v_shift_oee ORDER BY shift_id").df()
    par = con.sql("SELECT * FROM v_downtime_pareto").df()
    yt = con.sql("SELECT * FROM v_yield_by_type").df()
    m = json.loads((REPORTS / "model_metrics.json").read_text())["gbm_test"]
    fig = make_subplots(rows=3, cols=2, specs=[[{"type": "indicator"}, {"type": "indicator"}], [{}, {}], [{}, {}]],
        subplot_titles=("Avg OEE", "Avg first-pass yield", "OEE components by shift", "Downtime Pareto (modelled min)",
                        "Avg cycle time by shift (min)", "Yield by product type"), vertical_spacing=0.1)
    fig.add_trace(go.Indicator(mode="number", value=s.oee.mean()*100, number={"suffix": "%"}), 1, 1)
    fig.add_trace(go.Indicator(mode="number", value=s["yield"].mean()*100, number={"suffix": "%", "valueformat": ".2f"}), 1, 2)
    for c in ["oee", "availability", "performance", "yield"]:
        fig.add_trace(go.Scatter(x=s.shift_id, y=s[c], mode="lines+markers", name=c), 2, 1)
    fig.add_trace(go.Bar(x=par.mode_code, y=par.downtime_min, name="downtime", text=par.events, showlegend=False), 2, 2)
    fig.add_trace(go.Bar(x=s.shift_id, y=s.avg_cycle_min, name="avg cycle", showlegend=False), 3, 1)
    fig.add_trace(go.Bar(x=yt.product_type, y=yt["yield"], name="yield", showlegend=False), 3, 2)
    fig.update_yaxes(range=[0.94, 0.99], row=3, col=2)
    fig.update_layout(height=1100, width=1300, title=f"Factory Line Analytics — AI4I 2020 (10,000 cycles) | "
        f"Failure model: PR-AUC {m['pr_auc']:.2f}, precision {m['precision']:.0%}, recall {m['recall']:.0%}")
    fig.write_html(REPORTS / "dashboard.html", include_plotlyjs="cdn")
    FIG.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(FIG / "dashboard.png")
    except Exception as e:
        print("PNG export skipped:", e)

if __name__ == "__main__":
    run()
