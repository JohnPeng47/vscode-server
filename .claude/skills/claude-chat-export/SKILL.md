---
name: claude-chat-export
description: Export a Claude.ai chat to a Markdown file. Use when the user asks to export, save, or parse a Claude chat conversation. Requires the /browser skill to be available.
---

# Prompt: Export a Claude.ai Chat to Markdown

You are given a Claude.ai chat URL. Your job is to open the chat in the browser, run the parser script, and save the resulting Markdown file.

---

## Prerequisites

- The `/browser` skill must be available (Chrome + extension running).
- The user must be logged into claude.ai in their browser.

## Steps

1. **Open the chat URL** using `/browser` — call `list-browsers` if this is the first browser command in the session, then use `tabs_create` to open the URL in a new tab (name: `"Chat Export"`).

2. **Wait for the page to load** — call `wait` with ~3000ms.

3. **Read the parser script** from `data/scripts/claude_chat_parser.js` in this repo.

4. **Execute the script** in the browser tab via `javascript_tool`, passing the full script contents as the `code` argument. The script returns the Markdown string and also triggers a `.md` file download in the browser.

5. **Save the Markdown output** — write the returned Markdown to a file. Default location: `data/chats/<slug>.md` where `<slug>` is derived from the chat title (lowercase, hyphens). Ask the user if they want a different path.

6. **Report** — tell the user the file path, the number of user/assistant turns extracted, and the chat title.

## Notes

- The parser identifies assistant messages via `[data-is-streaming]` attributes and user messages as sibling containers without that attribute.
- Timestamps are extracted from user-turn text (e.g., "4:00 PM").
- "Searched the web" artifact lines and excessive blank lines are stripped.
- If the DOM structure has changed and the script returns an error or empty output, inspect the page with `read_page` or `screenshot` and adapt.
