"""Ingest + validate AI4I 2020 into a DuckDB star schema."""
import duckdb, pandas as pd
from .config import RAW, DB, SHIFT_SIZE, DOWNTIME_MIN

COLS = {"UDI":"udi","Product ID":"product_id","Type":"product_type","Air temperature [K]":"air_temp_k",
        "Process temperature [K]":"process_temp_k","Rotational speed [rpm]":"rpm","Torque [Nm]":"torque_nm",
        "Tool wear [min]":"tool_wear_min","Machine failure":"machine_failure"}
MODES = list(DOWNTIME_MIN)

def extract(path=RAW):
    return pd.read_csv(path).rename(columns=COLS)

def validate(df):
    """Return (clean_df, issues dict). Raises on schema errors."""
    req = list(COLS.values()) + MODES
    missing = [c for c in req if c not in df]
    if missing: raise ValueError(f"missing columns {missing}")
    issues = {"rows_in": len(df), "null_rows": int(df[req].isna().any(axis=1).sum()),
              "dup_udi": int(df.udi.duplicated().sum())}
    rng = (df.air_temp_k.between(250, 350) & df.process_temp_k.between(250, 360) & df.rpm.between(0, 5000)
           & df.torque_nm.between(0, 200) & (df.tool_wear_min >= 0) & df.product_type.isin(list("LMH")))
    issues["out_of_range"] = int((~rng).sum())
    # Known AI4I quirk: machine_failure flag inconsistent with failure-mode flags
    anymode = df[MODES].max(axis=1)
    issues["label_inconsistent"] = int((anymode != df.machine_failure).sum())
    clean = df[rng & ~df.udi.duplicated()].dropna(subset=req).copy()
    issues["rows_out"] = len(clean)
    return clean, issues

def transform(df):
    df = df.sort_values("udi").copy()
    df["shift_id"] = (df.udi - 1) // SHIFT_SIZE + 1
    # cycle time proxy: positive increment of cumulative tool-wear minutes between consecutive cycles
    d = df.tool_wear_min.diff()
    df["cycle_time_min"] = d.where(d > 0)
    df["downtime_min"] = sum(df[m] * v for m, v in DOWNTIME_MIN.items())
    df["temp_delta_k"] = df.process_temp_k - df.air_temp_k
    df["power_w"] = df.torque_nm * df.rpm * 2 * 3.141592653589793 / 60
    return df

def load(df, db=DB):
    con = duckdb.connect(str(db))
    con.register("src", df)
    con.execute("""
    CREATE OR REPLACE TABLE dim_product AS SELECT DISTINCT product_id, product_type FROM src;
    CREATE OR REPLACE TABLE dim_shift AS SELECT DISTINCT shift_id FROM src ORDER BY 1;
    CREATE OR REPLACE TABLE dim_failure_mode AS SELECT * FROM (VALUES
      ('TWF','Tool wear failure',45),('HDF','Heat dissipation failure',30),('PWF','Power failure',60),
      ('OSF','Overstrain failure',40),('RNF','Random failure',20)) t(mode_code, mode_name, repair_min);
    CREATE OR REPLACE TABLE fact_cycle AS SELECT udi, product_id, shift_id, air_temp_k, process_temp_k,
      temp_delta_k, rpm, torque_nm, power_w, tool_wear_min, cycle_time_min, machine_failure,
      TWF, HDF, PWF, OSF, RNF, downtime_min FROM src;
    CREATE OR REPLACE TABLE fact_failure_event AS
      SELECT udi, shift_id, mode_code FROM (
        UNPIVOT (SELECT udi, shift_id, TWF, HDF, PWF, OSF, RNF FROM src)
        ON TWF, HDF, PWF, OSF, RNF INTO NAME mode_code VALUE flag) WHERE flag = 1;
    """)
    from .kpis import create_views
    create_views(con)
    con.close()

def run():
    raw = extract()
    clean, issues = validate(raw)
    load(transform(clean))
    print("validation:", issues)
    return issues

if __name__ == "__main__":
    run()
