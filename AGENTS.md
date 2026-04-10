# AGENTS.md

## Project Context

This repository is a console-first MVP for semi-automated job applications.

Current product direction:
- first supported source is `hh.ru`
- vacancies are selected only by keyword rules
- LLM is used only to generate cover letters
- no scoring, no ranking by LLM
- no web UI yet
- all work should preserve a human-controlled flow

## Current Source of Truth

Important business decisions already made:
- do not add AI vacancy scoring
- do not build a dashboard yet
- do not expand to other job boards until `hh.ru` flow is stable
- use prepared `hh.ru` search URLs from config instead of generating them programmatically
- generate cover letters from the actual `hh.ru` resume, not from a local profile file

## Current Architecture

### Core

Located under `src/app/core/`.

Responsibilities:
- config loading
- logging
- state tracking
- keyword filtering
- workflow orchestration

### LLM

Located under `src/app/llm/`.

Responsibilities:
- local LLM client
- cover letter generation only

Current expectation:
- `Ollama` is the default provider
- local endpoint is configured in `config/app.yaml`

### HH Source

Located under `src/app/sources/hh/`.

Responsibilities:
- persistent browser session
- vacancy scanning
- vacancy detail parsing
- resume fetching
- response submission
- selector definitions

## Current HH Flow

### Scan

1. Open prepared `hh.ru` search URL from `config/searches.yaml`
2. Parse vacancy cards from the search results page
3. Convert them into internal `Job` objects
4. Filter them with include/exclude keyword rules

### Draft

1. Take the first matching vacancy
2. Open the vacancy page and fetch full description
3. Open the resume list on `hh.ru`
4. Find the configured resume by `hh.resume_title`
5. Open the resume page
6. Click the resume download button
7. Extract the TXT export link from the popup
8. Download and clean the text
9. Generate a cover letter with the local LLM

### Apply

Current `happy path` only:
1. Open vacancy page
2. Click respond
3. Handle relocation confirm if present
4. Fill cover letter if textarea is present
5. Click submit

If anything becomes ambiguous or unusual, return `manual_required`.

## Important Invariants

Do not change these unless explicitly asked:
- keyword-based vacancy filtering only
- real `hh` resume as input for cover letters
- conservative browser automation
- non-standard response flows should stop and return `manual_required`
- selectors should live in `src/app/sources/hh/selectors.py`

## Current Risks / Known Weak Spots

- `hh` selectors may change
- apply flow is only partially validated against real vacancies
- resume TXT export may still contain formatting noise, even after cleanup
- scanner currently does not paginate through multiple result pages
- live browser automation may require running outside restricted sandbox environments

## Local Environment Assumptions

- project is usually run in WSL/Linux
- Python version is defined in `.python-version`
- dependencies are installed into `.venv`
- Playwright Chromium is required
- Ollama is expected to be running locally

Useful commands:

```bash
source .venv/bin/activate
auto-responses login
auto-responses scan --limit 5
auto-responses draft --limit 1
auto-responses apply --limit 1
./scripts/reset.sh
```

## Editing Guidance For Future Work

- prefer minimal, local changes
- avoid broad refactors unless necessary
- do not add new infrastructure layers prematurely
- keep `core` generic and small
- keep `hh`-specific logic inside `src/app/sources/hh/`
- if adding new selectors, define them in `selectors.py`
- if a real response may be submitted, be explicit and careful

## What To Read First In A New Chat

If you are continuing work in a new chat, inspect these first:
- `README.md`
- `config/app.yaml`
- `config/searches.yaml`
- `src/app/core/workflow.py`
- `src/app/sources/hh/scanner.py`
- `src/app/sources/hh/resume.py`
- `src/app/sources/hh/apply.py`
- `src/app/sources/hh/selectors.py`

## Near-Term Priorities

1. Stabilize `hh` apply flow on real vacancies
2. Add safer `dry-run` or pre-submit inspection mode
3. Improve resume text cleaning only if it materially helps letter quality
4. Add pagination to scanner
5. Keep the system understandable and terminal-driven
