# app/models.py
from __future__ import annotations
from pydantic   import BaseModel, Field, field_validator
from datetime   import datetime, timezone
from typing     import Optional
import uuid

class PredictionRequest(BaseModel):
    model_name : str   = Field(..., min_length=1, max_length=100, examples=["xgboost-v1"])
    features   : dict  = Field(..., description="Feature key-value pairs")
    threshold  : float = Field(0.5, ge=0.0, le=1.0)
    metadata   : Optional[dict] = None

    @field_validator("features")
    @classmethod
    def features_not_empty(cls, v):
        if not v:
            raise ValueError("features dict must not be empty")
        return v

class PredictionResponse(BaseModel):
    id           : str      = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name   : str
    prediction   : float    = Field(..., ge=0.0, le=1.0)
    label        : str
    confidence   : float
    threshold    : float
    created_at   : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
