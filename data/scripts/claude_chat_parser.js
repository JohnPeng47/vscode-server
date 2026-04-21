// ============================================================================
// Claude.ai Chat Page → Markdown Parser
// ============================================================================
//
// WHAT THIS DOES:
//   Extracts conversation messages from a Claude.ai chat page and converts
//   them into a clean Markdown file with user/AI messages clearly separated.
//
// HOW TO RUN:
//   1. Open the target Claude.ai chat in Chrome (you must be logged in)
//   2. Execute this script in the browser console (or via browser automation)
//   3. Returns a Markdown string; also triggers a download of the .md file
//
// CAVEATS:
//   - Requires an active Claude.ai session
//   - Relies on DOM structure — may break if Anthropic redesigns the chat UI
//   - Identifies AI messages via [data-is-streaming] attribute on containers
//   - User messages are the sibling containers without that attribute
//   - Timestamps are extracted via regex from user-turn text
//   - "Searched the web" artifact lines are stripped for cleanliness
//   - Inline citation source labels (e.g. "arXiv", "GitHub") on their own
//     lines are stripped
//
// ============================================================================

(function parseClaudeChat() {
  "use strict";

  // ── 1. Title & slug ─────────────────────────────────────────────────

  const title = document.title.replace(/ - Claude$/, "").trim();
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+$/, "");

  // ── 2. Find the turn-level container ────────────────────────────────
  //
  // Claude.ai renders conversation turns as direct children of a flex
  // column container.  Each child is either a user turn (no
  // [data-is-streaming] descendant) or an assistant turn (has one).

  const turnContainer = document.querySelector(
    ".flex-1.flex.flex-col.px-4"
  );

  if (!turnContainer) {
    return "ERROR: Could not locate the conversation container.";
  }

  const children = Array.from(turnContainer.children);

  // ── 3. Walk children and classify each as user / assistant ──────────

  const turns = []; // { role: "user"|"assistant", text: string }

  for (const child of children) {
    const text = (child.innerText || "").trim();
    if (!text) continue; // skip spacers / empties

    const isAssistant = !!child.querySelector("[data-is-streaming]");

    turns.push({
      role: isAssistant ? "assistant" : "user",
      text,
    });
  }

  // ── 4. Clean up and build Markdown ──────────────────────────────────

  const TS_RE = /\d{1,2}:\d{2}\s*[AP]M/i;

  function cleanUserText(raw) {
    // Strip trailing timestamp line
    const lines = raw.split("\n");
    const cleaned = lines.filter((l) => !TS_RE.test(l.trim()) || l.trim().length > 12);
    return cleaned.join("\n").trim();
  }

  function extractTimestamp(raw) {
    const m = raw.match(TS_RE);
    return m ? m[0] : "";
  }

  function cleanAssistantText(raw) {
    return raw
      .replace(/^Searched the web\n?/gm, "") // remove search-artifact lines
      .replace(/\n{3,}/g, "\n\n") // collapse excessive blank lines
      .trim();
  }

  const md = [];
  md.push(`# ${title}\n`);
  md.push(
    `> Exported from [claude.ai](${window.location.href}) on ${
      new Date().toISOString().split("T")[0]
    }\n`
  );
  md.push("---\n");

  for (const turn of turns) {
    if (turn.role === "user") {
      const ts = extractTimestamp(turn.text);
      const tsLabel = ts ? ` *(${ts})*` : "";
      md.push(`## User${tsLabel}\n`);
      md.push(cleanUserText(turn.text));
      md.push("");
    } else {
      md.push(`## Assistant\n`);
      md.push(cleanAssistantText(turn.text));
      md.push("\n---\n");
    }
  }

  const markdown = md.join("\n");

  // ── 5. Trigger download ─────────────────────────────────────────────

  const blob = new Blob([markdown], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${slug}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  // Also return the markdown for callers (browser automation, etc.)
  return markdown;
})();
