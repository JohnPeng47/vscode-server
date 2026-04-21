// ============================================================================
// X/Twitter User Timeline Scraper (Internal GraphQL API)
// ============================================================================
//
// WHAT THIS DOES:
//   Scrapes tweets from a user's timeline using X's internal GraphQL API,
//   authenticated via the browser's existing session.
//
// HOW TO RUN:
//   1. Log in to x.com in Chrome
//   2. Navigate to the target user's profile (e.g. https://x.com/yacineMTB)
//   3. Open DevTools Console (F12 → Console)
//   4. Paste this entire script and press Enter
//   5. Wait for it to finish — it will copy JSON to clipboard and log results
//
// CAVEATS:
//   - Requires an active X session (you must be logged in)
//   - Uses X's internal/undocumented GraphQL API — may break if X changes
//     their API schema or query IDs
//   - The queryId for UserTweets may rotate; if the script returns errors,
//     open DevTools Network tab, scroll the user's timeline, filter for
//     "UserTweets", and grab the fresh queryId from the request URL
//   - Rate limiting: configurable delay between requests (default 4s)
//   - X may throttle or block after many requests — the script handles
//     429 responses with exponential backoff
//
// PARAMETERS (edit below):
//   - USERNAME: The @handle to scrape (without the @)
//   - MONTHS_BACK: How many months of tweets to collect
//   - DELAY_MS: Pause between API requests
//
// LAST TESTED: April 2026
// ============================================================================

