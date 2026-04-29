# Multi-run fuzzing: sequential agents, shared compact summaries, report.md.

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from ocufuzz.explore import run_exploration
from ocufuzz.report import build_report
from ocufuzz.summarize import build_prior_summary, summarize_run
from ocufuzz.trace import TransitionTrace


async def run_fuzzing(
    start_url: str,
    *,
    runs: int,
    task: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    max_steps: int = 12,
    artifacts_root: str | Path = "artifacts/explore",
    headless: bool | None = True,
    save_conversation: bool = False,
) -> tuple[Path, Path, int, int, int]:
    """
    Run ``runs`` sequential explorations.

    Returns ``(session_dir, report_md_path, issue_count, successful_runs, runs_completed)``.
    """
    if runs < 1:
        raise ValueError("runs must be >= 1")

    session_id = f"fuzz_{uuid.uuid4().hex[:12]}"
    session_dir = Path(artifacts_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    accumulated: list[tuple[int, str]] = []
    run_results: list[tuple[int, str, bool, TransitionTrace | None]] = []

    for i in range(runs):
        run_num = i + 1
        run_dir = session_dir / f"run_{run_num:02d}"
        shutil.rmtree(run_dir, ignore_errors=True)

        try:
            _, trace = await run_exploration(
                start_url,
                artifacts_dir=run_dir,
                task=task,
                model=model,
                provider=provider,
                max_steps=max_steps,
                headless=headless,
                save_conversation=save_conversation,
                prior_summary=build_prior_summary(accumulated),
            )
            has_issue = any(t.qa_observation for t in trace.transitions)
            run_results.append((run_num, "completed", has_issue, trace))
            accumulated.append((run_num, summarize_run(trace)))
        except Exception:
            run_results.append((run_num, "errored", False, None))
            accumulated.append((run_num, "run errored before usable trace"))

    report_path, issue_count, successful_runs, runs_completed = build_report(
        session_dir,
        start_url=start_url,
        runs_requested=runs,
        run_results=run_results,
    )
    return session_dir, report_path, issue_count, successful_runs, runs_completed
