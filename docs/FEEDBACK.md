# The feedback loop

The triage gets better from corrections. Prompts alone don't fix it: the on-device model is small, so the lasting fix for a recurring mistake is a rule. Rules only change with a person's approval.

## 0. The review page (default)

After a Default or Kept run, the Engine opens the review page in the browser, and the report note starts with the same link. Each message is a card with buttons (Keep, Archive, Delete, Low, Moderate, High, Confirm, Unsub, Release; tap again to clear) and an optional hint field. **Submit** runs InboxTriage with one tagged line per correction, exactly the lines described below, so the rest of this page applies unchanged. The browser asks before switching to Shortcuts each time.

How the data travels: the report is zipped by Shortcuts' Make Archive, base64url-encoded and put after `#v1.` in the link. Browsers never send the part after `#` to the server, and the page (`docs/review.html`) makes no network requests and has a Content Security Policy that forbids them. The link does stay in the browser's history. Set `reviewUI` to `"notes"` to turn the page off, or `"web"` to skip the note.

## 1. Mark mistakes in the report note

Every report line ends in the Gmail id:

```text
Ticket Seller — Big game this weekend · UNSUBSCRIBE · keep · rule · id:18f3c2a9e0b4d7c2
```

Put a tag at the start of the line: a two-letter code, an optional hint, and `)`.

| Code | Meaning |
|---|---|
| `xk)` | keep: back to the inbox (out of Trash if needed), marked Kept |
| `xa)` | archive |
| `xd)` | delete (archive while `allowDelete` is off) |
| `xl)` / `xm)` / `xh)` | summarize at low / moderate / high interest |
| `xc)` | summarize as a confirmation |
| `xu)` | unsubscribe |
| `xr)` | release from Kept: the next run triages it again |
| `xt)` | tag only: add the hint's tag, keep the decision |

```text
xm this is regular work business) Department Office — Faculty Meeting: Friday, Noon · KEEP · keep · model · id:…
xd) Music Shop — Shop Black Friday Early! · KEEP·low · keep · model · id:…
```

- Upper or lower case both work (iOS capitalizes the first letter).
- Leading spaces, bullets and checkboxes before the code are ignored.
- The hint is everything up to the first `)`, so it can contain `(` but not `)`.
- **Tags.** A hint that starts with an identifier and a semicolon, `xk LoR; student requesting a letter of recommendation)`, adds the Gmail label `LoR` to that message (an existing label of that name in any case is reused, otherwise it is created). This happens even in a dry run, because you asked for it on that message. The text after the semicolon is the hint for the rules, and proposed rules can carry the tag (`"tag": "LoR"` in `rules.json`), so future matches get the label in live runs. Tags are letters, digits, `-` and `_`, up to 24 characters; `see notes; later` is not a tag. On the review page, typing a tag without tapping a button submits a tag-only correction.
- **No hint, no rule.** A correction without a hint is an action on that message only: it is applied and recorded, marked "action only" in the feedback-applied note, and never used for rule proposals (Locally AI or `bin/learn`). Add a hint when you want the correction to generalize, and the proposals stay within what the hint says.

Why typed codes and not checkboxes? Notes' checklist items can be written from Shortcuts, but they can't be read back per note: the checklist query has no filters, and no action returns a note's checklist items.

## 2. Apply: share the note to InboxTriage

In Notes: **Share > InboxTriage**. For each tagged line, the shortcut:

1. records the correction in `feedback/pending.tsv`;
2. sends all corrections (sender address, item, original and new decision, your hint) and the current `rules.json` to **Locally AI**, asking for proposed sender and content rules with a one-line reason each. The reply goes to `feedback/proposed-rules.txt` and into the "feedback applied" note. It is never applied, and an unparseable reply is shown raw;
3. runs the Engine on exactly those messages with your decisions;
4. records them in `feedback/applied.txt`, so sharing the same note again changes nothing.

Steps 1 and 2 come before the Engine run and step 4 after it, so a failed run can simply be shared again.

## 3. Approve rule changes on the phone

After Apply feedback, the review page opens again in **proposals** mode (also from the menu: **Review proposed rules**). Each proposal is a card: the rule in plain English, the hint it came from, and what it replaces or "New rule". Tap Approve or Reject, then **Save**. The page builds the new `rules.json` (JavaScript validates every proposal: known action, a level for SUMMARIZE, a valid tag, a `from` or `keyword`) and hands it to InboxTriage as `RULES-UPDATE v1 len=<n>` plus base64 lines. InboxTriage writes it only if the length matches and it looks like rules.json, after saving the old file as `feedback/rules-backup-<time>.txt`. Every decision is appended to `feedback/rules-log.txt`, and the pending proposals are cleared. Rejected proposals are hidden on the page and listed to Locally AI as "never propose again". Nothing is applied without your Approve.

A new rule is added last and overrides broader rules for its own address (the last match wins); only a rule with the same address and subject, or the same keyword, is replaced.

The update rides in a `shortcuts://` link, so it is limited by URL length; a rules.json of a few hundred rules (tens of kilobytes) fits.

## 4. Learn: rule changes on the Mac

```sh
bin/learn            # proposal only: a diff of rules.json, plus what needs a person
bin/learn --apply    # after you approve: write local/rules.json, deploy, clear pending.tsv
bin/deploy --pull-rules   # bring rules approved on the phone into local/ (bin/learn and bin/deploy do this first)
```

`bin/deploy` and `bin/learn` first pull a `rules.json` changed on the phone into `local/` (and commit it there). `local/.deployed-rules.sha` records what was last deployed; if both the phone and `local/` changed, `bin/deploy` stops instead of overwriting either.

How `bin/learn` proposes (tested in `tests/test_learn.py`):

- A sender whose corrections all agree becomes a sender rule, added last so it overrides broader rules (last match wins) for that address only. A rule for the same address and subject is replaced.
- A single KEEP (an "undo") is usually about that one message, so a sender needs two before it becomes a KEEP rule.
- Conflicting corrections, RELEASE, and anything without a sender address are listed for a person. Those usually become a content rule or a prompt tweak in `prompts/content-rules.txt`.
- The model's proposals are shown next to the diff for comparison.
