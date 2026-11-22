# Changelog

## 0.2.0 (unreleased)

- Review page: after a Default or Kept run, the Engine opens `docs/review.html` (GitHub Pages) in the browser with the run's report zipped and base64url-encoded after `#v1.` in the link, so it never reaches a server. Each message is a card with decision buttons and a hint field. Submit runs InboxTriage with the corrections as tagged report lines, the same format and parser as a shared note.
- `reviewUI` config: `"both"` (default: page and note), `"web"` or `"notes"`. `reviewUrl` points a fork at its own page. The note starts with a link to the page.
- No hint, no rule: corrections without a hint are applied to that message only. Only hinted corrections go to the Locally AI proposals and `bin/learn`, and the proposal prompt says not to generalize beyond the hint.
- The review page shows each message once (a flagged message used to appear under Needs you and again under its decision).
- KEEP messages get a two-sentence summary (`prompts/summary-keep.txt`) in the note and on the review page, for context without opening the message.
- Review page: summaries are collapsed under "Summary" so the page stays short; the hint field reads "Optional hint to update rules".
- Report links: only Open in Mail. The Gmail web link is gone (Gmail on the web opened the inbox, not the message).
- Reports end with the Engine version; `bin/deploy` gives the shortcuts the deploy time.
- Tests for the page (node: payload decoding, report parsing, Submit text) and a Python round trip through the shortcut's feedback patterns. CI runs both.

## 0.1.1 (2026-11-19)

- Fix: feedback runs ignored the corrected decisions. The forced-decision lookup's pattern contains the message id, and the id had ended up in the replacement text instead of the Find pattern. A test now runs the generated lookup.
- Notes no longer show the title twice: the title comes from Create Note's name only.
- The model's rule proposals are saved as `feedback/proposed-rules.txt` (iOS saves text as .txt).

## 0.1.0 (2026-11-19)

First public release.

- Three generated shortcuts: **InboxTriage Token** (secrets → access token), **InboxTriage Engine** (triage), **InboxTriage** (menu, Kept view, Custom runs, feedback via the share sheet).
- Triage actions: KEEP, ARCHIVE, DELETE, UNSUBSCRIBE and SUMMARIZE (low, moderate, high, confirmations). Sender and content rules run first; Apple's on-device model decides the rest.
- Safety switches `dryRun`, `allowDelete` and `allowUnsubscribe`; keep on doubt; an `AutoTriage` label on every change; RFC 8058 one-click unsubscribe only; mailto unsubscribes as drafts that are never sent.
- `AutoTriage/Kept` label so kept mail isn't re-triaged; thread collapse; adjustable `ignoreHours`.
- Report as an Apple Note: Needs you, per-action sections and summaries by level, with Apple Mail (`message://`) and Gmail web links. In dry runs the headings say "Would …".
- Feedback loop: typed `x?hint)` tags, applied by sharing the note. Locally AI proposes rule changes (never applied automatically), and `bin/learn` produces a reviewed diff of the rules.
- Settings, rules and prompts are read from iCloud Drive at run time. Personal copies stay in the gitignored `local/` folder; `bin/deploy` never overwrites them with examples.
- Tests for the generated plists' invariants, the regex patterns and `bin/learn`; ruff; CI on Python 3.11 and 3.13.

The fixes that led to these invariants are described in [docs/LESSONS.md](docs/LESSONS.md).
