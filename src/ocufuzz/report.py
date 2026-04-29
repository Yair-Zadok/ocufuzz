# Build markdown reports from in-memory fuzz run results.

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ocufuzz.trace import TransitionTrace


def build_report(
    session_dir: Path,
    *,
    start_url: str,
    runs_requested: int,
    run_results: Sequence[tuple[int, str, bool, TransitionTrace | None]],
) -> tuple[Path, int, int, int]:
    """Write ``report.md`` under ``session_dir``. Each run result is ``(run_num, status, has_issue, trace)``."""
    session_dir = Path(session_dir)

    all_issues: list[dict[str, object]] = []
    for run_num, status, _has_issue, trace in run_results:
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
    for _run_num, status, _has_issue, trace in run_results:
        if status != "completed" or trace is None:
            continue
        if not any(t.qa_observation for t in trace.transitions):
            successful_runs += 1

    runs_completed = sum(1 for _, st, _, _ in run_results if st == "completed")
    denom = runs_requested if runs_requested > 0 else 1
    success_rate = successful_runs / denom

    lines: list[str] = [
        "# Fuzzing report",
        "",
        f"- **Session**: `{session_dir.name}`",
        f"- **Start URL**: {start_url}",
        f"- **Runs**: {runs_completed} completed with trace / {runs_requested} requested",
        f"- **Successful runs** (no QA issues): {successful_runs}",
        f"- **Success rate**: {success_rate * 100:.1f}%",
        "",
        "## Runs",
        "",
    ]
    for run_num, status, has_issue, _trace in run_results:
        note = "issues found" if has_issue else "no QA issues"
        lines.append(f"- **Run {run_num:02d}**: {status} — {note}")
    lines.extend(["", "## Issues", ""])

    if not all_issues:
        lines.append("- (none)")
    else:
        by_run: dict[int, list[dict[str, object]]] = {}
        for issue in all_issues:
            by_run.setdefault(int(issue["run"]), []).append(issue)
        for run_num in sorted(by_run):
            lines.append(f"### Run {run_num:02d}")
            lines.append("")
            for issue in by_run[run_num]:
                lines.append(
                    f"- Step **{issue['step']}** ({issue['severity'] or 'n/a'}) — {issue['observation']}\n"
                    f"  - URL: `{issue['url']}`\n"
                    f"  - Action: {issue['action_summary']}\n"
                    f"  - Screenshot: `{issue['screenshot']}`"
                )
            lines.append("")

    report_path = session_dir / "report.md"
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path, len(all_issues), successful_runs, runs_completed
