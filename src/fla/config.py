from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "ai4i2020.csv"
DB = ROOT / "data" / "warehouse.duckdb"
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"
MODEL = ROOT / "models" / "failure_model.joblib"
SHIFT_SIZE = 500          # consecutive cycles grouped into one "shift" (derived; dataset has no timestamps)
# Assumed repair minutes per failure mode (documented modelling assumption, not in source data)
DOWNTIME_MIN = {"TWF": 45, "HDF": 30, "PWF": 60, "OSF": 40, "RNF": 20}
SHIFT_MINUTES = 480
