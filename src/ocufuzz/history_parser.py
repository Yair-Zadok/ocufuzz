# Build `TransitionTrace` objects from browser-use agent history.

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from browser_use.agent.views import AgentHistoryList

from ocufuzz.trace import Transition, TransitionTrace


def _state_id(url: str | None, title: str | None) -> str:
    key = f"{url or ''}|{title or ''}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"s_{h}"


def _action_summary(actions: list[Any]) -> str:
    parts: list[str] = []
    for a in actions:
        try:
            parts.append(a.model_dump_json(exclude_none=True))
        except Exception:
            parts.append(repr(a))
    return "; ".join(parts) if parts else "(no actions)"


def _step_error(results: list[Any]) -> str | None:
    for result in results:
        error = getattr(result, "error", None)
        if error:
            return str(error)
    return None


def _extract_qa_note(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"QA:\s*(.+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    note = match.group(1).strip()
    return note or None


def _strip_qa_note(text: str | None) -> str | None:
    if not text:
        return None
    stripped = re.sub(r"\s*QA:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    return stripped or None


def _qa_severity(note: str | None) -> str | None:
    if not note:
        return None
    lowered = note.lower()
    if any(token in lowered for token in ("crash", "stuck", "blocked", "broken", "cannot", "can't", "error")):
        return "high"
    if any(token in lowered for token in ("unexpected", "wrong", "invalid", "mismatch", "inconsistent")):
        return "medium"
    return "low"


def transitions_from_agent_history(
    run_id: str,
    start_url: str,
    task: str,
    history: AgentHistoryList,
) -> TransitionTrace:
    # Convert every browser-use step into the trace rows used by reports.
    transitions: list[Transition] = []
    prev_url = start_url
    prev_title: str | None = None
    prev_shot: str | None = None

    for i, item in enumerate(history.history, start=1):
        mo = item.model_output
        state = item.state
        url_after = state.url
        title_after = state.title
        after_rel = _rel_path(state.screenshot_path)

        actions = list(mo.action) if mo is not None and mo.action else []
        error = _step_error(item.result)
        serialized: list[dict[str, Any]] = []
        for act in actions:
            try:
                serialized.append(act.model_dump(mode="json", exclude_none=True))
            except Exception:
                serialized.append({"repr": repr(act)})

        obs_parts: list[str] = []
        qa_observation: str | None = None
        if mo is not None:
            qa_observation = _extract_qa_note(mo.memory) or _extract_qa_note(mo.next_goal)
            clean_memory = _strip_qa_note(mo.memory)
            clean_goal = _strip_qa_note(mo.next_goal)
            if clean_memory:
                obs_parts.append(f"memory: {clean_memory}")
            if clean_goal:
                obs_parts.append(f"next_goal: {clean_goal}")
        observation = " | ".join(obs_parts) if obs_parts else None

        from_state = _state_id(prev_url, prev_title)
        to_state = _state_id(url_after, title_after)

        transitions.append(
            Transition(
                step=i,
                from_state=from_state,
                to_state=to_state,
                url_before=prev_url,
                url_after=url_after,
                title_after=title_after,
                before_screenshot=_rel_path(prev_shot) if prev_shot else None,
                after_screenshot=after_rel,
                action_summary=f"ERROR: {error}" if error else _action_summary(actions),
                model_actions=serialized,
                error=error,
                qa_observation=qa_observation,
                qa_severity=_qa_severity(qa_observation),
                suspected_bug=bool(qa_observation),
                observation=observation,
            )
        )

        prev_url = url_after
        prev_title = title_after
        prev_shot = state.screenshot_path

    return TransitionTrace(run_id=run_id, start_url=start_url, task=task, transitions=transitions)


def _rel_path(abs_or_rel: str | None) -> str | None:
    if not abs_or_rel:
        return None
    p = Path(abs_or_rel)
    try:
        cwd = Path.cwd()
        if p.is_absolute():
            s = str(p.relative_to(cwd)).replace("\\", "/")
        else:
            s = str(p).replace("\\", "/")
    except ValueError:
        s = str(p).replace("\\", "/")
    return s


def write_transitions(path: str | Path, trace: TransitionTrace) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(trace.to_json_dict(), indent=2), encoding="utf-8")
