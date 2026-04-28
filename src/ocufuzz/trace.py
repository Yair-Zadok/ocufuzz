# Classes for transition trace for exploration runs

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Transition(BaseModel):
    """One exploration step: inferred move from one UI state to another."""

    step: int = Field(..., ge=1, description="1-based step index after an agent decision.")
    from_state: str = Field(..., description="Stable id for the prior UI state.")
    to_state: str = Field(..., description="Stable id for the UI state after actions.")
    url_before: str | None = Field(None, description="URL before this step's actions.")
    url_after: str | None = Field(None, description="URL after this step's actions.")
    title_after: str | None = Field(None, description="Page title after this step.")
    before_screenshot: str | None = Field(
        None, description="Relative path to screenshot before step, if any."
    )
    after_screenshot: str | None = Field(
        None, description="Relative path to screenshot after step, if any."
    )
    action_summary: str = Field(..., description="Human-readable summary of chosen actions.")
    model_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Serialized agent actions for this step."
    )
    error: str | None = Field(None, description="Agent or model error for this step.")
    observation: str | None = Field(
        None,
        description="Agent memory / next goal text useful for graph labels.",
    )


class TransitionTrace(BaseModel):
    """Full trace for one `browser-use` exploration run."""

    run_id: str
    start_url: str
    task: str
    transitions: list[Transition] = Field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
