

import os

import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.environ.get("LAYA_SERVICE_URL", "http://localhost:8000")


def main():
    resp = requests.post(f"{SERVER_URL}/refresh", timeout=120)
    resp.raise_for_status()
    result = resp.json()
    print(
        f"Fetched {result['fetched']} listings, added {result['added']} new ones. "
        f"Total stored: {result['total']}"
    )


if __name__ == "__main__":
    main()