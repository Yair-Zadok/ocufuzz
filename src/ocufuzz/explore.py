# Outputs one exploration sequence to a caller-provided directory (browser-use).

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
MAXIMIZED_VIEW_SIZE = {"width": 1920, "height": 1080}
DEFAULT_AGENT_LLM_TIMEOUT_SECONDS = 120


def _ollama_model_name(model: str) -> str:
    if model.startswith(("ollama/", "ollama_chat/")):
        return model
    return f"ollama_chat/{model}"


def resolve_llm(
    model: str | None = None,
    provider: str | None = None,
) -> tuple[BaseChatModel, str, str]:
    """Pick the primary LLM. Defaults to local Ollama for credential-free runs."""
    chosen_provider = (provider or os.getenv("OCU_LLM_PROVIDER") or "ollama").lower()
    if chosen_provider == "ollama":
        chosen_model = model or os.getenv("OCU_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        base_url = os.getenv("OCU_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        return (
            ChatLiteLLM(
                model=_ollama_model_name(chosen_model),
                api_base=base_url,
                max_tokens=int(os.getenv("OCU_OLLAMA_MAX_TOKENS", "2048")),
                max_retries=int(os.getenv("OCU_OLLAMA_MAX_RETRIES", "2")),
            ),
            chosen_model,
            chosen_provider,
        )

    if chosen_provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("No Google credentials: set GOOGLE_API_KEY in the environment.")
        chosen_model = model or os.getenv("OCU_GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
        return ChatGoogle(model=chosen_model, thinking_budget=0), chosen_model, chosen_provider

    raise RuntimeError(
        f"Unsupported LLM provider '{chosen_provider}'. Use 'ollama' or 'google'."
    )


def resolve_fallback_llm(provider: str, primary_model: str) -> BaseChatModel | None:
    """Pick fallback model for provider errors like quota/rate limits."""
    if provider != "google":
        return None
    fallback_model = os.getenv("OCU_FALLBACK_GEMINI_MODEL", "gemini-3.1-flash-preview")
    if fallback_model == primary_model:
        return None
    return ChatGoogle(model=fallback_model, thinking_budget=0)


DEFAULT_TASK = (
    "You are a QA agent, you are testing a website for QA issues. Explore visible controls and form flows with short, targeted actions. "
    "Keep memory to one short sentence. Include 'QA: ...' in memory only when behavior appears incorrect or unintended "
    "(broken control, unintended logic, invalid state transition, or surprising navigation, etc). "
    "Do not include a QA note when no issue is observed."
)


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
    Run one `browser-use` agent session against ``start_url`` and write into ``artifacts_dir``.

    - ``run_history.json`` — serialized agent history
    - ``transitions.json`` — ocufuzz transition trace
    - ``conversation/`` — per-step conversation dumps when enabled

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

    browser_options: dict[str, object] = {
        "headless": headless,
        "args": ["--start-maximized"],
        "screen": MAXIMIZED_VIEW_SIZE,
        "viewport": MAXIMIZED_VIEW_SIZE,
        "window_size": MAXIMIZED_VIEW_SIZE,
    }

    browser = Browser(**browser_options)
    agent = Agent(
        task=full_task,
        llm=llm,
        llm_timeout=DEFAULT_AGENT_LLM_TIMEOUT_SECONDS,
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
    return root, trace
