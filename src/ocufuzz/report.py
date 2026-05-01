# Build the HTML report for failed runs.

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path

from ocufuzz.trace import TransitionTrace


def _run_label(run_num: int) -> str:
    return f"run_{run_num:02d}"


def _report_shot_path(run_num: int, run_relative_path: str | None) -> str | None:
    if not run_relative_path:
        return None
    return f"{_run_label(run_num)}/{run_relative_path}"


def _collect_issue_lines(trace: TransitionTrace) -> list[str]:
    lines: list[str] = []
    for transition in trace.transitions:
        if transition.qa_observation:
            text = transition.qa_observation.strip()
            if text and text not in lines:
                lines.append(text)
    return lines


def _write_run_slideshow(run_dir: Path, trace: TransitionTrace, run_num: int) -> Path:
    slides: list[tuple[str, str]] = []
    for transition in trace.transitions:
        if transition.after_screenshot:
            after = transition.after_screenshot
            assert after is not None
            slides.append((after, f"After step {transition.step}"))

    slide_items = "\n".join(
        f"<li><h3>{escape(caption)}</h3><img src=\"{escape(path)}\" alt=\"{escape(caption)}\"></li>"
        for path, caption in slides
    )
    if not slide_items:
        slide_items = "<li><p>No screenshots were captured for this run.</p></li>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Run {run_num:02d} slideshow</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.4; }}
    img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 6px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 18px; }}
  </style>
</head>
<body>
  <h1>Run {run_num:02d} slideshow</h1>
  <ul>{slide_items}</ul>
</body>
</html>
"""
    out_path = run_dir / "slideshow.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def build_report(
    session_dir: Path,
    *,
    start_url: str,
    runs_requested: int,
    run_results: Sequence[tuple[int, str, bool, TransitionTrace | None, str | None]],
) -> tuple[Path, int, int, int]:
    # Write report.html under session_dir and per-run slideshows.
    session_dir = Path(session_dir)

    all_issues: list[dict[str, object]] = []
    for run_num, status, _has_issue, trace, _error_text in run_results:
        if trace is None:
            continue
        for t in trace.transitions:
            if not t.qa_observation:
                continue
            all_issues.append(
                {
                    "run": run_num,
                    "step": t.step,
                    "url": t.url_after or "",
                    "severity": t.qa_severity or "",
                    "observation": t.qa_observation,
                    "action_summary": t.action_summary,
                    "screenshot": t.after_screenshot or "",
                }
            )

    successful_runs = 0
    for _run_num, status, _has_issue, trace, _error_text in run_results:
        if status != "completed" or trace is None:
            continue
        if not any(t.qa_observation for t in trace.transitions):
            successful_runs += 1

    runs_completed = sum(1 for _, st, _, _, _ in run_results if st == "completed")
    failed_entries: list[str] = []
    failed_count = 0

    for run_num, status, has_issue, trace, error_text in run_results:
        run_failed = status != "completed" or has_issue
        if not run_failed:
            continue
        failed_count += 1
        run_dir = session_dir / _run_label(run_num)

        issue_lines: list[str] = []
        if status != "completed":
            issue_lines.append(error_text or "Run errored before trace was available.")
        elif trace is not None:
            issue_lines.extend(_collect_issue_lines(trace))
        if not issue_lines:
            issue_lines.append("Run marked failed with no additional error text.")

        slideshow_link = ""
        transitions_link = ""
        meta_block = ""
        if trace is not None:
            _write_run_slideshow(run_dir, trace, run_num)
            transitions_link = (
                f'<div><a href="{escape(f"{_run_label(run_num)}/transitions.json")}">Open transitions.json</a></div>'
            )
            slideshow_link = (
                f'<div><a href="{escape(f"{_run_label(run_num)}/slideshow.html")}">Open run slideshow</a></div>'
            )
            first_issue = next((t for t in trace.transitions if t.qa_observation), None)
            if first_issue:
                screenshot = _report_shot_path(run_num, first_issue.after_screenshot)
                shot_html = (
                    f'<div><img src="{escape(screenshot)}" alt="Run screenshot"></div>'
                    if screenshot
                    else ""
                )
                meta_block = (
                    f"<div><strong>URL:</strong> {escape(first_issue.url_after or '')}</div>"
                    f"<div><strong>Action:</strong> {escape(first_issue.action_summary)}</div>"
                    f"{shot_html}"
                )

        issue_html = "".join(f"<p>{escape(text)}</p>" for text in issue_lines)
        failed_entries.append(
            f"""
<section class="run">
  <div class="run-heading">
    <h2>Run {run_num:02d}</h2>
    <span class="status">Failed</span>
  </div>
  <div class="issue">{issue_html}</div>
  <div class="details">{meta_block}</div>
  <div class="links">
    {slideshow_link}
    {transitions_link}
  </div>
</section>
"""
        )

    failed_html = (
        "\n".join(failed_entries)
        if failed_entries
        else '<p class="empty">No failed runs.</p>'
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Fuzzing report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #647083;
      --line: #dce2ea;
      --bad-bg: #fff1f0;
      --bad-ink: #9f241b;
      --link: #2456b3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(920px, calc(100% - 32px));
      margin: 40px auto;
    }}
    header {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 14px 35px rgba(20, 31, 48, 0.06);
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: clamp(2rem, 4vw, 3rem);
      letter-spacing: -0.04em;
    }}
    h2 {{
      margin: 0;
      font-size: 1.15rem;
    }}
    .meta {{
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .run {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      margin-top: 16px;
      padding: 18px;
      box-shadow: 0 10px 25px rgba(20, 31, 48, 0.045);
    }}
    .run-heading {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .status {{
      border-radius: 999px;
      background: var(--bad-bg);
      color: var(--bad-ink);
      font-size: 0.82rem;
      font-weight: 700;
      padding: 4px 10px;
    }}
    .issue {{
      border-left: 3px solid var(--bad-ink);
      background: var(--bad-bg);
      color: var(--bad-ink);
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 12px;
    }}
    .issue p {{
      margin: 0 0 8px;
    }}
    .issue p:last-child {{
      margin-bottom: 0;
    }}
    .details {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 12px;
    }}
    a {{
      color: var(--link);
      font-weight: 700;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    img {{
      max-width: 720px;
      width: 100%;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 10px;
      margin-top: 10px;
    }}
    .empty {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      color: var(--muted);
      margin-top: 16px;
      padding: 18px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{failed_count} failed / {runs_requested} runs</h1>
      <div class="meta">
        <div><strong>Session:</strong> {escape(session_dir.name)}</div>
        <div><strong>Start URL:</strong> {escape(start_url)}</div>
        <div><strong>Completed runs:</strong> {runs_completed}</div>
      </div>
    </header>
    {failed_html}
  </main>
</body>
</html>
"""

    report_path = session_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path, len(all_issues), successful_runs, runs_completed
