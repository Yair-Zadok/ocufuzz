# Build the HTML report for failed runs.

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path

from ocufuzz.trace import TransitionTrace

RunResult = tuple[int, str, bool, TransitionTrace | None, str | None]

REPORT_CSS = """
body { margin: 0; background: #f6f7f9; color: #17202a; font: 16px/1.5 Inter, "Segoe UI", Arial, sans-serif; }
main { width: min(920px, calc(100% - 32px)); margin: 40px auto; }
header, .run, .empty { background: white; border: 1px solid #dce2ea; border-radius: 14px; padding: 18px; box-shadow: 0 10px 25px #141f300c; }
h1 { margin: 0 0 14px; font-size: clamp(2rem, 4vw, 3rem); letter-spacing: -.04em; }
h2 { margin: 0; font-size: 1.15rem; }
.meta, .details, .empty { color: #647083; }
.run, .empty { margin-top: 16px; }
.run-heading, .links { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.status, .issue { background: #fff1f0; color: #9f241b; border-radius: 8px; }
.status { border-radius: 999px; font-size: .82rem; font-weight: 700; padding: 4px 10px; }
.issue { border-left: 3px solid #9f241b; padding: 10px 12px; margin-bottom: 12px; }
.issue p { margin: 0 0 8px; }
a { color: #2456b3; font-weight: 700; text-decoration: none; }
img { max-width: 720px; width: 100%; height: auto; border: 1px solid #dce2ea; border-radius: 10px; margin-top: 10px; }
"""

SLIDESHOW_CSS = """
body { font: 16px/1.4 Arial, sans-serif; margin: 24px; }
img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 6px; }
li { margin-bottom: 18px; }
"""


# Format a run number as its artifact folder name.
def _run_label(run_num: int) -> str:
    return f"run_{run_num:02d}"


# Wrap body HTML in a complete styled document.
def _html_page(title: str, body: str, css: str = REPORT_CSS) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(title)}</title>
  <style>{css}</style>
</head>
<body>{body}</body>
</html>"""


# Collect distinct QA notes from a run trace.
def _unique_issue_notes(trace: TransitionTrace) -> list[str]:
    notes: list[str] = []
    for transition in trace.transitions:
        note = (transition.qa_observation or "").strip()
        if note and note not in notes:
            notes.append(note)
    return notes


# Write a screenshot slideshow for one run.
def _write_run_slideshow(run_dir: Path, trace: TransitionTrace, run_num: int) -> Path:
    slides = [
        f'<li><h3>{escape(f"After step {t.step}")}</h3><img src="{escape(t.after_screenshot)}" alt="{escape(f"After step {t.step}")}"></li>'
        for t in trace.transitions
        if t.after_screenshot
    ]
    body = f"<h1>Run {run_num:02d} slideshow</h1><ul>{''.join(slides) or '<li><p>No screenshots were captured for this run.</p></li>'}</ul>"
    out_path = run_dir / "slideshow.html"
    out_path.write_text(_html_page(f"Run {run_num:02d} slideshow", body, SLIDESHOW_CSS), encoding="utf-8")
    return out_path


# Render one failed run's report card.
def _failed_run_card(session_dir: Path, result: RunResult) -> str:
    run_num, status, _has_issue, trace, error_text = result
    label = _run_label(run_num)
    notes = [error_text or "Run errored before trace was available."] if status != "completed" else []
    notes += _unique_issue_notes(trace) if trace else []
    notes = notes or ["Run marked failed with no additional error text."]
    details = links = ""

    if trace:
        _write_run_slideshow(session_dir / label, trace, run_num)
        first_issue = next((t for t in trace.transitions if t.qa_observation), None)
        if first_issue:
            screenshot = f'{label}/{first_issue.after_screenshot}' if first_issue.after_screenshot else ""
            image = f'<div><img src="{escape(screenshot)}" alt="Run screenshot"></div>' if screenshot else ""
            details = f"<div><strong>URL:</strong> {escape(first_issue.url_after or '')}</div><div><strong>Action:</strong> {escape(first_issue.action_summary)}</div>{image}"
        links = f'<div><a href="{label}/slideshow.html">Open run slideshow</a></div>'

    issue_html = "".join(f"<p>{escape(note)}</p>" for note in notes)
    return f'<section class="run"><div class="run-heading"><h2>Run {run_num:02d}</h2><span class="status">Failed</span></div><div class="issue">{issue_html}</div><div class="details">{details}</div><div class="links">{links}</div></section>'


# Build the session report and return summary metrics.
def build_report(
    session_dir: Path,
    *,
    start_url: str,
    runs_requested: int,
    run_results: Sequence[RunResult],
) -> tuple[Path, int, int, int]:
    # Write report.html under session_dir and per-run slideshows.
    session_dir = Path(session_dir)
    failed = [r for r in run_results if r[1] != "completed" or r[2]]
    issue_count = sum(
        1 for *_prefix, trace, _error in run_results if trace for t in trace.transitions if t.qa_observation
    )
    successful_runs = sum(
        1
        for _n, status, _issue, trace, _error in run_results
        if status == "completed" and trace and not any(t.qa_observation for t in trace.transitions)
    )
    runs_completed = sum(1 for _n, status, _issue, _trace, _error in run_results if status == "completed")
    failed_html = "".join(_failed_run_card(session_dir, result) for result in failed) or '<p class="empty">No failed runs.</p>'
    body = f'<main><header><h1>{len(failed)} failed / {runs_requested} runs</h1><div class="meta"><div><strong>Session:</strong> {escape(session_dir.name)}</div><div><strong>Start URL:</strong> {escape(start_url)}</div><div><strong>Completed runs:</strong> {runs_completed}</div></div></header>{failed_html}</main>'

    report_path = session_dir / "report.html"
    report_path.write_text(_html_page("Fuzzing report", body), encoding="utf-8")
    return report_path, issue_count, successful_runs, runs_completed
