#!/usr/bin/env python3
"""
Runner script that injects x_user_scraper.js into the browser via the
WebSocket bridge's javascript_tool, then polls for results.

Usage:
  python3 data/scripts/run_x_scraper.py [--tab-id TAB_ID]
"""

import json
import subprocess
import sys
import time
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BROWSER_CLIENT = Path.home() / ".claude" / "commands" / "browser-ws-client.py"
OUTPUT_DIR = SCRIPT_DIR.parent / "docs" / "yacine"


def call_browser(tool, args=None, tab_id=None, timeout=30):
    """Call a browser tool via the WS client."""
    cmd = ["python", str(BROWSER_CLIENT), "call", tool]
    if args:
        cmd += ["--args", json.dumps(args)]
    if tab_id:
        cmd += ["--tab-id", str(tab_id)]
    cmd += ["--timeout", str(timeout)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tab-id", type=int, help="Tab ID to execute in")
    args = parser.parse_args()

    tab_id = args.tab_id

    # Read the scraper JS
    js_file = SCRIPT_DIR / "x_user_scraper.js"
    js_code = js_file.read_text()

    # Modify the script to store result on window instead of returning it,
    # so we can poll for completion
    js_code = js_code.replace(
        "return result;\n})();",
        "window.__scrapeComplete = true; window.__scraped_tweets = result; return 'SCRAPE_STARTED';\n})();"
    )

    print("Injecting scraper script into browser...")
    result = call_browser("javascript_tool", {"code": js_code}, tab_id=tab_id, timeout=30)
    print(f"Injection result: {result}")

    if not result or "SCRAPE_STARTED" not in result:
        # The script is async so it returns a promise - the initial call may
        # return before completion. Let's poll for the result.
        print("Script injected (async). Polling for completion...")

    # Poll for completion
    print("Waiting for scrape to complete (this may take several minutes)...")
    poll_interval = 10  # seconds
    max_wait = 600  # 10 minutes
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        status = call_browser(
            "javascript_tool",
            {"code": "window.__scrapeComplete ? JSON.stringify({done: true, count: window.__scraped_tweets?.meta?.total_tweets || 0}) : JSON.stringify({done: false})"},
            tab_id=tab_id,
            timeout=15
        )

        if not status:
            print(f"  [{elapsed}s] Poll failed, retrying...")
            continue

        try:
            info = json.loads(status)
        except json.JSONDecodeError:
            print(f"  [{elapsed}s] Unexpected response: {status[:100]}")
            continue

        if info.get("done"):
            print(f"\nScrape complete! {info.get('count', '?')} tweets collected.")
            break
        else:
            # Try to get progress from console
            progress = call_browser(
                "javascript_tool",
                {"code": "window.__scraped_tweets ? 'collecting: ' + (window.__scraped_tweets.tweets?.length || 0) : 'still running...'"},
                tab_id=tab_id,
                timeout=10
            )
            print(f"  [{elapsed}s] {progress or 'waiting...'}")
    else:
        print("Timed out waiting for scrape to complete.")
        print("Check the browser console for details.")

    # Extract the data
    print("\nExtracting tweet data from browser...")
    data = call_browser(
        "javascript_tool",
        {"code": "JSON.stringify(window.__scraped_tweets || null)"},
        tab_id=tab_id,
        timeout=30
    )

    if not data or data == "null":
        print("No data retrieved. Check the browser console for errors.")
        sys.exit(1)

    # Parse and save
    try:
        tweets = json.loads(data)
    except json.JSONDecodeError:
        # Data might be too large for a single return - try chunked extraction
        print("Data too large for single extraction, trying chunked approach...")
        meta = call_browser(
            "javascript_tool",
            {"code": "JSON.stringify(window.__scraped_tweets.meta)"},
            tab_id=tab_id,
            timeout=15
        )
        meta = json.loads(meta)
        total = meta["total_tweets"]
        print(f"Total tweets: {total}")

        all_tweets = []
        chunk_size = 50
        for start in range(0, total, chunk_size):
            chunk = call_browser(
                "javascript_tool",
                {"code": f"JSON.stringify(window.__scraped_tweets.tweets.slice({start}, {start + chunk_size}))"},
                tab_id=tab_id,
                timeout=15
            )
            all_tweets.extend(json.loads(chunk))
            print(f"  Extracted {len(all_tweets)}/{total} tweets...")

        tweets = {"meta": meta, "tweets": all_tweets}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{tweets['meta']['username']}_tweets.json"
    output_file.write_text(json.dumps(tweets, indent=2))
    print(f"\nSaved to {output_file}")
    print(f"Total tweets: {tweets['meta']['total_tweets']}")
    if tweets['meta'].get('date_range'):
        print(f"Date range: {tweets['meta']['date_range']['oldest']} → {tweets['meta']['date_range']['newest']}")


if __name__ == "__main__":
    main()
