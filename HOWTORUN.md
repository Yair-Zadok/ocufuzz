# How To Run

Requires Python 3.11+.

## Download And Install

```powershell
git clone <repo-url> ocufuzz
cd ocufuzz
python -m pip install -e .
python -m playwright install chromium
```

## Serve Demo Sites

```powershell
python scripts/serve_test_sites.py
```

Use `http://127.0.0.1:8765/site-obvious-issue/` or `http://127.0.0.1:8765/site-obscure-issue/`.

## Run With Ollama

```powershell
ollama pull qwen3.5:9b
ollama serve
```

In another terminal:

```powershell
python -m ocufuzz "http://127.0.0.1:8765/site-obvious-issue/" --provider ollama --max-steps 12
```

## Run With Google

```powershell
$env:GOOGLE_API_KEY = "<your key>"
python -m ocufuzz "http://127.0.0.1:8765/site-obvious-issue/" --provider google --max-steps 12
```

## Environment Variables

- `GOOGLE_API_KEY`: required only for `--provider google`.
- `OCU_OLLAMA_BASE_URL`: default `http://localhost:11434`.

Use CLI flags like `--provider` and `--model` for per-run choices.

## CLI Help

```text
usage: __main__.py [-h] [--runs N] [--task TASK] [--max-steps MAX_STEPS]
                   [--artifacts ARTIFACTS] [--headed] [--save-conversation]
                   [--model MODEL] [--provider {ollama,google}]
                   url

ocufuzz: browser-use exploration fuzz runner

positional arguments:
  url                   Full URL to open (e.g. http://127.0.0.1:8765/site-
                        obvious-issue/)

options:
  -h, --help            show this help message and exit
  --runs N              Number of sequential exploration sequences (default:
                        1).
  --task TASK           Override exploration instructions (default uses built-
                        in QA prompt).
  --max-steps MAX_STEPS
                        Maximum agent steps per run.
  --artifacts ARTIFACTS
                        Root directory; each invocation creates a
                        fuzz_<date_time> session folder here.
  --headed              Run browser headed (default headless).
  --save-conversation   Persist per-step conversation dumps under the run
                        folder for debugging.
  --model MODEL         Override model for this run (default: qwen3.5:9b for
                        Ollama).
  --provider {ollama,google}
                        LLM provider to use (default: ollama).
```
