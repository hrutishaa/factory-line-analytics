import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
import pandas as pd, pytest, duckdb
from fla import pipeline
from fla.config import DB, MODEL

def test_validate_flags_bad_rows():
    df = pipeline.extract().head(50).copy()
    df.loc[0, "rpm"] = -5; df.loc[1, "product_type"] = "X"
    clean, issues = pipeline.validate(df)
    assert issues["out_of_range"] == 2 and len(clean) == 48

def test_validate_missing_column():
    with pytest.raises(ValueError):
        pipeline.validate(pipeline.extract().drop(columns=["rpm"]))

def test_star_schema_and_kpis():
    con = duckdb.connect(str(DB), read_only=True)
    assert con.execute("SELECT COUNT(*) FROM fact_cycle").fetchone()[0] == 10000
    lo, hi = con.execute("SELECT MIN(oee), MAX(oee) FROM v_shift_oee").fetchone()
    assert 0 <= lo <= hi <= 1
    assert con.execute("SELECT SUM(events) FROM v_downtime_pareto").fetchone()[0] == \
           con.execute("SELECT COUNT(*) FROM fact_failure_event").fetchone()[0]

def test_api_predict():
    from fastapi.testclient import TestClient
    from fla.api import app
    c = TestClient(app)
    ok = {"product_type": "L", "air_temp_k": 298, "process_temp_k": 308.6, "rpm": 1500, "torque_nm": 40, "tool_wear_min": 10}
    bad = dict(ok, rpm=1250, torque_nm=70, tool_wear_min=220)
    a, b = c.post("/predict", json=ok).json(), c.post("/predict", json=bad).json()
    assert a["failure_probability"] < b["failure_probability"]
    assert c.post("/predict", json=dict(ok, rpm=-1)).status_code == 422
