import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DATASETS_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = DATASETS_DIR.parent / "scenarios"


class ScenarioModel(BaseModel):
    scenario_id: str
    name: str
    description: str
    synthetic: bool = True
    telemetry: dict[str, float | None]
    alert: dict[str, Any]
    expected: dict[str, Any]


class EdgeCaseModel(BaseModel):
    case_id: str
    name: str
    description: str
    category: str
    synthetic: bool = True
    input_incident: dict[str, Any] | None = None
    telemetry: dict[str, float | None] | None = None
    expected_routing: dict[str, Any] = Field(default_factory=dict)
    expected_safety: dict[str, Any] = Field(default_factory=dict)
    ground_truth_limitations: str = ""


def load_all_scenarios() -> list[ScenarioModel]:
    scenarios: list[ScenarioModel] = []
    for file_path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            scenarios.append(ScenarioModel.model_validate(data))
    return scenarios


def load_all_edge_cases() -> list[EdgeCaseModel]:
    edge_file = DATASETS_DIR / "edge_cases.json"
    if not edge_file.exists():
        return []
    with open(edge_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [EdgeCaseModel.model_validate(c) for c in data]
