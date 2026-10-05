"""
laya_service.py

A small FastAPI wrapper around the Laya decision model.
Run this once and leave it running; ingest.py calls it for every job posting.

Start with:
    uvicorn laya_service:app --reload --port 8000
"""

import os

os.environ.setdefault("USE_TF", "0")  # avoids a known laya.load() hang with TensorFlow installed

from fastapi import FastAPI
from pydantic import BaseModel
from laya import Router

app = FastAPI(title="Laya Job Classifier")

# Preload so requests are ~30-40ms instead of triggering a cold model load
router = Router(preload=True)

QUESTIONS = {
    "relevant": {
        "type": "noul",
        "instructions": "Is this a frontend role primarily using React and/or TypeScript?",
    },
    "seniority": {
        "type": "choice",
        "instructions": "What seniority level is this role?",
        "criteria": {
            "junior": "0-2 years experience, junior/associate/trainee titles",
            "mid": "2-5 years experience, no seniority qualifier",
            "senior": "5+ years, senior/lead/principal/architect titles",
        },
    },
    "remote": {
        "type": "noul",
        "instructions": "Is this role remote or hybrid-remote friendly?",
    },
    "recruiter_spam": {
        "type": "noul",
        "instructions": "Is this a vague staffing-agency post with no real company or project details, "
        "as opposed to a genuine listing from a specific company?",
    },
}


class JobPosting(BaseModel):
    title: str
    description: str
    company: str = ""


@app.post("/classify")
def classify(job: JobPosting):
    state = {
        "title": job.title,
        "company": job.company,
        "description": job.description,
    }
    result = router.predict(state, QUESTIONS)
    answers = result["answers"]
    return {
        "relevant": answers["relevant"]["noul"],
        "seniority": answers["seniority"]["choice"],
        "remote": answers["remote"]["noul"],
        "recruiter_spam": answers["recruiter_spam"]["noul"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}