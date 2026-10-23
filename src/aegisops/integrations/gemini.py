import logging
import time
from typing import Any

from google import genai

from aegisops.core.config import get_settings
from aegisops.observability.metrics import (
    GEMINI_REQUEST_DURATION,
    GEMINI_REQUESTS,
    GEMINI_TOKENS,
)
from aegisops.workflows.investigation import InvestigationResult
from aegisops.workflows.rca import RootCauseAnalysis
from aegisops.workflows.remediation import RemediationPlan

logger = logging.getLogger("aegisops.gemini")


class GeminiError(Exception):
    """Raised when incident investigation or RCA generation fails."""


def _record_gemini_tokens(stage: str, response: Any) -> None:
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        in_tok = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        out_tok = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        if in_tok:
            GEMINI_TOKENS.labels(stage=stage, token_type="input").inc(in_tok)
        if out_tok:
            GEMINI_TOKENS.labels(stage=stage, token_type="output").inc(out_tok)


def generate_investigation(prompt: str) -> InvestigationResult:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value()

    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    start_time = time.perf_counter()
    try:
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 1500,
                    "response_mime_type": "application/json",
                    "response_schema": InvestigationResult,
                },
            )

        duration = time.perf_counter() - start_time
        GEMINI_REQUEST_DURATION.labels(stage="investigation").observe(duration)

        if isinstance(response.parsed, InvestigationResult):
            GEMINI_REQUESTS.labels(stage="investigation", status="succeeded").inc()
            _record_gemini_tokens("investigation", response)
            return response.parsed

        GEMINI_REQUESTS.labels(stage="investigation", status="invalid_output").inc()
        raise GeminiError("Gemini returned an invalid investigation")

    except GeminiError:
        raise
    except Exception as exc:
        GEMINI_REQUESTS.labels(stage="investigation", status="failed").inc()
        raise GeminiError("Gemini investigation failed") from exc


def generate_rca(prompt: str) -> RootCauseAnalysis:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value()

    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    start_time = time.perf_counter()
    try:
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 3000,
                    "response_mime_type": "application/json",
                    "response_schema": RootCauseAnalysis,
                },
            )

        duration = time.perf_counter() - start_time
        GEMINI_REQUEST_DURATION.labels(stage="rca").observe(duration)

        if isinstance(response.parsed, RootCauseAnalysis):
            GEMINI_REQUESTS.labels(stage="rca", status="succeeded").inc()
            _record_gemini_tokens("rca", response)
            analysis = response.parsed
            # Enforce safety constraint: synthetic monitoring metrics cannot confirm root cause
            analysis.root_cause_confirmed = False
            analysis.requires_human_review = True
            return analysis

        GEMINI_REQUESTS.labels(stage="rca", status="invalid_output").inc()
        raise GeminiError("Gemini returned an invalid root cause analysis")

    except GeminiError:
        raise
    except Exception as exc:
        GEMINI_REQUESTS.labels(stage="rca", status="failed").inc()
        raise GeminiError("Gemini RCA generation failed") from exc


def generate_remediation_plan(prompt: str) -> RemediationPlan:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value()

    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    start_time = time.perf_counter()
    try:
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 3000,
                    "response_mime_type": "application/json",
                    "response_schema": RemediationPlan,
                },
            )

        duration = time.perf_counter() - start_time
        GEMINI_REQUEST_DURATION.labels(stage="remediation_planning").observe(duration)

        if isinstance(response.parsed, RemediationPlan):
            GEMINI_REQUESTS.labels(
                stage="remediation_planning", status="succeeded"
            ).inc()
            _record_gemini_tokens("remediation_planning", response)
            plan = response.parsed
            plan.requires_human_approval = True
            plan.execution_enabled = False
            for action in plan.recommended_actions:
                action.requires_human_approval = True
            return plan

        GEMINI_REQUESTS.labels(
            stage="remediation_planning", status="invalid_output"
        ).inc()
        raise GeminiError("Gemini returned an invalid remediation plan")

    except GeminiError:
        raise
    except Exception as exc:
        GEMINI_REQUESTS.labels(stage="remediation_planning", status="failed").inc()
        raise GeminiError("Gemini remediation planning failed") from exc
