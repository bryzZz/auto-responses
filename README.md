# auto-responses

Console-first MVP for semi-automated job applications.

Current scope:
- first source: `hh.ru`
- vacancy selection only by keyword rules
- LLM is used only for cover letter generation
- no web UI yet, everything runs through the terminal
- browser automation is done with `Playwright`

## Goal

The project is meant to automate the repetitive parts of job applications while keeping the flow understandable and controllable:
- scan vacancies from prepared `hh.ru` search URLs
- filter them by include/exclude keywords
- fetch the full vacancy description
- fetch the real candidate resume from `hh.ru`
- generate a cover letter with a local LLM
- submit the response through browser automation

The design is intentionally conservative:
- no AI-based vacancy scoring
- no automatic decision-making beyond keyword filters
- non-standard response flows should return `manual_required`

## Current Status

Implemented:
- project skeleton with CLI commands
- persistent `hh.ru` browser session
- manual login flow
- scanner for `hh.ru` search result pages
- full vacancy description fetch
- resume fetch from `hh.ru`
  - opens the resume page
  - clicks the download button
  - extracts the TXT export link
  - downloads and cleans the text for LLM use
- local LLM integration through `Ollama`
- first `hh` apply happy path

Current constraints:
- only `hh.ru`
- one-page search scan, no pagination yet
- apply flow is only the first happy path
- resume parsing is based on `hh` TXT export, then cleaned locally
- many `hh` edge cases still intentionally return `manual_required`

## Stack

- Python 3.12
- Playwright
- PyYAML
- local LLM via Ollama HTTP API

## Repository Layout

```text
config/
  app.yaml
  searches.yaml

data/
  generated_letters/
  logs/
  session/
  state.json

scripts/
  bootstrap.sh
  reset.sh

src/app/
  cli.py
  main.py
  core/
    config.py
    keyword_filter.py
    logging.py
    models.py
    state.py
    workflow.py
  llm/
    base.py
    cover_letter.py
  sources/hh/
    apply.py
    models.py
    parser.py
    resume.py
    scanner.py
    selectors.py
    session.py
```

## Setup

Create and activate the virtual environment:

```bash
cd /home/nikita/dev/auto-responses
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

If Playwright browser binaries are missing:

```bash
.venv/bin/python -m playwright install chromium
```

## Ollama

The project expects a local LLM endpoint. Current default is `Ollama`.

Start Ollama:

```bash
ollama serve
```

Pull a model:

```bash
ollama pull qwen2.5:3b
```

The default config expects:

```yaml
llm:
  enabled: true
  provider: "ollama"
  model: "qwen2.5:3b"
  endpoint: "http://127.0.0.1:11434/api/generate"
```

## Configuration

### `config/app.yaml`

Main runtime settings:
- browser mode
- `hh` session settings
- `resume_title`
- local LLM settings

Important field:

```yaml
hh:
  resume_title: "Frontend-разработчик"
```

This must match the resume title on `hh.ru` that should be used for cover letter generation.

### `config/searches.yaml`

Contains prepared `hh.ru` search URLs and keyword rules.

Example:

```yaml
searches:
  - name: "frontend remote"
    source: "hh"
    url: "https://irkutsk.hh.ru/search/vacancy?..."
    include_keywords:
      - "frontend"
      - "react"
      - "typescript"
    exclude_keywords:
      - "1c"
      - "php"
      - "full-stack"
```

## Runtime Commands

Activate the environment first:

```bash
source .venv/bin/activate
```

### 1. Login to `hh.ru`

```bash
auto-responses login
```

This opens Chromium with a persistent profile stored under `data/session/hh`.

### 2. Scan vacancies

```bash
auto-responses scan --limit 5
```

This:
- opens the configured search URL
- parses vacancy cards
- applies keyword filters
- prints matching vacancies

### 3. Generate a draft

```bash
auto-responses draft --limit 1
```

This:
- scans vacancies
- fetches the full vacancy description
- fetches the configured resume from `hh.ru`
- generates a cover letter with the local LLM
- saves the result to `data/generated_letters/`

### 4. Apply

```bash
auto-responses apply --limit 1
```

This:
- generates the draft first
- asks for terminal confirmation
- attempts the first `hh` happy path apply flow

Use with care: this can submit a real response.

## Data and State

`data/state.json` tracks processed jobs and their statuses, for example:
- `drafted`
- `submitted`
- `manual_required`
- `error`

Ignored runtime artifacts:
- generated letters
- logs
- browser session

## Reset

To clear runtime artifacts:

```bash
./scripts/reset.sh
```

This resets:
- `data/generated_letters/`
- `data/logs/`
- `data/session/`
- `data/state.json`

You will need to log in to `hh.ru` again after reset.

## Important Behavior

### Vacancy selection

Vacancies are selected only by keyword rules. There is no LLM scoring.

### Resume source of truth

Cover letters are generated from the real resume text fetched from `hh.ru`, not from a local profile file.

### Apply flow

The apply flow should be conservative.

If any of these happens, the system should return `manual_required` instead of trying to outsmart the page:
- external redirect
- unexpected popup flow
- response limit or `hh` validation error
- ambiguous resume selection
- missing submit button

## Development Notes

- Prefer keeping `hh` selectors in `src/app/sources/hh/selectors.py`
- Keep browser flow logic in dedicated source modules, not in `core`
- Keep `core` generic and console-first for now
- Do not add UI until the console flow is stable
- Do not reintroduce vacancy scoring unless explicitly requested

## Recommended Next Steps

- stabilize the `hh` apply flow against real vacancy variations
- add a safe `dry-run` apply mode
- support multi-page vacancy scanning
- improve resume text normalization
- add tests for keyword filtering and text cleaning
