# Multi-run fuzzing: sequential agents, shared compact summaries, report.html.

from __future__ import annotations

from datetime import datetime
import shutil
from pathlib import Path

from ocufuzz.explore import run_exploration
from ocufuzz.history_parser import write_transitions
from ocufuzz.report import build_report
from ocufuzz.summarize import build_prior_summary, summarize_run
from ocufuzz.trace import TransitionTrace


def _copy_if_exists(src: str | None, dst: Path) -> bool:
    if not src:
        return False
    src_path = Path(src)
    if not src_path.exists() or not src_path.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst)
    return True


def _bundle_trace_screenshots(run_dir: Path, trace: TransitionTrace) -> None:
    """
    Copy trace screenshots into ``run_dir/screenshots`` and rewrite paths to run-local refs.
    """
    copied_by_source: dict[str, str] = {}
    sequence = 0

    for transition in trace.transitions:
        for attr in ("before_screenshot", "after_screenshot"):
            source = getattr(transition, attr)
            if not source:
                continue
            if source in copied_by_source:
                setattr(transition, attr, copied_by_source[source])
                continue

            sequence += 1
            ext = Path(source).suffix or ".png"
            target_name = f"shot_{sequence:04d}{ext}"
            target_rel = f"screenshots/{target_name}"
            target_abs = run_dir / target_rel
            if _copy_if_exists(source, target_abs):
                copied_by_source[source] = target_rel
                setattr(transition, attr, target_rel)


async def run_fuzzing(
    start_url: str,
    *,
    runs: int,
    task: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    max_steps: int = 12,
    artifacts_root: str | Path = "previous_runs",
    headless: bool | None = True,
    save_conversation: bool = False,
) -> tuple[Path, Path, int, int, int]:
    """
    Run ``runs`` sequential explorations.

    Returns ``(session_dir, report_md_path, issue_count, successful_runs, runs_completed)``.
    """
    if runs < 1:
        raise ValueError("runs must be >= 1")

    session_id = f"fuzz_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir = Path(artifacts_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    accumulated: list[tuple[int, str]] = []
    run_results: list[tuple[int, str, bool, TransitionTrace | None, str | None]] = []

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
            _bundle_trace_screenshots(run_dir, trace)
            write_transitions(run_dir / "transitions.json", trace)
            has_issue = any(t.qa_observation for t in trace.transitions)
            run_results.append((run_num, "completed", has_issue, trace, None))
            accumulated.append((run_num, summarize_run(trace)))
        except Exception as exc:
            error_text = str(exc).strip() or "run errored before usable trace"
            run_results.append((run_num, "errored", False, None, error_text))
            accumulated.append((run_num, error_text))

    report_path, issue_count, successful_runs, runs_completed = build_report(
        session_dir,
        start_url=start_url,
        runs_requested=runs,
        run_results=run_results,
    )
    return session_dir, report_path, issue_count, successful_runs, runs_completed
