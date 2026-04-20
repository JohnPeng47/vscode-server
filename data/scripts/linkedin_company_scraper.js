// ============================================================================
// LinkedIn Company Page Post Scraper (Voyager API)
// ============================================================================
//
// WHAT THIS DOES:
//   Scrapes all posts from a LinkedIn company page using LinkedIn's internal
//   Voyager GraphQL API, authenticated via the browser's existing session.
//
// HOW TO RUN:
//   1. Open the target company's LinkedIn page in Chrome
//   2. Execute this script in the browser console (or via browser automation)
//   3. Results are returned as a JSON object
//
// CAVEATS:
//   - Requires an active LinkedIn session (you must be logged in)
//   - Uses LinkedIn's internal/undocumented Voyager API — may break if
//     LinkedIn changes their API schema or query IDs
//   - The queryId for voyagerFeedDashOrganizationalPageUpdates may rotate;
//     if the script returns 400 errors, reload the company /posts/ page,
//     open DevTools Network tab, filter for "graphql", and grab the fresh
//     queryId from the organizational page updates request
//   - Timestamps are decoded from LinkedIn's activity snowflake IDs:
//     activityId >> 22 = Unix timestamp in milliseconds
//   - The API caps at ~500 results (total) regardless of how far back you go
//   - Rate limiting: 3-second pause between requests to be respectful
//
// PARAMETERS (edit below):
//   - orgUrn: The organizational page URN (find via Network tab or page source)
//   - cutoffMs: Posts older than this are excluded (default: July 1, 2025)
//   - count: Posts per API request (50 works, 10 is the default the UI uses)
//
// FINDING THE ORG URN:
//   1. Go to linkedin.com/company/COMPANY_NAME/posts/
//   2. Open DevTools > Network > filter "graphql"
//   3. Look for a request with "organizationalPageUrn" in the URL
//   4. The URN looks like: urn:li:fsd_organizationalPage:XXXXXXXX
//
// LAST TESTED: April 2026
// ============================================================================

(async function () {
  // --- CONFIGURATION ---
  var ORG_URN = 'urn:li:fsd_organizationalPage:35653234'; // Tailscale
  var CUTOFF_DATE = '2025-07-01T00:00:00Z';
  var COUNT_PER_REQUEST = 50;
  var DELAY_MS = 3000;
  var MAX_START = 1000; // safety limit

  // --- SETUP ---
  var csrf = document.cookie.match(/JSESSIONID="?([^;"]+)/)[1];
  var baseUrl = 'https://www.linkedin.com/voyager/api/graphql';
  // NOTE: This queryId may change. See CAVEATS above.
  var queryId = 'voyagerFeedDashOrganizationalPageUpdates.827e11d165078dd7a5afaf1cba734121';
  var cutoffMs = new Date(CUTOFF_DATE).getTime();

  var allPosts = [];
  var start = 0;
  var keepGoing = true;
  var seenIds = {};
  var requestCount = 0;

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // LinkedIn activity IDs are snowflake-style: right-shift by 22 bits
  // gives Unix timestamp in milliseconds.
  function activityIdToMs(idStr) {
    return Number(BigInt(idStr) >> 22n);
  }

  function extractActivityId(urn) {
    var m = urn.match(/urn:li:activity:(\d+)/);
    return m ? m[1] : null;
  }

  // --- PAGINATION LOOP ---
  while (keepGoing && start < MAX_START) {
    var url = baseUrl +
      '?variables=(count:' + COUNT_PER_REQUEST +
      ',start:' + start +
      ',moduleKey:ORGANIZATION_MEMBER_FEED_DESKTOP' +
      ',organizationalPageUrn:' + encodeURIComponent(ORG_URN) +
      ')&queryId=' + queryId;

    var resp = await fetch(url, {
      headers: {
        'csrf-token': csrf,
        'accept': 'application/vnd.linkedin.normalized+json+2.1'
      }
    });
    var body = await resp.json();

    // Check for API errors
    if (body.data && body.data.status && body.data.status >= 400) {
      console.error('API error at start=' + start, body.data.status);
      keepGoing = false;
      break;
    }

    var included = body.included || [];

    // The feed data is nested: body.data.data.feedDash...
    var feedData = body.data
      && body.data.data
      && body.data.data.feedDashOrganizationalPageUpdatesByOrganizationalPageRelevanceFeed;
    var elements = feedData && feedData['*elements'] || [];
    var paging = feedData && feedData.paging || {};
    var total = paging.total || 0;

    // Collect social engagement counts (likes, comments, shares)
    var socialCounts = {};
    included.forEach(function (item) {
      if (item['$type'] === 'com.linkedin.voyager.dash.feed.SocialActivityCounts') {
        socialCounts[item.urn] = {
          likes: item.numLikes || 0,
          comments: item.numComments || 0,
          shares: item.numShares || 0
        };
      }
    });

    // Extract posts from Update objects in the included array
    included.forEach(function (item) {
      if (item['$type'] !== 'com.linkedin.voyager.dash.feed.Update') return;
      var urn = item.entityUrn || '';
      var activityId = extractActivityId(urn);
      if (!activityId || seenIds[activityId]) return;
      seenIds[activityId] = true;

      var tsMs = activityIdToMs(activityId);
      if (tsMs < cutoffMs) return; // skip posts before cutoff

      var text = '';
      if (item.commentary && item.commentary.text && item.commentary.text.text) {
        text = item.commentary.text.text;
      }
      var actorName = '';
      if (item.actor && item.actor.name && item.actor.name.text) {
        actorName = item.actor.name.text;
      }
      var activityUrn = 'urn:li:activity:' + activityId;
      var social = socialCounts[activityUrn] || { likes: 0, comments: 0, shares: 0 };

      allPosts.push({
        activityId: activityId,
        date: new Date(tsMs).toISOString(),
        actor: actorName,
        text: text,
        likes: social.likes,
        comments: social.comments,
        shares: social.shares,
        url: 'https://www.linkedin.com/feed/update/urn:li:activity:' + activityId
      });
    });

    requestCount++;
    console.log('Request ' + requestCount + ': start=' + start +
      ' elements=' + elements.length + ' total=' + total +
      ' collected=' + allPosts.length);

    // Stop if we've exhausted all pages
    if (elements.length === 0 || start + COUNT_PER_REQUEST >= total) {
      keepGoing = false;
    }

    start += COUNT_PER_REQUEST;
    if (keepGoing) await sleep(DELAY_MS);
  }

  // Sort newest first
  allPosts.sort(function (a, b) { return new Date(b.date) - new Date(a.date); });

  return {
    totalPosts: allPosts.length,
    requestsMade: requestCount,
    dateRange: allPosts.length > 0
      ? allPosts[allPosts.length - 1].date.split('T')[0] + ' to ' + allPosts[0].date.split('T')[0]
      : 'none',
    posts: allPosts
  };
})()
