from aegisops.core.config import get_settings
from evaluation.runners.evaluate_cost import (
    OFFICIAL_PRICING_REFERENCE,
    calculate_stage_cost,
    run_cost_evaluation,
)


def test_cost_calculation_math():
    pricing = {"input_per_million": 0.10, "output_per_million": 0.40}
    # 1,000,000 in, 1,000,000 out => 0.10 + 0.40 = 0.50
    cost = calculate_stage_cost(1_000_000, 1_000_000, pricing)
    assert cost == 0.50

    # 10,000 in, 5,000 out => (0.01 * 0.10) + (0.005 * 0.40) = 0.001 + 0.002 = 0.003
    cost = calculate_stage_cost(10_000, 5_000, pricing)
    assert cost == 0.003

    # Unavailable pricing returns None
    assert calculate_stage_cost(10_000, 5_000, None) is None


def test_evaluate_cost_configured_model(monkeypatch):
    # Test reading actual configured model from settings
    settings = get_settings()
    assert settings.gemini_model == "gemini-3.5-flash-lite"

    result = run_cost_evaluation()
    assert result["target_model"] == "gemini-3.5-flash-lite"
    assert result["usage_source"] == "estimated"
    # Configured model gemini-3.5-flash-lite does not have public verified rate card
    assert result["pricing_available"] is False
    assert result["cost_status"] == "UNAVAILABLE"
    assert result["estimated_cost_per_incident_workflow_usd"] is None
    assert result["estimated_cost_per_1000_incidents_usd"] is None
    assert len(result["limitations"]) >= 1
    assert "gemini-3.5-flash-lite" in result["limitations"][0]
    assert result["status"] == "PASSED"


def test_evaluate_cost_verified_model():
    result = run_cost_evaluation(target_model="gemini-1.5-flash")
    assert result["target_model"] == "gemini-1.5-flash"
    assert result["pricing_available"] is True
    assert result["cost_status"] == "CALCULATED"
    assert (
        result["model_rates_per_million_usd"]
        == (OFFICIAL_PRICING_REFERENCE["verified_models"]["gemini-1.5-flash"])
    )
    assert result["estimated_cost_per_incident_workflow_usd"] is not None
    assert result["estimated_cost_per_incident_workflow_usd"] > 0
    assert result["status"] == "PASSED"


def test_evaluate_cost_measured_tokens():
    measured = {
        "investigation": {"input": 1200, "output": 600},
        "root_cause_analysis": {"input": 2000, "output": 1000},
        "remediation_planning": {"input": 2500, "output": 1100},
    }
    result = run_cost_evaluation(
        target_model="gemini-2.0-flash",
        measured_tokens=measured,
        mode="live",
    )
    assert result["usage_source"] == "measured"
    assert result["evaluation_mode"] == "live"
    assert result["token_totals"]["input_tokens"] == 1200 + 2000 + 2500
    assert result["token_totals"]["output_tokens"] == 600 + 1000 + 1100
    assert result["stage_breakdown"]["investigation"]["usage_source"] == "measured"
    assert result["estimated_cost_per_incident_workflow_usd"] is not None
