# How to run ocufuzz

## Setup

```bash
cd ocufuzz
python -m pip install -e .
playwright install chromium
```

Set:

- Optional: `OCU_LLM_PROVIDER` (default: `ollama`; also supports `google`).
- Optional: `OCU_OLLAMA_MODEL` (default: `qwen3.5:9b`).
- Optional: `OCU_OLLAMA_BASE_URL` (default: `http://localhost:11434`).
- Optional: `OCU_OLLAMA_MAX_TOKENS` (default: `2048`).
- Optional: `OCU_OLLAMA_MAX_RETRIES` (default: `2`).
- `GOOGLE_API_KEY` — required only when using `--provider google`.
- Optional: `OCU_GEMINI_MODEL` (default: `gemini-3.1-flash-lite-preview`, for Google).
- Optional: `OCU_FALLBACK_GEMINI_MODEL` (default: `gemini-3.1-flash-preview`, for Google).
- Optional: `OCU_MAX_HISTORY_ITEMS` (default: `10`).
- $env:GOOGLE_API_KEY = ""

The default runner uses local Ollama via LiteLLM with `qwen3.5:9b`.
Make sure Ollama is running and the model is pulled:

```powershell
ollama pull qwen3.5:9b
ollama serve
```

Gemini remains available with `--provider google` and uses thinking disabled
(`thinking_budget=0`).

## Local test site

In one terminal:

```bash
python scripts/serve_test_sites.py
```

Opens:

- `http://127.0.0.1:8765/site-1/`

## Exploration smoke run

With the server running, in another terminal:

```bash
python -m ocufuzz "http://127.0.0.1:8765/site-1/" --max-steps 12
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
python -m ocufuzz "http://127.0.0.1:8765/site-1/" --max-steps 12 --headed
```

Optional model override for one run:

```powershell
python -m ocufuzz "http://127.0.0.1:8765/site-1/" --model qwen3.5:9b
```

Optional Gemini run:

```powershell
$env:GOOGLE_API_KEY = "<your key>"
python -m ocufuzz "http://127.0.0.1:8765/site-1/" --provider google --model gemini-3.1-flash-lite-preview
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
- `--provider <ollama|google>`: Override the LLM provider for this run only.

Artifacts are written under `artifacts/explore/<run_id>/`:

- `run_history.json` — raw `browser-use` history
- `transitions.json` — ocufuzz transition trace
- `conversation/` — per-step conversation dumps (only when `--save-conversation` is set)
