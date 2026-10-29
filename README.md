# Factory Line Analytics — production KPIs, SPC & failure prediction

End-to-end manufacturing analytics on the public **AI4I 2020 Predictive Maintenance** dataset
(UCI ML Repository, id 601, 10,000 machine cycles, CC BY 4.0): automated ingest + validation into a DuckDB star schema,
SQL KPI views (cycle time, yield, downtime, OEE), SPC + hypothesis tests, a gradient-boosted failure model served by FastAPI,
and an interactive Plotly dashboard.

## One-command run
```bash
make all        # venv + deps, download data, pipeline -> stats -> model -> dashboard, then tests
make serve      # FastAPI on :8000  (POST /predict, GET /health)
```
(No make? `cd src && ../.venv/bin/python -m fla.run_all && cd .. && .venv/bin/python -m pytest -q`)

## Architecture
```
data/raw/ai4i2020.csv ─► pipeline.py (extract → validate → transform → load)
                          └─► DuckDB warehouse: dim_product, dim_shift, dim_failure_mode,
                                                fact_cycle, fact_failure_event
                              └─► kpis.py views: v_shift_kpis, v_shift_oee, v_yield_by_type, v_downtime_pareto
stats.py  ─► SPC p-chart, torque I-MR limits, ANOVA, chi-square, Mann-Whitney  → reports/stats.json
model.py  ─► logistic baseline vs HistGradientBoosting, held-out test set       → reports/model_metrics.json
api.py    ─► FastAPI /predict (pydantic-validated inputs, returns probability + alert)
dashboard.py ─► reports/dashboard.html (interactive) + reports/figures/*.png
```

## Modelling assumptions (be transparent)
AI4I has no timestamps, durations, or repair logs, so some production metrics are **derived**:
- **Shift** = 500 consecutive cycles (20 shifts).
- **Cycle time** proxy = positive increment of cumulative tool-wear minutes between consecutive cycles.
- **Downtime** = assumed repair minutes per failure mode (PWF 60, OSF 40, TWF 45, HDF 30, RNF 20) — see `config.py`.
- **OEE** = Availability (run ÷ (run + downtime)) × Performance (median cycle ÷ avg cycle, capped at 1) × Yield (1 − failure rate).
Yield, failure counts, sensor stats and all model metrics come directly from the real data.

## Results (actual run)
**Data validation:** 10,000 rows in / 10,000 out; 0 nulls, 0 duplicates, 0 out-of-range; flagged **27 label-inconsistent rows**
(machine_failure flag disagrees with failure-mode flags — a known AI4I quirk).

**KPIs (20 shifts):** first-pass yield **96.61%**, avg OEE **49.2%** (range 20.4%–59.3%), availability 65.8%, performance 76.9%,
avg cycle time 2.60 min. Downtime Pareto: power failures (95 events) drive the most modelled downtime (5,700 min), then
overstrain (98), heat dissipation (115), tool wear (46), random (19).

**SPC / statistics**
- p-chart (p̄ = 3.39%) flagged **shifts 9 and 10 out of control** (yield 84.8% and 88.4%; OEE 20%/26%).
- Torque I-MR limits 10.4–69.6 Nm; 26 cycles outside.
- Failure rate differs by product type (χ² = 13.75, p = 0.001): yield L 96.1%, M 97.2%, H 97.9%.
- ANOVA: torque does *not* differ by product type (F = 0.13, p = 0.88) — so the type effect isn't explained by load.
- Failed vs OK cycles (Mann-Whitney, all p < 1e-23): median torque 53.7 vs 39.9 Nm, tool wear 165 vs 107 min, speed 1,365 vs 1,507 rpm.

**Failure prediction (stratified 80/20 split, 2,000 test cycles, 3.4% failures; threshold tuned on a validation split, not test)**

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic regression (baseline, t=0.5) | 0.931 | 0.473 | 17.3% | 85.3% | 0.287 |
| HistGradientBoosting (t=0.86) | **0.967** | **0.891** | **93.2%** | **80.9%** | **0.866** |

GBM test confusion: 55 TP, 4 FP, 13 FN, 1,928 TN — catches 81% of failures with 4 false alarms in 2,000 cycles.
Caveat: AI4I is synthetic-but-realistic data; failures are partly rule-generated, so real lines would score lower.

## Screenshots
- `reports/figures/dashboard.png` — KPI dashboard
- `reports/figures/spc_p_chart.png` — SPC p-chart

## Tests
`pytest` — validation catches bad rows / schema errors, star schema row counts + KPI bounds, API predictions & 422 on bad input (4 tests passing).
