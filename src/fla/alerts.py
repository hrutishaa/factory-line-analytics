"""Line-health alerting: SPC rule checks per shift -> alerts with root-cause drilldown -> shift handoff report."""
import json, duckdb, numpy as np, pandas as pd
from .config import DB, REPORTS
from .stats import p_chart

def we_rules(rate, center, sigma):
    """Western Electric rules 1,2,4 on a series. Returns {index: [rule names]}."""
    z = (rate - center) / sigma; hits = {}
    def add(i, r): hits.setdefault(int(i), []).append(r)
    for i in range(len(z)):
        if abs(z[i]) > 3: add(i, "WE1: point beyond 3σ")
        if i >= 2 and sum(z[i-2:i+1] > 2) >= 2 and z[i] > 2: add(i, "WE2: 2 of 3 beyond +2σ")
        if i >= 7 and (all(z[i-7:i+1] > 0) or all(z[i-7:i+1] < 0)): add(i, "WE4: 8 in a row above center" if z[i] > 0 else "WE4: 8 in a row below center (improvement)")
    return hits

def run():
    con = duckdb.connect(str(DB), read_only=True)
    s = con.sql("SELECT * FROM v_shift_oee ORDER BY shift_id").df()
    pbar, lcl, ucl = p_chart(s)
    sigma = ((ucl - pbar) / 3).values
    rate = (s.failed_units / s.units).values
    hits = we_rules(rate, pbar, sigma)
    mode = con.sql("""SELECT e.shift_id, e.mode_code, p.product_type, COUNT(*) n FROM fact_failure_event e
        JOIN fact_cycle c USING(udi) JOIN dim_product p USING(product_id) GROUP BY ALL""").df()
    base_mode = mode.groupby("mode_code").n.sum() / len(s)
    status, alerts = [], []
    for i, r in s.iterrows():
        z = (rate[i] - pbar) / sigma[i]
        bad = i in hits and any("improvement" not in h for h in hits[i])
        st = "red" if bad else "amber" if i in hits else ("amber" if z > 1.5 else "green")
        status.append({"shift_id": int(r.shift_id), "status": st, "failure_rate": float(rate[i]),
                       "yield": float(r["yield"]), "oee": float(r.oee), "z": float(z)})
        if i in hits:
            m = mode[mode.shift_id == r.shift_id]
            by_mode = m.groupby("mode_code").n.sum().sort_values(ascending=False)
            lift = (by_mode / base_mode.reindex(by_mode.index)).round(2)
            alerts.append({"shift_id": int(r.shift_id), "rules": hits[i], "failure_rate": float(rate[i]),
                "ucl": float(ucl[i]), "yield": float(r["yield"]), "oee": float(r.oee),
                "by_mode": by_mode.to_dict(), "mode_lift_vs_avg_shift": lift.to_dict(),
                "severity": st, "by_type": m.groupby("product_type").n.sum().to_dict(), "top_cause": by_mode.index[0]})
    out = {"pbar": float(pbar), "status": status, "alerts": alerts}
    (REPORTS / "line_health.json").write_text(json.dumps(out, indent=2))
    write_handoff(out, s)
    print(f"{len(alerts)} alerts:", [(a['shift_id'], a['rules'], a['top_cause']) for a in alerts])
    return out

def write_handoff(out, s):
    names = {"TWF": "tool wear", "HDF": "heat dissipation", "PWF": "power", "OSF": "overstrain", "RNF": "random"}
    L = ["# Shift Handoff — Line Health Report", "",
         f"Source: AI4I 2020, {int(s.units.sum()):,} cycles, {len(s)} shifts of 500 cycles. Baseline failure rate p̄ = {out['pbar']:.2%}.", "",
         "## Status board", "", "| Shift | Status | Failure rate | Yield | OEE (modelled) |", "|---|---|---|---|---|"]
    for x in out["status"]:
        L.append(f"| {x['shift_id']} | {x['status'].upper()} | {x['failure_rate']:.1%} | {x['yield']:.1%} | {x['oee']:.1%} |")
    L += ["", "## Open alerts", ""]
    for a in out["alerts"]:
        L += [f"### [{a['severity'].upper()}] Shift {a['shift_id']} — {', '.join(a['rules'])}",
              f"- Failure rate {a['failure_rate']:.1%} vs UCL {a['ucl']:.1%}; yield {a['yield']:.1%}; OEE {a['oee']:.1%}",
              "- Failure modes: " + ", ".join(f"{names[k]} {v} ({a['mode_lift_vs_avg_shift'][k]}× avg shift)" for k, v in a["by_mode"].items()),
              "- By product type: " + ", ".join(f"{k} {v}" for k, v in sorted(a["by_type"].items())),
              (f"- Next action: inspect **{names[a['top_cause']]}** failures first (largest contributor)." if a["severity"] == "red"
               else "- Next action: sustained run below baseline — confirm what changed and whether to re-baseline limits."), ""]
    if not out["alerts"]: L.append("None.")
    (REPORTS / "shift_handoff.md").write_text("\n".join(L) + "\n")

if __name__ == "__main__":
    run()
