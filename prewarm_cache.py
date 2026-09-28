"""Pre-warm the Kaapi Bricks app cache before the demo.

Sends the demo questions through the app so their answers are stored in the Lakebase
semantic cache. Document (SOP) questions take ~20–25 s in Genie Agent mode when not cached.
Run this 30 minutes before the demo; cached answers expire after 48 hours.

Usage:
    python prewarm_cache.py <APP_URL> [--profile DEFAULT]

A deployed Databricks App requires OAuth, so requests are signed with the Databricks CLI
profile's token.
"""

import argparse
import time

import requests
from databricks.sdk import WorkspaceClient

QUESTIONS = [
    "Which ingredients are below reorder threshold? Show store and days of cover.",
    "How long can prepared decoction be kept before discarding?",
    "What were our top-selling drinks from February to May?",
    "How do I make a Classic Filter Coffee?",
    "What is the correct decoction ratio and timing?",
    "How long does Coorg Arabica take to reorder?",
]

parser = argparse.ArgumentParser()
parser.add_argument("app_url", nargs="?", default="http://localhost:8000")
parser.add_argument("--profile", default="DEFAULT")
args = parser.parse_args()
app_url = args.app_url.rstrip("/")

headers = {"Content-Type": "application/json"}
if not app_url.startswith("http://localhost"):
    headers.update(WorkspaceClient(profile=args.profile).config.authenticate())

print(f"Pre-warming cache at {app_url}...\n")

for i, q in enumerate(QUESTIONS, 1):
    print(f"  [{i}/{len(QUESTIONS)}] {q[:60]}...")
    start = time.time()
    try:
        resp = requests.post(
            f"{app_url}/api/chat",
            headers=headers,
            json={"query": q, "store_location": "Koramangala, Bangalore", "history": []},
            timeout=300,
            stream=True,
        )
        for _ in resp.iter_lines(decode_unicode=True):  # consume the SSE stream
            pass
        print(f"           Done ({resp.status_code}, {time.time() - start:.0f}s)")
    except Exception as e:
        print(f"           Error: {e}")
    time.sleep(2)

print("\nVerifying cache...")
try:
    stats = requests.get(f"{app_url}/api/stats", headers=headers, timeout=10).json()
    print(f"  Cache entries: {stats.get('cache_entries', 'N/A')}")
    print(f"  Total messages: {stats.get('messages', 'N/A')}")
    print(f"  Lakebase connected: {stats.get('connected', False)}")
except Exception as e:
    print(f"  Could not verify: {e}")

print("\nCache pre-warm complete.")
