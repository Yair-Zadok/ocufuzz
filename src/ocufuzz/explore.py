# Outputs one exploration sequence as a fresh browser-use agent.

from __future__ import annotations

import os
from pathlib import Path

from browser_use import Agent, Browser, ChatGoogle
from browser_use.llm.base import BaseChatModel
from browser_use.llm.litellm.chat import ChatLiteLLM

from ocufuzz.history_parser import transitions_from_agent_history, write_transitions
from ocufuzz.trace import TransitionTrace


DEFAULT_OLLAMA_MODEL = "qwen3.5:9b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_GOOGLE_MODEL = "gemini-flash-lite-latest"
FALLBACK_GOOGLE_MODEL = "gemini-flash-latest"
DEFAULT_OLLAMA_MAX_TOKENS = 2048
DEFAULT_OLLAMA_MAX_RETRIES = 2
DEFAULT_MAX_HISTORY_ITEMS = 10
DEFAULT_AGENT_LLM_TIMEOUT_SECONDS = 240


# Normalize an Ollama model name for LiteLLM.
def _ollama_model_name(model: str) -> str:
    if model.startswith(("ollama/", "ollama_chat/")):
        return model
    return f"ollama_chat/{model}"


# Resolve the configured primary LLM.
def resolve_llm(
    model: str | None = None,
    provider: str | None = None,
) -> tuple[BaseChatModel, str, str]:
    # Choose the model for a run, keeping local Ollama as the no-credentials default.
    chosen_provider = (provider or "ollama").lower()
    if chosen_provider == "ollama":
        chosen_model = model or DEFAULT_OLLAMA_MODEL
        base_url = os.getenv("OCU_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        return (
            ChatLiteLLM(
                model=_ollama_model_name(chosen_model),
                api_base=base_url,
                max_tokens=DEFAULT_OLLAMA_MAX_TOKENS,
                max_retries=DEFAULT_OLLAMA_MAX_RETRIES,
            ),
            chosen_model,
            chosen_provider,
        )

    if chosen_provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("No Google credentials: set GOOGLE_API_KEY in the environment.")
        chosen_model = model or DEFAULT_GOOGLE_MODEL
        return ChatGoogle(model=chosen_model), chosen_model, chosen_provider

    raise RuntimeError(
        f"Unsupported LLM provider '{chosen_provider}'. Use 'ollama' or 'google'."
    )


# Resolve a fallback LLM for supported providers.
def resolve_fallback_llm(provider: str, primary_model: str) -> BaseChatModel | None:
    # Use a second Google model when the primary one hits provider limits.
    if provider != "google":
        return None
    if FALLBACK_GOOGLE_MODEL == primary_model:
        return None
    return ChatGoogle(model=FALLBACK_GOOGLE_MODEL)


DEFAULT_TASK = (
    "You are a QA agent, you are testing a website for QA issues. Explore visible controls and form flows with short, targeted actions. "
    "Include 'QA: ...' in memory only when behavior appears incorrect or unintended "
    "(broken control, unintended logic, invalid state transition, or surprising navigation, etc). "
    "Do not include a QA note when no issue is observed."
)


# Run one browser-use exploration and write artifacts.
async def run_exploration(
    start_url: str,
    *,
    artifacts_dir: Path,
    task: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    max_steps: int = 12,
    headless: bool | None = True,
    save_conversation: bool = False,
    prior_summary: str | None = None,
) -> tuple[Path, TransitionTrace]:
    """
    Run one browser-use agent against ``start_url`` and collect the run output.

    Each run writes the browser-use history, the ocufuzz transition trace, and
    optional per-step conversation dumps into ``artifacts_dir``.

    Returns ``(artifacts_dir, trace)``.
    """
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    run_id = root.name
    conv_dir = root / "conversation"
    if save_conversation:
        conv_dir.mkdir(parents=True, exist_ok=True)

    llm, primary_model, llm_provider = resolve_llm(model=model, provider=provider)
    fallback_llm = resolve_fallback_llm(llm_provider, primary_model)
    task_text = task or DEFAULT_TASK
    full_task = f"Start at URL: {start_url}\n\n{task_text}"

    if prior_summary and prior_summary.strip():
        prior_block = (
            "Previous QA agents already explored this site. Try different areas and interactions to find new issues.\n"
            + prior_summary.strip()
        )
        full_task = f"{full_task}\n\n{prior_block}"

    browser = Browser(headless=headless, args=["--start-maximized"])
    agent = Agent(
        task=full_task,
        llm=llm,
        llm_timeout=DEFAULT_AGENT_LLM_TIMEOUT_SECONDS,
        flash_mode=False,
        use_thinking=True,
        max_history_items=DEFAULT_MAX_HISTORY_ITEMS,
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
    return root, trace