(async function () {
  // --- CONFIGURATION ---
  var USERNAME = 'yacineMTB';
  var MONTHS_BACK = 3;
  var DELAY_MS = 4000; // 4 seconds between requests to avoid rate limits
  var MAX_RETRIES = 3;
  var BACKOFF_MS = 30000; // 30s backoff on 429

  // --- QUERY ID ---
  // This is the GraphQL query ID for UserTweets. It may change over time.
  // To find the current one:
  //   1. Go to a user's profile on x.com
  //   2. Open DevTools → Network → filter "UserTweets"
  //   3. Scroll down to trigger a load
  //   4. Copy the queryId from the request URL path
  var QUERY_ID = '6fWQaBPK51aGyC_VC7t9GQ'; // as of April 2026

  // --- SETUP ---
  var ct0 = document.cookie.match(/ct0=([^;]+)/);
  if (!ct0) {
    console.error('❌ No ct0 cookie found — are you logged in to x.com?');
    return;
  }
  var csrfToken = ct0[1];

  var cutoffDate = new Date();
  cutoffDate.setMonth(cutoffDate.getMonth() - MONTHS_BACK);
  var cutoffMs = cutoffDate.getTime();

  console.log('🐦 X Timeline Scraper');
  console.log('  User: @' + USERNAME);
  console.log('  Cutoff: ' + cutoffDate.toISOString());
  console.log('  Delay: ' + DELAY_MS + 'ms between requests');
  console.log('');

  // --- STEP 1: Resolve username → userId ---
  console.log('📡 Resolving user ID for @' + USERNAME + '...');

  var userByScreenNameId = 'IGgvgiOx4QZndDHuD3x9TQ'; // UserByScreenName query ID
  var userVars = JSON.stringify({
    screen_name: USERNAME,
    withGrokTranslatedBio: true,
  });
  var userFeatures = JSON.stringify({
    hidden_profile_subscriptions_enabled: true,
    profile_label_improvements_pcf_label_in_post_enabled: true,
    responsive_web_profile_redirect_enabled: false,
    rweb_tipjar_consumption_enabled: false,
    verified_phone_label_enabled: false,
    subscriptions_verification_info_is_identity_verified_enabled: true,
    subscriptions_verification_info_verified_since_enabled: true,
    highlights_tweets_tab_ui_enabled: true,
    responsive_web_twitter_article_notes_tab_enabled: true,
    subscriptions_feature_can_gift_premium: true,
    creator_subscriptions_tweet_preview_api_enabled: true,
    responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
    responsive_web_graphql_timeline_navigation_enabled: true,
  });

  var userFieldToggles = JSON.stringify({withPayments: false, withAuxiliaryUserLabels: true});
  var userResp = await fetch(
    'https://x.com/i/api/graphql/' + userByScreenNameId + '/UserByScreenName?' +
    'variables=' + encodeURIComponent(userVars) +
    '&features=' + encodeURIComponent(userFeatures) +
    '&fieldToggles=' + encodeURIComponent(userFieldToggles),
    {
      headers: {
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'x-csrf-token': csrfToken,
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
      },
      credentials: 'include',
    }
  );

  if (!userResp.ok) {
    console.error('❌ Failed to resolve user: HTTP ' + userResp.status);
    var errText = await userResp.text();
    console.error(errText);
    return;
  }

  var userData = await userResp.json();
  var userId = userData?.data?.user?.result?.rest_id;
  if (!userId) {
    console.error('❌ Could not extract user ID from response');
    console.error(JSON.stringify(userData, null, 2));
    return;
  }
  console.log('✅ User ID: ' + userId);

  // --- STEP 2: Paginate through UserTweets ---
  var allTweets = [];
  var cursor = null;
  var pageNum = 0;
  var reachedCutoff = false;
  var consecutiveEmpty = 0;

  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  function parseTweetData(tweet) {
    if (!tweet) return null;

    // Handle tweet with visibility results wrapper
    var core = tweet;
    if (tweet.__typename === 'TweetWithVisibilityResults') {
      core = tweet.tweet;
    }
    if (!core || !core.legacy) return null;

    var legacy = core.legacy;
    var createdAt = new Date(legacy.created_at);

    return {
      id: legacy.id_str || core.rest_id,
      created_at: legacy.created_at,
      timestamp_ms: createdAt.getTime(),
      full_text: legacy.full_text,
      retweet_count: legacy.retweet_count || 0,
      favorite_count: legacy.favorite_count || 0,
      reply_count: legacy.reply_count || 0,
      quote_count: legacy.quote_count || 0,
      bookmark_count: legacy.bookmark_count || 0,
      lang: legacy.lang,
      is_retweet: !!legacy.retweeted_status_result,
      is_quote: !!legacy.is_quote_status,
      is_reply: !!legacy.in_reply_to_status_id_str,
      in_reply_to_user: legacy.in_reply_to_screen_name || null,
      urls: (legacy.entities?.urls || []).map(function (u) { return u.expanded_url; }),
      media: (legacy.extended_entities?.media || []).map(function (m) {
        return {
          type: m.type,
          url: m.media_url_https,
          expanded_url: m.expanded_url,
        };
      }),
    };
  }

  while (!reachedCutoff) {
    pageNum++;
    var variables = {
      userId: userId,
      count: 20,
      includePromotedContent: false,
      withQuickPromoteEligibilityTweetFields: true,
      withVoice: true,
    };
    if (cursor) {
      variables.cursor = cursor;
    }

    var features = JSON.stringify({
      rweb_video_screen_enabled: false,
      rweb_cashtags_enabled: true,
      profile_label_improvements_pcf_label_in_post_enabled: true,
      responsive_web_profile_redirect_enabled: false,
      rweb_tipjar_consumption_enabled: false,
      verified_phone_label_enabled: false,
      creator_subscriptions_tweet_preview_api_enabled: true,
      responsive_web_graphql_timeline_navigation_enabled: true,
      responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
      premium_content_api_read_enabled: false,
      communities_web_enable_tweet_community_results_fetch: true,
      c9s_tweet_anatomy_moderator_badge_enabled: true,
      responsive_web_grok_analyze_button_fetch_trends_enabled: false,
      responsive_web_grok_analyze_post_followups_enabled: true,
      responsive_web_jetfuel_frame: true,
      responsive_web_grok_share_attachment_enabled: true,
      responsive_web_grok_annotations_enabled: true,
      articles_preview_enabled: true,
      responsive_web_edit_tweet_api_enabled: true,
      graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
      view_counts_everywhere_api_enabled: true,
      longform_notetweets_consumption_enabled: true,
      responsive_web_twitter_article_tweet_consumption_enabled: true,
      content_disclosure_indicator_enabled: true,
      content_disclosure_ai_generated_indicator_enabled: true,
      responsive_web_grok_show_grok_translated_post: true,
      responsive_web_grok_analysis_button_from_backend: true,
      post_ctas_fetch_enabled: true,
      freedom_of_speech_not_reach_fetch_enabled: true,
      standardized_nudges_misinfo: true,
      tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled: true,
      longform_notetweets_rich_text_read_enabled: true,
      longform_notetweets_inline_media_enabled: false,
      responsive_web_grok_image_annotation_enabled: true,
      responsive_web_grok_imagine_annotation_enabled: true,
      responsive_web_grok_community_note_auto_translation_is_enabled: true,
      responsive_web_enhance_cards_enabled: false,
    });

    var fieldToggles = JSON.stringify({withArticlePlainText: false});

    var url = 'https://x.com/i/api/graphql/' + QUERY_ID + '/UserTweets?' +
      'variables=' + encodeURIComponent(JSON.stringify(variables)) +
      '&features=' + encodeURIComponent(features) +
      '&fieldToggles=' + encodeURIComponent(fieldToggles);

    var retries = 0;
    var resp;
    var success = false;

    while (retries <= MAX_RETRIES) {
      try {
        resp = await fetch(url, {
          headers: {
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-csrf-token': csrfToken,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
          },
          credentials: 'include',
        });

        if (resp.status === 429) {
          retries++;
          var waitTime = BACKOFF_MS * retries;
          console.warn('⚠️  Rate limited (429). Backing off ' + (waitTime / 1000) + 's... (retry ' + retries + '/' + MAX_RETRIES + ')');
          await sleep(waitTime);
          continue;
        }

        if (!resp.ok) {
          console.error('❌ HTTP ' + resp.status + ' on page ' + pageNum);
          var errBody = await resp.text();
          console.error(errBody.substring(0, 500));
          retries++;
          await sleep(DELAY_MS * 2);
          continue;
        }

        success = true;
        break;
      } catch (e) {
        console.error('❌ Fetch error: ' + e.message);
        retries++;
        await sleep(DELAY_MS * 2);
      }
    }

    if (!success) {
      console.error('❌ Failed after ' + MAX_RETRIES + ' retries on page ' + pageNum + '. Stopping.');
      break;
    }

    var data = await resp.json();

    // Navigate the response structure
    var instructions = (data?.data?.user?.result?.timeline_v2 || data?.data?.user?.result?.timeline)?.timeline?.instructions || [];
    var entries = [];
    for (var i = 0; i < instructions.length; i++) {
      var instr = instructions[i];
      if (instr.type === 'TimelineAddEntries' || instr.type === 'TimelineAddToModule') {
        entries = entries.concat(instr.entries || []);
      }
    }

    if (entries.length === 0) {
      consecutiveEmpty++;
      if (consecutiveEmpty >= 3) {
        console.log('⚠️  3 consecutive empty pages — stopping');
        break;
      }
      await sleep(DELAY_MS);
      continue;
    }
    consecutiveEmpty = 0;

    var pageTweets = 0;
    var oldestOnPage = null;

    for (var j = 0; j < entries.length; j++) {
      var entry = entries[j];
      var entryId = entry.entryId || '';

      // Extract cursor for pagination
      if (entryId.startsWith('cursor-bottom-')) {
        cursor = entry.content?.value;
        continue;
      }
      if (entryId.startsWith('cursor-top-')) {
        continue;
      }

      // Extract tweet result
      var tweetResult = entry.content?.itemContent?.tweet_results?.result;
      if (!tweetResult) continue;

      var parsed = parseTweetData(tweetResult);
      if (!parsed) continue;

      // Check cutoff
      if (parsed.timestamp_ms < cutoffMs) {
        reachedCutoff = true;
        continue;
      }

      // Deduplicate
      var isDupe = false;
      for (var k = 0; k < allTweets.length; k++) {
        if (allTweets[k].id === parsed.id) { isDupe = true; break; }
      }
      if (!isDupe) {
        allTweets.push(parsed);
        pageTweets++;
      }

      if (!oldestOnPage || parsed.timestamp_ms < oldestOnPage) {
        oldestOnPage = parsed.timestamp_ms;
      }
    }

    var oldestStr = oldestOnPage ? new Date(oldestOnPage).toISOString().split('T')[0] : '?';
    console.log('📄 Page ' + pageNum + ': +' + pageTweets + ' tweets (oldest: ' + oldestStr + ', total: ' + allTweets.length + ')');

    if (!cursor) {
      console.log('ℹ️  No more pages (no cursor)');
      break;
    }

    await sleep(DELAY_MS);
  }

  // --- STEP 3: Sort and output ---
  allTweets.sort(function (a, b) { return b.timestamp_ms - a.timestamp_ms; });

  var result = {
    meta: {
      username: USERNAME,
      user_id: userId,
      scraped_at: new Date().toISOString(),
      cutoff_date: cutoffDate.toISOString(),
      total_tweets: allTweets.length,
      date_range: allTweets.length > 0
        ? {
            newest: allTweets[0].created_at,
            oldest: allTweets[allTweets.length - 1].created_at,
          }
        : null,
    },
    tweets: allTweets,
  };

  var json = JSON.stringify(result, null, 2);

  // Copy to clipboard
  try {
    await navigator.clipboard.writeText(json);
    console.log('📋 JSON copied to clipboard!');
  } catch (e) {
    console.log('⚠️  Could not copy to clipboard. Use copy(json) or save via console.');
  }

  // Store on window for easy access
  window.__scraped_tweets = result;

  console.log('');
  console.log('✅ Done! ' + allTweets.length + ' tweets collected.');
  console.log('');
  console.log('To save: copy the JSON from clipboard, or run:');
  console.log('  copy(JSON.stringify(window.__scraped_tweets, null, 2))');
  console.log('');
  console.log('Or download as file:');
  console.log('  var a = document.createElement("a");');
  console.log('  a.href = URL.createObjectURL(new Blob([JSON.stringify(window.__scraped_tweets, null, 2)], {type:"application/json"}));');
  console.log('  a.download = "yacineMTB_tweets.json"; a.click();');

  return result;
})();
