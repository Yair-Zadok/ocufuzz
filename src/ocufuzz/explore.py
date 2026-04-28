# Outputs testing sequences to artifacts/explore/run_id/ by using browser-use to walk the website and collect screenshots of the website at each step.

from __future__ import annotations

import os
import uuid
from pathlib import Path

from browser_use import Agent, Browser, ChatGoogle

from ocufuzz.history_parser import transitions_from_agent_history, write_transitions


def resolve_llm():
    """Pick an LLM: Gemini 3.1 Flash-Lite with minimal thinking by default."""
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogle(
            model=os.getenv("OCU_GEMINI_MODEL", "gemini-3-flash-preview"),
            thinking_budget=0,
        )
    raise RuntimeError(
        "No LLM credentials: set GOOGLE_API_KEY in the environment."
    )


DEFAULT_TASK = (
    "Explore this page thoroughly for QA. Interact with visible buttons, links, and form controls. "
    "Use plausible sample text in fields. Aim to reveal at least two distinct on-screen states, "
    "then finish with the done action and briefly summarize what you saw. You are a fuzzing agent, try to find weird or unexpected control flows"
)


async def run_exploration(
    start_url: str,
    *,
    task: str | None = None,
    max_steps: int = 12,
    artifacts_root: str | Path = "artifacts/explore",
    headless: bool | None = True,
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
    conv_dir.mkdir(parents=True, exist_ok=True)

    llm = resolve_llm()
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
        browser=browser,
        save_conversation_path=str(conv_dir),
        use_vision=False,
        vision_detail_level="low",
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
