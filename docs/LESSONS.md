# Lessons learned: generating Apple Shortcuts

Shortcuts has no public file format and no API for building shortcuts. Generating 1,600 actions from Python meant finding out, one iPhone run at a time, what the format really accepts. Each item below cost at least one broken run, and each is now a test in `tests/` where that's possible.

## The platform

1. **iPhone Mail can't archive or delete from Shortcuts.** On iOS, Mail exposes only Find Message, Open Mailbox, Search in Mail, Send Email and Focus Filter. macOS Mail has Archive, Delete and Update Message, but not iOS. The Gmail API (via Get Contents of URL) was the only way to act on mail from the phone.
2. **Gmail's iPhone app has no link to a specific message.** The old `googlegmail:///cv=<thread>` scheme stopped deep-linking around 2022, and the mobile web ignores `#all/<id>`. `message://<Message-ID>` does open the exact message in Apple Mail, if the account is set up there.
3. **Notes can't report checklist ticks back.** Shortcuts can append checklist items, but the checklist query has no filters and no action returns a note's items. Feedback is typed instead (`xa)`, `xm hint)`).
4. **Runs from the editor can skip the "Allow … to access …" prompts** that a run from the shortcut's tile shows. A run with no permission fails quietly (e.g. zero messages). The first run after an import should be from the tile.
5. **Hidden folders.** The iPhone's file picker never shows dot-folders. Picking `.config/inbox-triage` in the **Mac** Shortcuts app (Cmd+Shift+.) works and syncs to the phone. The path inside the picked folder must be a bare file name: `secrets.json` works; `.config/inbox-triage/secrets.json` from iCloud Drive's root fails with "couldn't be opened".

## The plist format

6. **An empty Text counts as "has any value".** `If <text> has any value` is true for `""`. All text emptiness checks compare `value + "|"` with `"|"` instead (`test_text_variables_never_use_has_value`).
7. **A missing key in a dotted path aborts the whole run.** `Get Dictionary Value "payload.parts.1.parts"` stops the shortcut ("no value was found for dictionary key 'parts'") instead of returning nothing. Keys are read one level at a time, and nested MIME bodies are found with a regex over the raw JSON (`test_no_dotted_dictionary_keys`, `test_body_extraction`).
8. **Get Dictionary Value on Text aborts too** ("couldn't convert from Text"). Feedback runs pass plain id strings, so they branch before any dictionary lookup, and model replies are only checked with patterns on the phone.
9. **If inputs need a type.** Comparing an untyped named variable shows a red, invalid condition in the editor. Every text comparison coerces its input to Text (the editor's *Type* option, `WFCoercionVariableAggrandizement`) (`test_text_comparisons_have_typed_inputs`).
10. **Text parameters take token strings; variable parameters take attachments.** Replace Text's and URL Encode's `WFInput` are text (`WFTextTokenString`). Get Dictionary Value's input is an attachment (`WFTextTokenAttachment`). The wrong one imports as an empty placeholder.
11. **Some keys aren't what the metadata says.**
    - Create Note's body is `WFCreateNoteInput`. The intent metadata's `contents` is ignored on iOS 26, giving a note with only a title.
    - Format Date's custom pattern is `WFDateFormat`, not `WFDateFormatString`.
    - Count's input is `Input`.
    - Delete Notes is `com.apple.Notes.…` while Create Note is `com.apple.mobilenotes.SharingExtension`.
12. **An unrecognized parameter doesn't fail; it prompts.** A wrong key makes Shortcuts ask the user at run time, or silently drop the value.
13. **Notes' Markdown import mis-renders some text.** A bare email address at the start of a line left a gap of about 55 blank lines. Senders without a display name are now shown as `name (domain)`, and `&` as a full-width `＆`.
14. **iOS saves text as `.txt`**, whatever extension the path asks for.
15. **A broken regex is a runtime error.** A pattern with an unclosed bracket (a quoting slip in generated code) stopped every feedback run at that step. All patterns now live as named constants in the generator and are compiled and exercised by `tests/test_patterns.py`.

## The workflow

- **Ground truth beats documentation.** The most reliable sources were Apple's own Gallery shortcuts on macOS, app-intent metadata (`Metadata.appintents/extract.actionsdata`), and a shortcut exported from the phone (fetch `icloud.com/shortcuts/api/records/<id>` and decode the plist). Community references disagreed with each other, and so did Apple's own metadata (lesson 11).
- **Make the run observable.** Every run writes `log/last-run.txt` and `log/last-report.txt` to iCloud Drive, so problems could be diagnosed from a Mac without screenshots. Several bugs were found in those logs, not on the phone.
- **Turn every phone failure into an invariant.** The generator is easy to change, and the iPhone is slow to test on. The tests check the generated plists for the failure modes above before anything is signed.
