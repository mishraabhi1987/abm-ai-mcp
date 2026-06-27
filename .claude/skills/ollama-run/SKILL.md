---
name: ollama-run
description: Manually start and health-check the local Ollama server. Invoke with /ollama-run to launch `ollama serve`, confirm it is listening on port 11434, and verify the qwen3.5:4b model is available before using the offline model path.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash(ollama serve), Bash(pgrep *), Bash(curl *), Bash(sleep *), Read
---

## Purpose

Bring the local Ollama server up (if it is not already) and verify the offline
model path is ready. This skill has a side effect (starting a background
server), so it is user-invoked only — never auto-triggered.

## Steps

### Step 1 — Is it already running?

Run `pgrep -x ollama`.

- Exit code 0 (process found): say "Ollama already running." and go to Step 3.
- Non-zero (not found): go to Step 2.

### Step 2 — Start the server

Start `ollama serve` with `run_in_background: true`.

Then run `sleep 2` to allow GPU/Metal discovery and port binding to complete
(cold start can take a few seconds on first launch).

Read the background task output and look for `Listening on 127.0.0.1:11434`.

- If you see it: startup succeeded. Note the background task ID for the user.
- If you see `address already in use` or any bind error: another process holds
  port 11434. Report the error and stop — do not start a second instance.
- If you see no output yet: continue to Step 3 (the verify step will confirm).

### Step 3 — Verify the API (with retry for warm-up)

Run:

```
curl -s --max-time 3 http://localhost:11434/api/tags
```

If it fails or returns nothing, run `sleep 2` and retry the same curl **once**.

Interpret the result:

- Valid JSON returned → say "Ollama is up and reachable at http://localhost:11434."
- Response contains `qwen3.5:4b` → say "qwen3.5:4b is available."
- Response does NOT contain `qwen3.5:4b` → say "qwen3.5:4b not found — run
  `ollama pull qwen3.5:4b` to download it."
- Both curl attempts fail → say "Server process started but API not reachable
  yet — wait a few seconds and run /ollama-run again."

## Final report

State clearly: (1) whether Ollama was already running or freshly started,
(2) whether the API responded, (3) whether qwen3.5:4b is available, and
(4) the background task ID if a new server was started (so the user can check
or stop it later).
