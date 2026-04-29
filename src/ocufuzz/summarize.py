# Compact one-line summaries of a transition trace for prior-run context.

from __future__ import annotations

from urllib.parse import urlparse

from ocufuzz.trace import TransitionTrace

MAX_PRIOR_SUMMARY_CHARS = 4000


def _url_path(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or "/"
    return path if path else "/"


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def summarize_run(trace: TransitionTrace) -> str:
    """One compact line: visited paths, titles, issue texts (no step/issue counts)."""
    paths_ordered: list[str] = []
    seen_paths: set[str] = set()
    start_path = _url_path(trace.start_url)
    if start_path:
        paths_ordered.append(start_path)
        seen_paths.add(start_path)
    for t in trace.transitions:
        p = _url_path(t.url_after)
        if p and p not in seen_paths:
            seen_paths.add(p)
            paths_ordered.append(p)

    max_paths = 5
    path_parts = paths_ordered[:max_paths]
    if len(paths_ordered) > max_paths:
        path_parts.append(f"+{len(paths_ordered) - max_paths} more")
    paths_str = ", ".join(path_parts) if path_parts else "(none)"

    titles_ordered: list[str] = []
    seen_titles: set[str] = set()
    for t in trace.transitions:
        title = (t.title_after or "").strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            titles_ordered.append(title)
    max_titles = 3
    title_parts = titles_ordered[:max_titles]
    if len(titles_ordered) > max_titles:
        title_parts.append(f"+{len(titles_ordered) - max_titles} more")
    titles_str = ", ".join(title_parts) if title_parts else "(none)"

    issues: list[str] = []
    seen_issue: set[str] = set()
    for t in trace.transitions:
        if t.qa_observation:
            note = t.qa_observation.strip()
            if note and note not in seen_issue:
                seen_issue.add(note)
                issues.append(_truncate(note, 160))

    if not issues:
        issues_part = "no issues"
    else:
        joined = "; ".join(issues)
        issues_part = _truncate(joined, 220)

    line = f"visited {paths_str}; titles: {titles_str}; issues: {issues_part}"
    return _truncate(line, 420)


def build_prior_summary(summaries: list[tuple[int, str]]) -> str | None:
    """Build one prompt summary string and cap total chars."""
    if not summaries:
        return None
    full = "\n".join(f"Run {n}: {summary}" for n, summary in summaries).strip()
    if not full:
        return None
    if len(full) <= MAX_PRIOR_SUMMARY_CHARS:
        return full
    return full[-MAX_PRIOR_SUMMARY_CHARS:]
