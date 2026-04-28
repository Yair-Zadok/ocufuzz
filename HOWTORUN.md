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

Artifacts are written under `artifacts/explore/<run_id>/`:

- `run_history.json` — raw `browser-use` history
- `transitions.json` — ocufuzz transition trace
- `conversation/` — per-step conversation dumps
