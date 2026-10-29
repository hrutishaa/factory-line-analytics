"""SPC control charts + hypothesis tests. Writes reports/stats.json and figures."""
import json, duckdb, numpy as np
from scipy import stats
from .config import DB, REPORTS, FIG

def p_chart(df):
    pbar = df.failed_units.sum() / df.units.sum()
    se = np.sqrt(pbar * (1 - pbar) / df.units)
    return pbar, np.clip(pbar - 3*se, 0, None), pbar + 3*se

def imr_limits(x):
    mr = np.abs(np.diff(x)); mrbar = mr.mean(); xbar = x.mean()
    return xbar, xbar - 2.66*mrbar, xbar + 2.66*mrbar

def run():
    con = duckdb.connect(str(DB), read_only=True)
    shift = con.sql("SELECT * FROM v_shift_oee ORDER BY shift_id").df()
    cyc = con.sql("SELECT f.*, p.product_type FROM fact_cycle f JOIN dim_product p USING(product_id)").df()
    pbar, lcl, ucl = p_chart(shift)
    rate = shift.failed_units / shift.units
    ooc = shift.shift_id[(rate > ucl) | (rate < lcl)].tolist()
    t_bar, t_lcl, t_ucl = imr_limits(cyc.torque_nm.values)
    torque_ooc = int(((cyc.torque_nm > t_ucl) | (cyc.torque_nm < t_lcl)).sum())
    groups = [g.torque_nm.values for _, g in cyc.groupby("product_type")]
    anova = stats.f_oneway(*groups)
    ct = (cyc.groupby("product_type").machine_failure.agg(["sum", "count"]))
    chi = stats.chi2_contingency(np.c_[ct["sum"], ct["count"] - ct["sum"]])
    f, ok = cyc[cyc.machine_failure == 1], cyc[cyc.machine_failure == 0]
    mw = {c: stats.mannwhitneyu(f[c], ok[c]) for c in ["torque_nm", "tool_wear_min", "rpm", "temp_delta_k"]}
    out = {
      "p_chart": {"pbar": pbar, "ooc_shifts": ooc},
      "torque_imr": {"mean": t_bar, "lcl": t_lcl, "ucl": t_ucl, "points_out_of_control": torque_ooc},
      "anova_torque_by_type": {"F": anova.statistic, "p": anova.pvalue},
      "chi2_failure_vs_type": {"chi2": chi.statistic, "p": chi.pvalue, "yield_by_type": (1 - ct["sum"]/ct["count"]).to_dict()},
      "mannwhitney_failed_vs_ok": {c: {"U": r.statistic, "p": r.pvalue,
            "median_failed": float(f[c].median()), "median_ok": float(ok[c].median())} for c, r in mw.items()},
    }
    REPORTS.mkdir(exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    (REPORTS / "stats.json").write_text(json.dumps(out, indent=2, default=float))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(shift.shift_id, rate, "o-", label="failure rate"); ax.plot(shift.shift_id, ucl, "r--", label="UCL")
    ax.plot(shift.shift_id, lcl, "r--"); ax.axhline(pbar, color="g", label="p̄")
    ax.set(title="p-chart: failure rate per shift (500 cycles)", xlabel="shift", ylabel="fraction failed"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "spc_p_chart.png", dpi=120)
    print(json.dumps(out, indent=1, default=float))
    return out

if __name__ == "__main__":
    run()
