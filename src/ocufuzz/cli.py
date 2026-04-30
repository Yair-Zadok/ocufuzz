"""CLI entrypoint for exploratory runs."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="ocufuzz: browser-use exploration fuzz runner")
    parser.add_argument("url", help="Full URL to open (e.g. http://127.0.0.1:8765/site-1/)")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Number of sequential exploration sequences (default: 1).",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Override exploration instructions (default uses built-in QA prompt).",
    )
    parser.add_argument("--max-steps", type=int, default=12, help="Maximum agent steps per run.")
    parser.add_argument(
        "--artifacts",
        default="previous_runs",
        help="Root directory; each invocation creates a fuzz_<date_time> session folder here.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser headed (default headless).",
    )
    parser.add_argument(
        "--save-conversation",
        action="store_true",
        help="Persist per-step conversation dumps under the run folder for debugging.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model for this run (default: qwen3.5:9b for Ollama).",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "google"],
        default=None,
        help="LLM provider to use (default: OCU_LLM_PROVIDER or ollama).",
    )
    args = parser.parse_args()

    async def _go():
        from ocufuzz.fuzz import run_fuzzing

        session_dir, report_path, issue_count, successful, _ = await run_fuzzing(
            args.url,
            runs=args.runs,
            task=args.task,
            model=args.model,
            provider=args.provider,
            max_steps=args.max_steps,
            artifacts_root=args.artifacts,
            headless=not args.headed,
            save_conversation=args.save_conversation,
        )
        rate = (successful / args.runs * 100) if args.runs else 0.0
        print(f"Session: {session_dir.resolve()}")
        print(
            f"Fuzzing complete: {successful}/{args.runs} successful ({rate:.1f}%), "
            f"{issue_count} issue(s). Report: {report_path.resolve()}"
        )

    try:
        asyncio.run(_go())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
