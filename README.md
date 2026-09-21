# Job Match Extension

A local-first Chrome side-panel extension and FastAPI service that rank a small
library of resume bases against a job description. Results are explainable at
the requirement level: each point should trace to resume evidence or an
explicit gap.

## Current status

The repository now contains the first backend vertical slice:

- typed request and response contracts;
- deterministic lexical and synonym-aware requirement scoring;
- experience/project evidence weighted above skills-only evidence;
- close-score handling that avoids false precision;
- deterministic offline extraction for an initial technical requirement set;
- Markdown resume parsing into stable, section-aware evidence records;
- a Chrome MV3 side panel with Greenhouse, Lever, and paste-text capture;
- a resume.lol MCP sync for nine canonical role-family bases;
- a library-backed job endpoint that extracts requirements and ranks those bases;
- unit tests for ranking and evidence placement.

The supplied source plan is preserved in
`chromeextension job matcher plan.md`. The implementation roadmap is in
`PROJECT_PLAN.md`.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn job_matcher.main:app --reload
```

API documentation is then available at `http://localhost:8000/docs`.

To refresh the private resume library from resume.lol:

```bash
RESUME_LOL_MCP_TOKEN='your-token' python scripts/sync_resume_lol.py
```

The sync stores resumes under the Git-ignored `data/private/` directory and
does not print their contents.

## Layout

```text
src/job_matcher/       FastAPI service and scoring engine
tests/                 Backend tests
data/examples/         Safe, versioned sample inputs
data/private/resumes/  Local resume.lol bases (ignored by Git)
extension/             Chrome MV3 side-panel client
scripts/               Local data-sync utilities
```

Never commit real API keys, bearer tokens, private resumes, or application
history. Use `.env` and `data/private/` for local-only material.

## Load the extension

1. Start the backend at `http://localhost:8000`.
2. Open `chrome://extensions`, enable Developer mode, and choose **Load unpacked**.
3. Select this repository's `extension/` directory.
4. Open a Greenhouse or Lever posting and click the extension action, or paste a
   job description in the side panel.

The panel ranks the locally synced resume bases and shows extracted
requirements. Configure a different backend URL or bearer token from the
extension's options page; provider API keys remain backend-only.
