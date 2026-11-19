# The feedback loop

The triage gets better from corrections. Prompts alone don't fix it: the on-device model is small, so the lasting fix for a recurring mistake is a rule. Rules only change with a person's approval.

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

```text
xm this is regular work business) Department Office — Faculty Meeting: Friday, Noon · KEEP · keep · model · id:…
xd) Music Shop — Shop Black Friday Early! · KEEP·low · keep · model · id:…
```

- Upper or lower case both work (iOS capitalizes the first letter).
- Leading spaces, bullets and checkboxes before the code are ignored.
- The hint is everything up to the first `)`, so it can contain `(` but not `)`.

Why typed codes and not checkboxes? Notes' checklist items can be written from Shortcuts, but they can't be read back per note: the checklist query has no filters, and no action returns a note's checklist items.

## 2. Apply: share the note to InboxTriage

In Notes: **Share > InboxTriage**. For each tagged line, the shortcut:

1. records the correction in `feedback/pending.tsv`;
2. sends all corrections (sender address, item, original and new decision, your hint) and the current `rules.json` to **Locally AI**, asking for proposed sender and content rules with a one-line reason each. The reply goes to `feedback/proposed-rules.txt` and into the "feedback applied" note. It is never applied, and an unparseable reply is shown raw;
3. runs the Engine on exactly those messages with your decisions;
4. records them in `feedback/applied.txt`, so sharing the same note again changes nothing.

Steps 1 and 2 come before the Engine run and step 4 after it, so a failed run can simply be shared again.

## 3. Learn: approve rule changes on the Mac

```sh
bin/learn            # proposal only: a diff of rules.json, plus what needs a person
bin/learn --apply    # after you approve: write local/rules.json, deploy, clear pending.tsv
```

How `bin/learn` proposes (tested in `tests/test_learn.py`):

- A sender whose corrections all agree becomes a sender rule. It replaces any broader rule that matched the same address, but keeps subject-specific rules.
- A single KEEP (an "undo") is usually about that one message, so a sender needs two before it becomes a KEEP rule.
- Conflicting corrections, RELEASE, and anything without a sender address are listed for a person. Those usually become a content rule or a prompt tweak in `prompts/content-rules.txt`.
- The model's proposals are shown next to the diff for comparison.
