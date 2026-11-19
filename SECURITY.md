# Security and privacy

## What the shortcuts can do

Inbox Triage uses one Google OAuth scope, `https://www.googleapis.com/auth/gmail.modify`. It can read messages and change labels, move messages to Trash and create drafts. It **cannot permanently delete** mail. It never sends mail: unsubscribe-by-email creates a draft that you send yourself.

## Where secrets live

- The OAuth client ID, client secret and refresh token live in `iCloud Drive/.config/inbox-triage/secrets.json`, a file you create. They are not in this repository, in the generated shortcuts or in `config.json`.
- `bin/gmail-auth` prints the refresh token to the terminal and never writes it to disk.
- The secrets file is readable by anything with access to your iCloud Drive (your devices, and any tool you run there). Treat the refresh token like a password: it gives read and modify access to the mailbox.
- Only the **InboxTriage Token** shortcut reads the secrets. It sends them only to `oauth2.googleapis.com` and outputs a one-hour access token. That token is only sent to `gmail.googleapis.com`. The unsubscribe POST goes to the sender's URL with no Authorization header (enforced by `tests/test_generator.py`).
- To revoke access, remove the app at <https://myaccount.google.com/permissions>.

## Where your mail goes

- Classification and summaries run on Apple's **on-device** model.
- Rule proposals run on **Locally AI**, also on the device. They receive sender, subject, decisions and your hints, never message bodies.
- Reports go to Apple Notes, and logs to iCloud Drive (`log/last-run.txt`, `log/last-report.txt`, overwritten every run). Both contain senders and subjects, so they stay in your iCloud and out of this repository. Personal config and rules live in the gitignored `local/` folder.

## Reporting a problem

Please open a GitHub issue. Don't include tokens, message ids or mail content.
