# laya-job-filter

A job search dashboard that pulls live listings from the Adzuna API and
automatically classifies each one — relevance, seniority, remote-friendliness,
recruiter-spam likelihood — using **Laya**, a 421M-parameter open-source
decision model. No LLM calls, no API cost per classification, ~35ms per job.

Instead of scrolling through job boards manually, you define what you're
looking for once, and the dashboard shows you only what actually matches.

## Why Laya instead of an LLM?

Classifying "is this spam / what seniority / is this remote" for every job
posting is a fixed, repeatable judgment task — not generation. Laya answers
typed questions (yes/no, multiple-choice, score) about a piece of text in a
**single forward pass**, with calibrated confidence scores you can threshold
on. That makes it fast and cheap enough to run on every refresh, instead of
reaching for an LLM call per job.

## Features

- 🔍 **Live job fetching** from the Adzuna API, driven by your own search
  profile (role, location, how recent)
- 🧠 **Automatic classification** per job: relevance score, seniority level,
  remote-friendly flag, recruiter-spam likelihood
- 🔁 **One-click refetch** — pulls new listings and classifies them instantly,
  with duplicates (by URL) automatically skipped
- ✏️ **Editable criteria** — change what Laya looks for directly from the
  dashboard UI, no code changes needed
- ⚙️ **Editable search profile** — change role, location, or freshness window
  from the UI as well
- ⚡ **Single lightweight backend** — one FastAPI server handles the model,
  the Adzuna fetching, and serves the dashboard itself

## Tech stack

FastAPI · Laya · Adzuna API · vanilla JS/HTML dashboard (no frontend build step)

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/AbhijithTA/laya-job-filter.git
cd laya-job-filter
```

### 2. Get Adzuna API credentials
Free sign-up at [developer.adzuna.com](https://developer.adzuna.com/) — you'll
get an App ID and App Key.

### 3. Configure environment
Copy `.env.example` to `.env` and fill in your credentials:
```
ADZUNA_APP_ID=your_app_id_here
ADZUNA_APP_KEY=your_app_key_here
ADZUNA_COUNTRY=in
ADZUNA_RESULTS_PER_PAGE=20
```

### 4. Install dependencies
```bash
python -m pip install -r requirements.txt
```

### 5. Run
```bash
python -m uvicorn app:app --reload --port 8000
```
Open **http://localhost:8000/** — that's the dashboard, served directly by
the same server.

## Using it

- **Edit Profile** — set what role and location you're hunting for, and how
  recent listings should be (`max_days_old`). This is saved to `profile.json`
  (auto-created on first run, gitignored).
- **Refetch Jobs** — pulls new listings matching your profile, classifies
  each with Laya, and adds any new ones to `jobs.json` (also gitignored).
- **Edit Criteria** — a JSON editor for the questions Laya asks about every
  job. Each question needs a `type` (`"noul"` for yes/no-style confidence, or
  `"choice"` for multi-option) and `instructions`; `"choice"` also needs a
  `criteria` object mapping each option to a description. Saved to
  `criteria.json`. New criteria apply to jobs classified from that point
  forward — existing stored jobs keep their old tags.

## Project structure

```
laya-job-filter/
├── app.py              # backend: Laya classification, Adzuna fetch, API routes, serves dashboard
├── dashboard.html       # frontend — refetch button, profile editor, criteria editor
├── ingest.py            # thin CLI trigger for /refresh, useful for cron automation
├── requirements.txt
├── .env.example
├── .gitignore
├── jobs.json            # auto-created, gitignored — your fetched/classified jobs
├── profile.json          # auto-created, gitignored — your search profile
└── criteria.json         # auto-created, gitignored — your classification questions
```

## Automating with cron

Keep the server running (e.g. via `systemd` or `pm2`), then schedule
`ingest.py` to hit `/refresh` periodically:
```
0 */3 * * * cd /path/to/laya-job-filter && /path/to/venv/bin/python ingest.py >> ingest.log 2>&1
```

## Limitations

Laya's zero-shot accuracy is weaker than a large LLM's on nuanced or
high-cardinality judgments, and its yes/no (`noul`) questions can
occasionally latch onto option wording rather than the input text. It works
best when your criteria are phrased clearly and the answer space per
question stays small — which fits this use case well.

## License

MIT (or update to match your preference)