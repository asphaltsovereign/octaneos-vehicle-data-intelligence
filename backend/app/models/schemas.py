from typing import Literal, Optional
from pydantic import BaseModel, Field


Severity = Literal["info", "low", "medium", "high", "critical"]


class EvidenceItem(BaseModel):
    signal: str
    observation: str
    value: Optional[float] = None
    direction: Literal["support", "contradict", "context"] = "context"


class Hypothesis(BaseModel):
    name: str
    subsystem: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = []
    contradictions: list[EvidenceItem] = []
    recommended_action: str
    blocked_claims: list[str] = []


class AnomalyRegion(BaseModel):
    start_index: int
    end_index: int
    start_time: str
    end_time: str
    score: float = Field(ge=0, le=1)
    top_signals: list[str]


class AnalysisSummary(BaseModel):
    session_id: str
    source_type: Literal["ved", "san"]
    sample_count: int
    quality_score: int
    analysis_ready: bool
    health_score: int
    risk: Severity
    anomaly_regions: list[AnomalyRegion]
    hypotheses: list[Hypothesis]
    limitations: list[str]
    metrics: dict
    model: dict
