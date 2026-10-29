"""Train failure-prediction model; honest metrics on held-out data."""
import json, joblib, duckdb, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_fscore_support, confusion_matrix
from .config import DB, MODEL, REPORTS

FEATURES = ["type_code", "air_temp_k", "process_temp_k", "rpm", "torque_nm", "tool_wear_min", "temp_delta_k", "power_w"]
TYPE = {"L": 0, "M": 1, "H": 2}

def features(df):
    df = df.copy()
    df["type_code"] = df.product_type.map(TYPE)
    df["temp_delta_k"] = df.process_temp_k - df.air_temp_k
    df["power_w"] = df.torque_nm * df.rpm * 2 * np.pi / 60
    return df[FEATURES]

def load():
    con = duckdb.connect(str(DB), read_only=True)
    return con.sql("SELECT f.*, p.product_type FROM fact_cycle f JOIN dim_product p USING(product_id) ORDER BY udi").df()

def evaluate(m, X, y, thr):
    p = m.predict_proba(X)[:, 1]; pred = (p >= thr).astype(int)
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "threshold": thr,
            "precision": pr, "recall": rc, "f1": f1, "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}

def run():
    df = load(); X, y = features(df), df.machine_failure.values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    Xfit, Xval, yfit, yval = train_test_split(Xtr, ytr, test_size=0.25, stratify=ytr, random_state=42)
    res = {"n_train": len(Xtr), "n_test": len(Xte), "test_failure_rate": float(yte.mean())}
    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")).fit(Xfit, yfit)
    gbm = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, class_weight="balanced", random_state=42).fit(Xfit, yfit)
    # choose threshold maximizing F1 on validation split (never on test)
    pv = gbm.predict_proba(Xval)[:, 1]
    thrs = np.linspace(0.05, 0.95, 91)
    f1s = [precision_recall_fscore_support(yval, (pv >= t).astype(int), average="binary", zero_division=0)[2] for t in thrs]
    thr = float(thrs[int(np.argmax(f1s))])
    res["baseline_logreg_test"] = evaluate(base, Xte, yte, 0.5)
    res["gbm_test"] = evaluate(gbm, Xte, yte, thr)
    final = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, class_weight="balanced", random_state=42).fit(Xtr, ytr)
    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump({"model": final, "threshold": thr, "features": FEATURES}, MODEL)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "model_metrics.json").write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=1, default=float)); return res

if __name__ == "__main__":
    run()
