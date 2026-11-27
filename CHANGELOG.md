# Changelog

## 0.3.0 (unreleased)

- Nothing blocks a run any more: every message (errors, "Rules updated", "No new feedback", Clean up) is a notification, not an alert that waited unseen when you had switched apps. Errors still stop the run, after saving `log/last-error.txt`. SETUP.md lists the one-time permission prompts. Version 0.3.1.

- Approve rules on the phone: after Apply feedback (or from the menu's Review proposed rules), the review page shows each proposed rule with its hint and what it replaces, with Approve/Reject. Saving sends the new rules.json to InboxTriage, which checks its length and shape, backs up the old file in `feedback/`, writes it, and logs every decision in `feedback/rules-log.txt`. Rejected proposals don't come back.
- New rules no longer remove broader rules; they are added last and override them for their own address (last match wins), in both bin/learn and the page.
- `bin/deploy` and `bin/learn` pull phone-approved rules into `local/` first and stop if both sides changed.

## 0.2.0

- Review page: after a Default or Kept run, the Engine opens `docs/review.html` (GitHub Pages) in the browser with the run's report zipped and base64url-encoded after `#v1.` in the link, so it never reaches a server. Each message is a card with decision buttons and a hint field. Submit runs InboxTriage with the corrections as tagged report lines, the same format and parser as a shared note.
- `reviewUI` config: `"both"` (default: page and note), `"web"` or `"notes"`. `reviewUrl` points a fork at its own page. The note starts with a link to the page.
- Tags: a hint that starts with `Tag;` ("LoR; student requesting a letter of recommendation") adds the Gmail label `LoR` to that message, even in a dry run, reusing an existing label of that name in any case. New code `xt` tags without changing the decision; on the review page a typed tag alone counts. The rest of the hint goes to the rule proposals, and rules can carry a `tag` that labels future matches in live runs. Report lines show `#tag`.
- No hint, no rule: corrections without a hint are applied to that message only. Only hinted corrections go to the Locally AI proposals and `bin/learn`, and the proposal prompt says not to generalize beyond the hint.
- The review page shows each message once (a flagged message used to appear under Needs you and again under its decision).
- Notes gap after an email address in a subject (Google Calendar invites put the invitee's address there): subjects, sender names, summaries and feedback-applied entries show `@` as `＠`, as `&` became `＆`. Engine 0.2.1.
- Summaries say what the body adds, not who sent it: the prompts say the sender and subject are already shown, with a good/bad example for Keep. Before summarizing, links, preheader filler, invisible characters and quoted replies are removed, so the 3000-character budget holds the content.
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
