# How to run ocufuzz

## Setup

```bash
cd ocufuzz
python -m pip install -e .
playwright install chromium
```

Set:

- `GOOGLE_API_KEY` — required for Gemini.
- Optional: `OCU_GEMINI_MODEL` (default: `gemini-3.1-flash-lite-preview`).
- Optional: `OCU_FALLBACK_GEMINI_MODEL` (default: `gemini-3.1-flash-preview`).
- Optional: `OCU_MAX_HISTORY_ITEMS` (default: `10`).
- $env:GOOGLE_API_KEY = ""

The default runner uses Gemini 3.1 Flash-Lite Preview with thinking disabled
(`thinking_budget=0`).

## Local test sites

In one terminal:

```bash
python scripts/serve_test_sites.py
```

Opens:

- `http://127.0.0.1:8765/forms-site/`
- `http://127.0.0.1:8765/widgets-site/`
- `http://127.0.0.1:8765/flow-site/`

## Exploration smoke run

With the server running, in another terminal:

```bash
python -m ocufuzz "http://127.0.0.1:8765/forms-site/" --max-steps 12
```

This efficient default keeps browser-use execution and QA issue detection in the same step loop:
- screenshots still captured per step
- no second screenshot-analysis pass
- QA note is only recorded when likely incorrect behavior is observed
- conversation dumps are off by default
- LLM history is capped via `max_history_items` for lower token growth
- fallback model is used automatically on provider failures (e.g., rate limits)

Optional debugging run with full conversation artifacts:

```bash
python -m ocufuzz "http://127.0.0.1:8765/forms-site/" --max-steps 12 --headed
```

Optional model override for one run:

```bash
python -m ocufuzz "http://127.0.0.1:8765/forms-site/" --model gemini-3.1-flash-lite-preview
```

## CLI options

`python -m ocufuzz <url> [options]`

- `url` (required positional): Full URL to open.
- `--task <text>`: Override the built-in exploration/QA instructions.
- `--max-steps <int>`: Maximum number of agent steps (default `12`).
- `--artifacts <path>`: Root directory for run outputs (default `artifacts/explore`).
- `--headed`: Run with a visible browser window (default is headless).
- `--save-conversation`: Save per-step conversation dumps for debugging (default off).
- `--model <name>`: Override the model for this run only.

Artifacts are written under `artifacts/explore/<run_id>/`:

- `run_history.json` — raw `browser-use` history
- `transitions.json` — ocufuzz transition trace
- `conversation/` — per-step conversation dumps (only when `--save-conversation` is set)
