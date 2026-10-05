import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]
ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "in")
ADZUNA_QUERY = os.environ.get("ADZUNA_QUERY", "React Developer")
ADZUNA_LOCATION = os.environ.get("ADZUNA_LOCATION", "")
RESULTS_PER_PAGE = int(os.environ.get("ADZUNA_RESULTS_PER_PAGE", "20"))
LAYA_SERVICE_URL = os.environ.get("LAYA_SERVICE_URL", "http://localhost:8000")

JOBS_FILE = Path(__file__).parent / "jobs.json"


def fetch_adzuna_jobs():
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": ADZUNA_QUERY,
        "where": ADZUNA_LOCATION,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def classify_job(title, description, company):
    resp = requests.post(
        f"{LAYA_SERVICE_URL}/classify",
        json={"title": title, "description": description, "company": company},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def load_existing_jobs():
    if JOBS_FILE.exists():
        return json.loads(JOBS_FILE.read_text())
    return []


def save_jobs(jobs):
    JOBS_FILE.write_text(json.dumps(jobs, indent=2))


def main():
    existing = load_existing_jobs()
    seen_urls = {job["url"] for job in existing}

    raw_jobs = fetch_adzuna_jobs()
    new_count = 0

    for job in raw_jobs:
        url = job.get("redirect_url", "")
        if not url or url in seen_urls:
            continue

        title = job.get("title", "")
        description = job.get("description", "")
        company = job.get("company", {}).get("display_name", "")

        try:
            tags = classify_job(title, description, company)
        except requests.RequestException as e:
            print(f"Skipping '{title}' — Laya service error: {e}")
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
    print(f"Fetched {len(raw_jobs)} listings, added {new_count} new ones. Total stored: {len(existing)}")


if __name__ == "__main__":
    main()