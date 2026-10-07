"""
Run with:
    python -m uvicorn app:app --reload --port 8000

Then open:
    http://localhost:8000/
"""

import json
import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0") 

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from laya import Router

load_dotenv()

BASE_DIR = Path(__file__).parent
JOBS_FILE = BASE_DIR / "jobs.json"
CRITERIA_FILE = BASE_DIR / "criteria.json"
PROFILE_FILE = BASE_DIR / "profile.json"

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]
ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "in")
RESULTS_PER_PAGE = int(os.environ.get("ADZUNA_RESULTS_PER_PAGE", "20"))

DEFAULT_PROFILE = {
    "what": os.environ.get("ADZUNA_QUERY", "backend developer"),
    "where": os.environ.get("ADZUNA_LOCATION", "remote"),
    "max_days_old": 30,
}

DEFAULT_QUESTIONS = {
    "relevant": {
        "type": "noul",
        "instructions": "Is this job posting genuinely about software development, engineering, "
        "or a closely related technical role — as opposed to sales, marketing, management, "
        "or unrelated fields?",
    },
    "seniority": {
        "type": "choice",
        "instructions": "What seniority level does this role require?",
        "criteria": {
            "junior": "0-2 years experience, junior/associate/trainee/entry-level titles",
            "mid": "2-5 years experience, no seniority qualifier in title",
            "senior": "5+ years experience, senior/lead/principal/staff/architect titles",
        },
    },
    "remote": {
        "type": "noul",
        "instructions": "Does this posting explicitly offer remote or hybrid-remote work?",
    },
    "recruiter_spam": {
        "type": "noul",
        "instructions": "Is this a vague staffing-agency post with no real company or project details, "
        "as opposed to a genuine listing from a specific company?",
    },
}

app = FastAPI(title="Job Filter")
router = Router(preload=True)


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    save_json(path, default)
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def load_criteria():
    return load_json(CRITERIA_FILE, DEFAULT_QUESTIONS)


def save_criteria(questions):
    save_json(CRITERIA_FILE, questions)


def load_profile():
    return load_json(PROFILE_FILE, DEFAULT_PROFILE)


def save_profile(profile):
    save_json(PROFILE_FILE, profile)


def load_jobs():
    return load_json(JOBS_FILE, [])


def save_jobs(jobs):
    save_json(JOBS_FILE, jobs)


def fetch_adzuna_jobs(what, where, max_days_old):
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": what,
        "results_per_page": RESULTS_PER_PAGE,
        "max_days_old": max_days_old,
        "content-type": "application/json",
    }
    if where:
        params["where"] = where
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def classify(title, description, company):
    state = {"title": title, "company": company, "description": description}
    questions = load_criteria()
    result = router.predict(state, questions)
    answers = result["answers"]
    return {key: answers[key][q["type"]] for key, q in questions.items()}


class CriteriaUpdate(BaseModel):
    questions: dict


class ProfileUpdate(BaseModel):
    what: str
    where: str = ""
    max_days_old: int = 30


@app.get("/")
def dashboard():
    return FileResponse(BASE_DIR / "dashboard.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/jobs")
def get_jobs():
    return load_jobs()


@app.get("/criteria")
def get_criteria():
    return load_criteria()


@app.post("/criteria")
def update_criteria(update: CriteriaUpdate):
    save_criteria(update.questions)
    return {"status": "saved", "questions": update.questions}


@app.get("/profile")
def get_profile():
    return load_profile()


@app.post("/profile")
def update_profile(update: ProfileUpdate):
    profile = {
        "what": update.what,
        "where": update.where,
        "max_days_old": update.max_days_old,
    }
    save_profile(profile)
    return {"status": "saved", "profile": profile}


@app.post("/refresh")
def refresh():
    profile = load_profile()
    existing = load_jobs()
    seen_urls = {job["url"] for job in existing}

    raw_jobs = fetch_adzuna_jobs(
        what=profile["what"],
        where=profile.get("where", ""),
        max_days_old=profile.get("max_days_old", 30),
    )
    new_count = 0

    for job in raw_jobs:
        url = job.get("redirect_url", "")
        if not url or url in seen_urls:
            continue

        title = job.get("title", "")
        description = job.get("description", "")
        company = job.get("company", {}).get("display_name", "")

        try:
            tags = classify(title, description, company)
        except Exception as e:
            print(f"Skipping '{title}' — classify error: {e}")
            continue

        existing.append(
            {
                "title": title,
                "company": company,
                "location": job.get("location", {}).get("display_name", ""),
                "url": url,
                "created": job.get("created", ""),
                "description": description[:500],
                **tags,
            }
        )
        seen_urls.add(url)
        new_count += 1

    save_jobs(existing)
    return {
        "fetched": len(raw_jobs),
        "added": new_count,
        "total": len(existing),
        "profile": profile,
    }