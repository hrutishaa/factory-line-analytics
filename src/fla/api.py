"""FastAPI service: POST /predict returns failure probability for a machine cycle."""
import joblib, pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal
from .config import MODEL
from .model import features

app = FastAPI(title="Factory Line Failure Predictor")
_art = None
def art():
    global _art
    if _art is None: _art = joblib.load(MODEL)
    return _art

class Cycle(BaseModel):
    product_type: Literal["L", "M", "H"]
    air_temp_k: float = Field(gt=250, lt=350)
    process_temp_k: float = Field(gt=250, lt=360)
    rpm: float = Field(gt=0, lt=5000)
    torque_nm: float = Field(ge=0, lt=200)
    tool_wear_min: float = Field(ge=0)

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/predict")
def predict(c: Cycle):
    a = art(); X = features(pd.DataFrame([c.model_dump()]))
    p = float(a["model"].predict_proba(X)[0, 1])
    return {"failure_probability": round(p, 4), "alert": p >= a["threshold"], "threshold": a["threshold"]}
