# Setup

You need an iPhone with Apple Intelligence (iOS 26 or later), a Gmail or Google Workspace account, and a Mac (to sign in, and to generate and sign the shortcuts). [Locally AI](https://locallyai.app) is optional and is used for rule proposals.

## 1. Google Cloud (once, about 10 minutes)

1. At <https://console.cloud.google.com>, create a project (e.g. "Inbox Triage").
2. **APIs & Services > Library > Gmail API > Enable.**
3. **Google Auth Platform** (OAuth consent screen):
   1. **Branding:** app name, user support email, developer contact. For an External app, Google also wants an application home page, a privacy policy link and an authorized domain. This repo's `docs/` folder holds a minimal [home page](https://marcus-darden.github.io/inbox-triage/) and [privacy policy](https://marcus-darden.github.io/inbox-triage/privacy.html) served by GitHub Pages. Fork and adapt them. Leave the logo empty, because a logo triggers brand verification.
   2. **Audience:** External, then **Publish app** (In production). In Testing status, refresh tokens expire after 7 days. Unverified personal apps work; you'll see an "unverified app" warning when you sign in.
4. **Credentials > Create credentials > OAuth client ID > Desktop app.** Note the client ID and secret.

## 2. Sign in and create the labels (Mac)

```sh
bin/gmail-auth
```

1. Paste the client ID and secret. The browser opens Google's sign-in page.
2. Running over ssh? The browser's redirect to `127.0.0.1` can't reach the script. Copy the address-bar URL and paste it into the terminal.
3. The script prints the refresh token (it never writes it to disk). It creates the Gmail labels `AutoTriage` and `AutoTriage/Kept`, and writes their ids to `local/config.json` (gitignored).

Create `iCloud Drive/.config/inbox-triage/secrets.json`:

```json
{"CLIENT_ID": "…", "CLIENT_SECRET": "…", "REFRESH_TOKEN": "…"}
```

## 3. Your settings

The repo ships examples. Your own copies live in `local/` (gitignored), and `bin/deploy` prefers them:

```text
local/config.json        from icloud/config.example.json   (bin/gmail-auth creates it)
local/rules.json         from icloud/rules.example.json
local/prompts/*.txt      optional overrides of icloud/prompts/*.txt
```

`config.json` keys:

| Key | Default | Meaning |
|---|---|---|
| `dryRun` | `"true"` | `"true"` reports only. Quoted strings, not JSON booleans: the shortcut compares text. |
| `allowDelete` | `"false"` | Allow moving to Trash. Otherwise deletes become archives. |
| `allowUnsubscribe` | `"false"` | Allow the one-click POST and mailto drafts. |
| `minConfidence` | `0.8` | Below this, a model decision becomes KEEP. |
| `maxMessages` | `25` | Messages per run. |
| `ignoreHours` | `24` | Skip mail newer than this (`older_than:<n>h`). |
| `query` | `in:inbox -is:starred` | Base Gmail search. |
| `auditLabelId`, `keptLabelId` | set by `bin/gmail-auth` | Ids of `AutoTriage` and `AutoTriage/Kept`. |
| `feedbackModel` | `"locally"` | Model for rule proposals: `"locally"` or `"apple"`. |
| `reviewUI` | `"both"` | Where a run's report goes: `"both"` (review page and note), `"web"` or `"notes"`. |
| `reviewUrl` | this repo's Pages | The review page. A fork can serve its own `docs/review.html`. |

## 4. Build and deploy (Mac)

```sh
bin/build-shortcut   # writes build/*.unsigned.shortcut and signs build/*.shortcut
bin/deploy           # copies config, rules, prompts and shortcuts to iCloud Drive/Shortcuts/EmailTriage
```

`bin/deploy` never overwrites a config, rules or prompt file in iCloud with an example. Only files from `local/` replace what's there.

## 5. Install on the iPhone

1. In **Files > iCloud Drive > Shortcuts > EmailTriage** (or from the unzipped `InboxTriage-0.1.0.zip` on the [Releases](https://github.com/marcus-darden/inbox-triage/releases) page), open and **Add** in this order: **InboxTriage Token**, **InboxTriage Engine**, **InboxTriage**. Delete old copies first, so the names stay exact. A copy imported as "… 2" breaks Run Shortcut.
2. Run **InboxTriage** from its tile (not the editor) and grant every prompt: folder access for `.config/inbox-triage` and the Gmail sites. If the secrets alert appears, open the shortcut in the Mac Shortcuts app and pick the `.config/inbox-triage` folder in the first Get File action (Cmd+Shift+. shows hidden folders).
3. Check the dry-run report note. Mark mistakes, share the note to InboxTriage, then run `bin/learn` on the Mac.
4. **Automation:** Shortcuts > Automation > Time of Day (e.g. 7:00 and 18:00) > Run Immediately > *Run Shortcut* **InboxTriage** with the input `default`.
5. When the reports look right, set `dryRun` to `"false"` in `local/config.json` and run `bin/deploy`. Turn on `allowDelete` and `allowUnsubscribe` later, one at a time.
