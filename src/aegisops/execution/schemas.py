from typing import Any, Literal

from pydantic import BaseModel, Field


class SimulationResult(BaseModel):
    operation_id: str
    mode: Literal["simulation"] = "simulation"
    parameters: dict[str, Any]
    intended_purpose: str
    target_scope: str
    expected_observations: list[str]
    risk_assessment: str
    actual_infrastructure_access: bool = False
    system_changes_performed: bool = False
    dry_run: bool = True
    status: Literal["simulated_success", "simulated_failed"] = "simulated_success"
    simulated_output: dict[str, Any] = Field(default_factory=dict)
