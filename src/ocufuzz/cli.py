"""CLI entrypoint for exploratory runs."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="ocufuzz: browser-use exploration smoke runner")
    parser.add_argument("url", help="Full URL to open (e.g. http://127.0.0.1:8765/site-1/)")
    parser.add_argument(
        "--task",
        default=None,
        help="Override exploration instructions (default uses built-in QA prompt).",
    )
    parser.add_argument("--max-steps", type=int, default=12, help="Maximum agent steps.")
    parser.add_argument(
        "--artifacts",
        default="artifacts/explore",
        help="Directory under which a new run subfolder is created.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser headed (default headless).",
    )
    parser.add_argument(
        "--save-conversation",
        action="store_true",
        help="Persist per-step conversation dumps under artifacts for debugging.",
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
        from ocufuzz.explore import run_exploration

        out = await run_exploration(
            args.url,
            task=args.task,
            model=args.model,
            provider=args.provider,
            max_steps=args.max_steps,
            artifacts_root=args.artifacts,
            headless=not args.headed,
            save_conversation=args.save_conversation,
        )
        print(f"Artifacts written under: {out.resolve()}")

    try:
        asyncio.run(_go())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
