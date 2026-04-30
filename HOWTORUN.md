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

## Exploration / fuzzing run

With the server running, in another terminal:

```bash
python -m ocufuzz "http://127.0.0.1:8765/site-1/" --max-steps 12
```

Each invocation creates a session folder `previous_runs/fuzz_<date_time>/` with `run_01/`, …, `report.html`. Use `--runs N` for N sequential agents (default `1`).


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
- `--runs N`: Number of sequential exploration runs (default `1`).
- `--task <text>`: Override the built-in exploration/QA instructions.
- `--max-steps <int>`: Maximum number of agent steps per run (default `12`).
- `--artifacts <path>`: Root directory for session outputs (default `previous_runs`).
- `--headed`: Run with a visible browser window (default is headless).
- `--save-conversation`: Save per-step conversation dumps for debugging (default off).
- `--model <name>`: Override the model for this run only.
- `--provider <ollama|google>`: Override the LLM provider for this run only.

Artifacts are written under `previous_runs/fuzz_<date_time>/`:

- `run_01/`, `run_02/`, … — each contains `run_history.json`, `transitions.json`, `screenshots/`, and `slideshow.html` (when trace exists)
- `report.html` — simple failure-oriented session summary (`failed / runs`) with links to failed run slideshows
