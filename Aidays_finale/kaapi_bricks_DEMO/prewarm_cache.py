"""Pre-warm the Kaapi Bricks app cache before demo.

Fires all example questions through the app so the semantic cache in
Lakebase is populated. Run this 30 minutes before the demo.

Usage:
    python prewarm_cache.py [APP_URL]
"""

import sys
import time
import requests

APP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

QUESTIONS = [
    "What's our best-selling drink this month?",
    "How do I make a Classic Filter Coffee?",
    "Which stores are running low on Coorg Arabica beans?",
    "What promotions are active right now?",
    "How long does Coorg Arabica take to reorder?",
    "What should I prepare for tomorrow?",
]

print(f"Pre-warming cache at {APP_URL}...\n")

for i, q in enumerate(QUESTIONS, 1):
    print(f"  [{i}/{len(QUESTIONS)}] {q[:60]}...")
    try:
        resp = requests.post(
            f"{APP_URL}/api/chat",
            json={
                "query": q,
                "store_location": "Koramangala, Bangalore",
                "history": [],
            },
            timeout=120,
            stream=True,
        )
        # Consume SSE stream
        for line in resp.iter_lines(decode_unicode=True):
            pass
        print(f"           Done ({resp.status_code})")
    except Exception as e:
        print(f"           Error: {e}")
    time.sleep(2)

# Verify cache
print("\nVerifying cache...")
try:
    stats = requests.get(f"{APP_URL}/api/stats", timeout=10).json()
    print(f"  Cache entries: {stats.get('cache_entries', 'N/A')}")
    print(f"  Total messages: {stats.get('messages', 'N/A')}")
    print(f"  Lakebase connected: {stats.get('connected', False)}")
except Exception as e:
    print(f"  Could not verify: {e}")

print("\nCache pre-warm complete.")
