from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    code_change = "code_change"
    payment = "payment"
    code_and_payment = "code_and_payment"
    ops = "ops"
    custom = "custom"


class Verdict(str, Enum):
    SAFE = "SAFE"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    BLOCKED = "BLOCKED"


class PaymentRequest(BaseModel):
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=8)
    recipient: str
    invoice_reference: str | None = None


class Constraints(BaseModel):
    max_risk_score: int = Field(100, ge=0, le=100)
    require_citations: bool = False


class EvaluateRequest(BaseModel):
    task_type: TaskType
    action_summary: str = Field(..., min_length=3, max_length=8000)
    repository_url: str | None = None
    repository_ref: str | None = None
    diff_text: str | None = None
    policy_urls: list[str] = Field(default_factory=list)
    documentation_urls: list[str] = Field(default_factory=list)
    payment_request: PaymentRequest | None = None
    constraints: Constraints = Field(default_factory=Constraints)


class EvaluateResponse(BaseModel):
    run_id: str
    status: Verdict
    risk_score: int = Field(..., ge=0, le=100)
    summary: str
    reasons: list[str]
    safer_alternative: str
    context_assessment: dict[str, Any]
    code_assessment: dict[str, Any]
    payment_assessment: dict[str, Any]
    llm_synthesis: dict[str, Any]
    timings: dict[str, Any]
