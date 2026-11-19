# Changelog

## 0.1.0 (2026-11-19)

First public release.

- Three generated shortcuts: **InboxTriage Token** (secrets → access token), **InboxTriage Engine** (triage), **InboxTriage** (menu, Kept view, Custom runs, feedback via the share sheet).
- Triage actions: KEEP, ARCHIVE, DELETE, UNSUBSCRIBE and SUMMARIZE (low, moderate, high, confirmations). Sender and content rules run first; Apple's on-device model decides the rest.
- Safety switches `dryRun`, `allowDelete` and `allowUnsubscribe`; keep on doubt; an `AutoTriage` label on every change; RFC 8058 one-click unsubscribe only; mailto unsubscribes as drafts that are never sent.
- `AutoTriage/Kept` label so kept mail isn't re-triaged; thread collapse; adjustable `ignoreHours`.
- Report as an Apple Note: Needs you, per-action sections and summaries by level, with Apple Mail (`message://`) and Gmail web links. In dry runs the headings say "Would …".
- Feedback loop: typed `x?hint)` tags, applied by sharing the note. Locally AI proposes rule changes (never applied automatically), and `bin/learn` produces a reviewed diff of the rules.
- Settings, rules and prompts are read from iCloud Drive at run time. Personal copies stay in the gitignored `local/` folder; `bin/deploy` never overwrites them with examples.
- Tests for the generated plists' invariants, the regex patterns and `bin/learn`; ruff; CI on Python 3.9 and 3.12.

The fixes that led to these invariants are described in [docs/LESSONS.md](docs/LESSONS.md).
