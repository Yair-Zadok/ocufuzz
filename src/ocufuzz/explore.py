# Outputs testing sequences to artifacts/explore/run_id/ by using browser-use to walk the website and collect screenshots of the website at each step.

from __future__ import annotations

import os
import uuid
from pathlib import Path

from browser_use import Agent, Browser, ChatGoogle

from ocufuzz.history_parser import transitions_from_agent_history, write_transitions


def resolve_llm(model: str | None = None) -> tuple[ChatGoogle, str]:
    """Pick the primary LLM with minimal thinking by default."""
    if os.getenv("GOOGLE_API_KEY"):
        chosen_model = model or os.getenv("OCU_GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
        return ChatGoogle(model=chosen_model, thinking_budget=0), chosen_model
    raise RuntimeError(
        "No LLM credentials: set GOOGLE_API_KEY in the environment."
    )


def resolve_fallback_llm(primary_model: str) -> ChatGoogle | None:
    """Pick fallback model for provider errors like quota/rate limits."""
    fallback_model = os.getenv("OCU_FALLBACK_GEMINI_MODEL", "gemini-3.1-flash-preview")
    if fallback_model == primary_model:
        return None
    return ChatGoogle(model=fallback_model, thinking_budget=0)


DEFAULT_TASK = (
    "Explore visible controls and form flows with short, targeted actions. "
    "Reveal at least two distinct UI states, then call done. "
    "Keep memory to one short sentence. Include 'QA: ...' in memory only when behavior appears incorrect or unintended "
    "(broken control, invalid state transition, bad validation, or surprising navigation, etc). "
    "Do not include a QA note when no issue is observed."
)


async def run_exploration(
    start_url: str,
    *,
    task: str | None = None,
    model: str | None = None,
    max_steps: int = 12,
    artifacts_root: str | Path = "artifacts/explore",
    headless: bool | None = True,
    save_conversation: bool = False,
) -> Path:
    """
    Run one `browser-use` agent session against ``start_url`` and write:

    - ``run_history.json`` — serialized agent history
    - ``transitions.json`` — ocufuzz transition trace
    - ``conversation/`` — per-step conversation dumps when enabled
    """
    run_id = uuid.uuid4().hex[:10]
    root = Path(artifacts_root) / run_id
    root.mkdir(parents=True, exist_ok=True)
    conv_dir = root / "conversation"
    if save_conversation:
        conv_dir.mkdir(parents=True, exist_ok=True)

    llm, primary_model = resolve_llm(model=model)
    fallback_llm = resolve_fallback_llm(primary_model)
    task_text = task or DEFAULT_TASK
    full_task = f"Start at URL: {start_url}\n\n{task_text}"

    browser = Browser(
        headless=headless,
        viewport={"width": 1280, "height": 900},
        window_size={"width": 1280, "height": 900},
    )
    agent = Agent(
        task=full_task,
        llm=llm,
        flash_mode=True,
        use_thinking=False,
        max_history_items=int(os.getenv("OCU_MAX_HISTORY_ITEMS", "10")),
        browser=browser,
        fallback_llm=fallback_llm,
        save_conversation_path=str(conv_dir) if save_conversation else None,
        use_vision=True,
    )

    history = await agent.run(max_steps=max_steps)
    history.save_to_file(root / "run_history.json")

    trace = transitions_from_agent_history(
        run_id=run_id,
        start_url=start_url,
        task=task_text,
        history=history,
    )
    write_transitions(root / "transitions.json", trace)
    return root
