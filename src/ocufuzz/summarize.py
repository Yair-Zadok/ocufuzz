# Summarizes finished runs so later agents can avoid repeating the same path.

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from ocufuzz.trace import TransitionTrace

MAX_PRIOR_SUMMARY_CHARS = 4000


# Extract the path portion of a URL.
def _url_path(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or "/"
    return path if path else "/"


# Trim text to a maximum display length.
def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


# Return non-empty values once, preserving order.
def _unique(values: Iterable[str | None]) -> list[str]:
    items: list[str] = []
    for value in values:
        value = (value or "").strip()
        if value and value not in items:
            items.append(value)
    return items


# Format a limited list with a "+N more" suffix.
def _limited(values: list[str], max_items: int) -> str:
    parts = values[:max_items]
    if len(values) > max_items:
        parts.append(f"+{len(values) - max_items} more")
    return ", ".join(parts) if parts else "(none)"


# Summarize one run for future prompts.
def summarize_run(trace: TransitionTrace) -> str:
    paths = _unique([_url_path(trace.start_url), *[_url_path(t.url_after) for t in trace.transitions]])
    titles = _unique(t.title_after for t in trace.transitions)
    issues = [_truncate(note, 160) for note in _unique(t.qa_observation for t in trace.transitions)]
    issue_text = _truncate("; ".join(issues), 220) if issues else "no issues"
    return _truncate(f"visited {_limited(paths, 5)}; titles: {_limited(titles, 3)}; issues: {issue_text}", 420)


# Join previous run notes without letting the prompt grow without bound.
def build_prior_summary(summaries: list[tuple[int, str]]) -> str | None:
    if not summaries:
        return None
    full = "\n".join(f"Run {n}: {summary}" for n, summary in summaries).strip()
    if not full:
        return None
    if len(full) <= MAX_PRIOR_SUMMARY_CHARS:
        return full
    return full[-MAX_PRIOR_SUMMARY_CHARS:]
