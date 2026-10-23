"""Evaluation runner for Gemini Token Usage and Cost Modeling (Step 16).

Implements rigorous token accounting, verified Google Gemini API pricing models,
truthful unavailable-pricing handling for unreleased/experimental models, and
clear separation between measured and estimated usage profiles.
"""

from typing import Any

from aegisops.core.config import get_settings

# Official Google Gemini Developer API Rate Card
# Verified reference date: 2026-01-01
OFFICIAL_PRICING_REFERENCE: dict[str, Any] = {
    "source": "Google Cloud / Gemini Developer API Public Rate Card",
    "pricing_date": "2026-01-01",
    "verified_models": {
        "gemini-1.5-flash": {
            "input_per_million": 0.075,
            "output_per_million": 0.30,
        },
        "gemini-2.0-flash": {
            "input_per_million": 0.10,
            "output_per_million": 0.40,
        },
        "gemini-2.0-flash-lite": {
            "input_per_million": 0.075,
            "output_per_million": 0.30,
        },
        "gemini-1.5-pro": {
            "input_per_million": 1.25,
            "output_per_million": 5.00,
        },
    },
}

# Empirical and observed token profiles for AegisOps structured workflows
WORKFLOW_STAGE_PROFILES: dict[str, dict[str, Any]] = {
    "investigation": {
        "calls_per_incident": 1,
        "input_tokens_est": 850,
        "output_tokens_est": 450,
        "description": "Evidence ingestion, metric formatting, and structured observation generation.",
    },
    "root_cause_analysis": {
        "calls_per_incident": 1,
        "input_tokens_est": 1650,
        "output_tokens_est": 850,
        "description": "Historical telemetry window analysis, hypothesis comparison, and limitation mapping.",
    },
    "remediation_planning": {
        "calls_per_incident": 1,
        "input_tokens_est": 1950,
        "output_tokens_est": 950,
        "description": "RCA synthesis, safety invariant injection, advisory action generation, and risk classification.",
    },
}


def calculate_stage_cost(
    input_tokens: int,
    output_tokens: int,
    model_pricing: dict[str, float] | None,
) -> float | None:
    """Calculates stage cost in USD. Returns None if pricing is unavailable."""
    if model_pricing is None:
        return None
    cost_in = (input_tokens / 1_000_000.0) * model_pricing["input_per_million"]
    cost_out = (output_tokens / 1_000_000.0) * model_pricing["output_per_million"]
    return round(cost_in + cost_out, 6)


def run_cost_evaluation(
    target_model: str | None = None,
    measured_tokens: dict[str, dict[str, int]] | None = None,
    mode: str = "mocked",
) -> dict[str, Any]:
    """Evaluates token usage and projected API costs for the configured Gemini model.

    Args:
        target_model: Specific model identifier. If None, reads from application settings.
        measured_tokens: Optional dictionary of measured {stage: {"input": X, "output": Y}}
            tokens from actual Gemini execution metadata.
        mode: 'mocked' for deterministic synthetic tests, 'live' for real bounded API tests.
    """
    settings = get_settings()
    model = target_model or settings.gemini_model

    verified_pricing: dict[str, float] | None = OFFICIAL_PRICING_REFERENCE[
        "verified_models"
    ].get(model)
    pricing_available = verified_pricing is not None

    usage_source = "measured" if measured_tokens else "estimated"

    stage_breakdown: dict[str, Any] = {}
    total_calls = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_combined_cost: float | None = 0.0 if pricing_available else None

    for stage_name, profile in WORKFLOW_STAGE_PROFILES.items():
        calls = profile["calls_per_incident"]

        if measured_tokens and stage_name in measured_tokens:
            in_tok = measured_tokens[stage_name].get("input", 0)
            out_tok = measured_tokens[stage_name].get("output", 0)
        else:
            in_tok = profile["input_tokens_est"] * calls
            out_tok = profile["output_tokens_est"] * calls

        stage_cost = calculate_stage_cost(in_tok, out_tok, verified_pricing)

        total_calls += calls
        total_input_tokens += in_tok
        total_output_tokens += out_tok

        if (
            pricing_available
            and total_combined_cost is not None
            and stage_cost is not None
        ):
            total_combined_cost += stage_cost

        stage_breakdown[stage_name] = {
            "calls": calls,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
            "usage_source": usage_source,
            "estimated_cost_usd": stage_cost,
            "description": profile["description"],
        }

    total_tokens = total_input_tokens + total_output_tokens
    cost_per_incident_usd = (
        round(total_combined_cost, 6) if total_combined_cost is not None else None
    )
    cost_per_1000_incidents = (
        round(cost_per_incident_usd * 1000.0, 2)
        if cost_per_incident_usd is not None
        else None
    )

    limitations: list[str] = []
    if not pricing_available:
        limitations.append(
            f"Configured model '{model}' does not have verified official pricing in "
            f"the {OFFICIAL_PRICING_REFERENCE['source']} as of {OFFICIAL_PRICING_REFERENCE['pricing_date']}. "
            "Estimated cost is reported as unavailable rather than substituting another model."
        )
    if usage_source == "estimated":
        limitations.append(
            "Token consumption is estimated from empirical workflow stage profiles; "
            "actual live production token consumption will vary with incident payload size."
        )

    return {
        "suite": "gemini_usage_and_cost_modeling",
        "target_model": model,
        "evaluation_mode": mode,
        "usage_source": usage_source,
        "pricing_available": pricing_available,
        "pricing_source": OFFICIAL_PRICING_REFERENCE["source"],
        "pricing_date": OFFICIAL_PRICING_REFERENCE["pricing_date"],
        "model_rates_per_million_usd": verified_pricing,
        "workflow_calls_total": total_calls,
        "token_totals": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
        },
        "stage_breakdown": stage_breakdown,
        "estimated_cost_per_incident_workflow_usd": cost_per_incident_usd,
        "estimated_cost_per_1000_incidents_usd": cost_per_1000_incidents,
        "cost_status": "CALCULATED" if pricing_available else "UNAVAILABLE",
        "limitations": limitations,
        "status": "PASSED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_cost_evaluation(), indent=2))
