#!/usr/bin/env python3
"""
Scrapes tweets via X's SearchTimeline API using the browser's session.
Uses the browser-ws-client to execute fetch() calls in the browser tab.

Usage:
  python3 data/scripts/x_search_scraper.py --tab-id 317351751 --query "from:yacineMTB since:2026-01-21 until:2026-04-02"
"""
import json
import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

CLIENT = str(Path.home() / ".claude/commands/browser-ws-client.py")

SEARCH_QID = "R0u1RWRf748KzyGBXvOYRA"
BEARER = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

FEATURES = {
    "rweb_video_screen_enabled": False, "rweb_cashtags_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False, "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True, "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

# JS template for a single search page fetch
JS_TEMPLATE = r"""
(async function() {
  var ct0 = document.cookie.match(/ct0=([^;]+)/)[1];
  var varsStr = VARS_PLACEHOLDER;
  var featStr = FEATS_PLACEHOLDER;
  var url = 'https://x.com/i/api/graphql/QID_PLACEHOLDER/SearchTimeline?variables=' + encodeURIComponent(varsStr) + '&features=' + encodeURIComponent(featStr);
  var resp = await fetch(url, {
    headers: {
      'authorization': 'BEARER_PLACEHOLDER',
      'x-csrf-token': ct0,
      'x-twitter-active-user': 'yes',
      'x-twitter-auth-type': 'OAuth2Session',
      'x-twitter-client-language': 'en'
    },
    credentials: 'include'
  });
  if (resp.status === 429) return JSON.stringify({error: 'rate_limited', status: 429});
  if (!resp.ok) return JSON.stringify({error: 'http_error', status: resp.status});
  var data = await resp.json();
  var timeline = data?.data?.search_by_raw_query?.search_timeline?.timeline;
  if (!timeline) return JSON.stringify({error: 'no_timeline'});
  var instructions = timeline.instructions || [];
  var entries = [];
  for (var i = 0; i < instructions.length; i++) {
    if (instructions[i].type === 'TimelineAddEntries') entries = entries.concat(instructions[i].entries || []);
  }
  var tweets = [], nextCursor = null;
  for (var j = 0; j < entries.length; j++) {
    var e = entries[j];
    if (e.entryId && e.entryId.startsWith('cursor-bottom-')) { nextCursor = e.content?.value; continue; }
    if (e.entryId && (e.entryId.startsWith('cursor-top-') || e.entryId.startsWith('promoted'))) continue;
    var tr = e.content?.itemContent?.tweet_results?.result;
    if (!tr) continue;
    var core = tr.__typename === 'TweetWithVisibilityResults' ? tr.tweet : tr;
    if (!core || !core.legacy) continue;
    var l = core.legacy;
    tweets.push({
      id: l.id_str || core.rest_id, created_at: l.created_at,
      timestamp_ms: new Date(l.created_at).getTime(), full_text: l.full_text,
      retweet_count: l.retweet_count||0, favorite_count: l.favorite_count||0,
      reply_count: l.reply_count||0, quote_count: l.quote_count||0,
      bookmark_count: l.bookmark_count||0, lang: l.lang,
      is_retweet: !!l.retweeted_status_result, is_quote: !!l.is_quote_status,
      is_reply: !!l.in_reply_to_status_id_str,
      in_reply_to_user: l.in_reply_to_screen_name||null,
      urls: (l.entities?.urls||[]).map(function(u){return u.expanded_url}),
      media: (l.extended_entities?.media||[]).map(function(m){
        return {type:m.type, url:m.media_url_https, expanded_url:m.expanded_url};
      })
    });
  }
  return JSON.stringify({tweets: tweets, cursor: nextCursor});
})()
"""


def build_js(variables):
    """Build the JS code for a single page fetch."""
    vars_json = json.dumps(variables)
    feats_json = json.dumps(FEATURES)
    js = JS_TEMPLATE
    js = js.replace("VARS_PLACEHOLDER", json.dumps(vars_json))
    js = js.replace("FEATS_PLACEHOLDER", json.dumps(feats_json))
    js = js.replace("QID_PLACEHOLDER", SEARCH_QID)
    js = js.replace("BEARER_PLACEHOLDER", BEARER)
    return js


def browser_js(code, tab_id, timeout=30):
    """Execute JS in the browser tab."""
    args = json.dumps({"code": code})
    try:
        r = subprocess.run(
            ["python", CLIENT, "call", "javascript_tool",
             "--tab-id", str(tab_id), "--timeout", str(timeout), "--args", args],
            capture_output=True, text=True, timeout=timeout + 15
        )
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tab-id", type=int, required=True)
    parser.add_argument("--query", default="from:yacineMTB since:2026-01-21 until:2026-04-02")
    parser.add_argument("--merge-with", help="Path to existing JSON to merge results into")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--delay", type=int, default=4, help="Seconds between requests")
    args = parser.parse_args()

    # Load existing tweets if merging
    all_tweets = []
    seen_ids = set()
    if args.merge_with:
        existing = json.loads(Path(args.merge_with).read_text())
        all_tweets = existing["tweets"]
        seen_ids = {t["id"] for t in all_tweets}
        print(f"Loaded {len(all_tweets)} existing tweets to merge with")

    cursor = None
    page = 0
    empty_count = 0
    new_total = 0

    while True:
        page += 1
        variables = {
            "rawQuery": args.query,
            "count": 20,
            "querySource": "typed_query",
            "product": "Latest",
            "withGrokTranslatedBio": False,
        }
        if cursor:
            variables["cursor"] = cursor

        js = build_js(variables)
        result = browser_js(js, args.tab_id, timeout=30)

        if not result:
            print(f"  Page {page}: fetch failed, retrying in 10s...")
            sys.stdout.flush()
            time.sleep(10)
            continue

        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            print(f"  Page {page}: bad JSON: {result[:200]}")
            break

        if data.get("error") == "rate_limited":
            print(f"  Page {page}: rate limited, waiting 30s...")
            sys.stdout.flush()
            time.sleep(30)
            continue
        elif data.get("error"):
            print(f"  Page {page}: error: {data['error']}")
            break

        tweets = data.get("tweets", [])
        cursor = data.get("cursor")

        if not tweets:
            empty_count += 1
            if empty_count >= 2:
                print("  No more results, stopping")
                break
            time.sleep(args.delay)
            continue
        empty_count = 0

        new_count = 0
        oldest_on_page = None
        for t in tweets:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                all_tweets.append(t)
                new_count += 1
                new_total += 1
            if not oldest_on_page or t["timestamp_ms"] < oldest_on_page:
                oldest_on_page = t["timestamp_ms"]

        oldest_str = datetime.fromtimestamp(
            oldest_on_page / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d") if oldest_on_page else "?"
        print(f"  Page {page}: +{new_count} new (oldest: {oldest_str}, total: {len(all_tweets)})")
        sys.stdout.flush()

        if not cursor:
            print("  No cursor, done")
            break

        time.sleep(args.delay)

    # Sort and save
    all_tweets.sort(key=lambda t: t["timestamp_ms"], reverse=True)

    output_path = args.output or args.merge_with or "tweets.json"
    result_obj = {
        "meta": {
            "username": "yacineMTB",
            "user_id": "1173552893003255808",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "query": args.query,
            "total_tweets": len(all_tweets),
            "date_range": {
                "newest": all_tweets[0]["created_at"],
                "oldest": all_tweets[-1]["created_at"],
            } if all_tweets else None,
        },
        "tweets": all_tweets,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result_obj, indent=2))
    print(f"\nDone! {new_total} new tweets. {len(all_tweets)} total.")
    print(f"Saved to {output_path} ({Path(output_path).stat().st_size / 1024:.1f} KB)")
    if result_obj["meta"]["date_range"]:
        print(f"Range: {result_obj['meta']['date_range']['oldest']} -> {result_obj['meta']['date_range']['newest']}")


if __name__ == "__main__":
    main()
