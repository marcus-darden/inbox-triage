"""The regular expressions the shortcuts run (as ICU patterns in Replace Text), checked with Python's re.

Each pattern is used as 'replace the whole text with $1'; when it doesn't match, the text comes back
unchanged, and the shortcut detects that. The helper below mimics that behaviour.
"""
import base64
import json
import re

import pytest

LINE = "Sun & Snow — Warren Miller Is Back · UNSUBSCRIBE · keep · rule · id:19a2bc3"


def whole(pattern, text, repl=r"\1"):
    """Shortcuts' Replace Text with a regex: replace the whole match, or return text unchanged."""
    return re.sub(pattern, repl, text, count=1)


def b64url(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def decode_like_the_shortcut(builder, data):
    d = data.replace("-", "+").replace("_", "/")
    d = whole(builder.PAD2_RE, d, r"\1==")
    d = whole(builder.PAD3_RE, d, r"\1=")
    return base64.b64decode(d).decode()


# ---- feedback tags -----------------------------------------------------------------------------

@pytest.mark.parametrize("line, code, hint", [
    ("xa) " + LINE, "a", ""),
    ("Xa) " + LINE, "a", ""),                                  # iOS capitalizes the first letter
    ("xl I'm interested in shoes) " + LINE, "l", "I'm interested in shoes"),
    ("XM  extra spaces  ) " + LINE, "m", "extra spaces"),
    ("xh keep these (from the dept) ) " + LINE, "h", "keep these (from the dept"),  # hint ends at first ')'
])
def test_tagged_lines(builder, line, code, hint):
    assert whole(builder.FEEDBACK_MARK_RE, line, "MARKED") == "MARKED"
    codes = [c for c in "kadlmhcurt" if whole(builder.feedback_code_re(c), line, "HIT") == "HIT"]
    assert codes == [code]
    assert whole(builder.FEEDBACK_HINT_RE, line) == hint
    assert whole(builder.FEEDBACK_ID_RE, line) == "19a2bc3"
    assert whole(builder.FEEDBACK_ORIGINAL_RE, line) == "UNSUBSCRIBE"


@pytest.mark.parametrize("line", [
    LINE,                                                  # untagged
    "xa " + LINE,                                          # old form without ')'
    "Hello (world) — ) no code · KEEP · keep · model · id:abc",  # ')' but no code
    "xz) " + LINE,                                         # unknown code
    "xa) a line with no id",                               # no id to act on
])
def test_untagged_lines_are_ignored(builder, line):
    assert whole(builder.FEEDBACK_MARK_RE, line, "MARKED") != "MARKED"


def test_item_text_drops_the_tag(builder):
    assert whole(builder.FEEDBACK_ITEM_RE, "xa) " + LINE) == "Sun & Snow — Warren Miller Is Back"


def test_original_keeps_only_the_action_word(builder):
    line = "xh) Dept — Awards · SUMMARIZE·high · archive · rule · id:x1"
    assert whole(builder.FEEDBACK_ORIGINAL_RE, line) == "SUMMARIZE"


# ---- message body extraction from Gmail's messages.get JSON -------------------------------------

def part(mime, text=None, parts=None, attachment=False):
    p = {"partId": "0", "mimeType": mime, "filename": "", "headers": [{"name": "Content-Type", "value": mime}]}
    if attachment:
        p["filename"] = "file.pdf"
        p["body"] = {"attachmentId": "ANGjdJ8", "size": 12345}
    else:
        p["body"] = {"size": len(text or ""), **({"data": b64url(text)} if text is not None else {})}
    if parts:
        p["parts"] = parts
        p["body"] = {"size": 0}
    return p


def message(payload):
    return json.dumps({"id": "abc", "threadId": "abc", "labelIds": ["INBOX"], "snippet": "snip",
                       "payload": payload}, indent=2)


PLAIN, HTML = "Plain text body, line one.\nLine two (with parentheses).", "<p>Hello <b>HTML</b></p>"
SHAPES = {
    "text/plain only": (part("text/plain", PLAIN), PLAIN, None),
    "text/html only (no parts at all)": (part("text/html", HTML), None, HTML),
    "multipart/alternative": (part("multipart/alternative", parts=[part("text/plain", PLAIN),
                                                                   part("text/html", HTML)]), PLAIN, HTML),
    "related > alternative + inline image": (
        part("multipart/related", parts=[part("multipart/alternative", parts=[part("text/plain", PLAIN),
                                                                             part("text/html", HTML)]),
                                          part("image/jpeg", attachment=True)]), PLAIN, HTML),
    "mixed > alternative + pdf": (
        part("multipart/mixed", parts=[part("multipart/alternative", parts=[part("text/plain", PLAIN),
                                                                           part("text/html", HTML)]),
                                       part("application/pdf", attachment=True)]), PLAIN, HTML),
    "mixed > html + pdf": (part("multipart/mixed", parts=[part("text/html", HTML),
                                                         part("application/pdf", attachment=True)]), None, HTML),
}


@pytest.mark.parametrize("shape", SHAPES)
def test_body_extraction(builder, shape):
    payload, plain, html = SHAPES[shape]
    raw = message(payload)
    got_plain = whole(builder.BODY_PLAIN_RE, raw)
    got_html = whole(builder.BODY_HTML_RE, raw)
    if plain is None:
        assert got_plain.startswith("{")  # no match: the shortcut falls back to HTML
    else:
        assert decode_like_the_shortcut(builder, got_plain) == plain
    if html is None:
        assert got_html.startswith("{")
    else:
        assert decode_like_the_shortcut(builder, got_html) == html


def test_no_body_part_falls_back(builder):
    raw = message(part("multipart/mixed", parts=[part("application/pdf", attachment=True)]))
    assert whole(builder.BODY_PLAIN_RE, raw).startswith("{")
    assert whole(builder.BODY_HTML_RE, raw).startswith("{")


@pytest.mark.parametrize("length", range(1, 13))
def test_base64_padding(builder, length):
    text = "x" * length
    assert decode_like_the_shortcut(builder, b64url(text)) == text


# ---- headers -----------------------------------------------------------------------------------

def metadata(from_value):
    # Google escapes < > & = as < etc. and quotes as \"; json.dumps with ensure_ascii escapes the same way
    raw = json.dumps({"id": "a", "payload": {"mimeType": "text/plain",
                                             "headers": [{"name": "From", "value": from_value}]}}, indent=2)
    for ch, esc in [("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("=", "\\u003d")]:
        raw = raw.replace(ch, esc)
    return raw


@pytest.mark.parametrize("from_value", [
    "Jane Doe <jane@example.com>",
    '"Ticket Seller @ Events" <events@tickets.example>',
    "plain@example.org",
    "R&D Team <rd@example.com>",
])
def test_from_header(builder, from_value):
    got = whole(builder.FROM_HEADER_RE, metadata(from_value))
    for esc, ch in [("\\u003c", "<"), ("\\u003e", ">"), ("\\u0026", "&"), ("\\u003d", "="), ('\\"', '"')]:
        got = got.replace(esc, ch)
    assert got == from_value


@pytest.mark.parametrize("from_value, name", [
    ("Jane Doe <jane@example.com>", "Jane Doe"),
    ('"Ticket Seller @ Events" <events@tickets.example>', "Ticket Seller @ Events"),
    ("plain@example.org", "plain@example.org"),
])
def test_sender_display_name(builder, from_value, name):
    assert whole(builder.SENDER_NAME_RE, from_value) == name


def test_unsubscribe_header(builder):
    header = "<mailto:leave@list.example?subject=unsubscribe>, <https://list.example/u/abc?x=1>"
    assert whole(builder.UNSUB_HTTPS_RE, header) == "https://list.example/u/abc?x=1"
    assert whole(builder.UNSUB_MAILTO_RE, header) == "leave@list.example"
    assert whole(builder.UNSUB_HTTPS_RE, "<mailto:only@list.example>").startswith("<mailto:")


@pytest.mark.parametrize("sender, shown", [
    ("someone@example.edu", "someone (example.edu)"),   # bare address: no autolink at line start
    ("Jane Doe", "Jane Doe"),
    ("R＆D Team", "R＆D Team"),
])
def test_bare_address_is_rewritten(builder, sender, shown):
    assert whole(builder.BARE_ADDRESS_RE, sender, r"\1 (\2)") == shown


@pytest.mark.parametrize("prefix", ["", "  ", "• ", "- ", "* ", "☐ ", "☑ ", "\t• "])
def test_tags_after_bullets_and_checkboxes(builder, prefix):
    line = prefix + "Xm a hint) " + LINE
    assert whole(builder.FEEDBACK_MARK_RE, line, "MARKED") == "MARKED"
    assert [c for c in "kadlmhcurt" if whole(builder.feedback_code_re(c), line, "HIT") == "HIT"] == ["m"]
    assert whole(builder.FEEDBACK_HINT_RE, line) == "a hint"
    assert whole(builder.FEEDBACK_ITEM_RE, line) == "Sun & Snow — Warren Miller Is Back"


# ---- tags in hints ------------------------------------------------------------------------------

@pytest.mark.parametrize("hint, tag, rest", [
    ("LoR; student requesting a letter of recommendation", "LoR", "student requesting a letter of recommendation"),
    ("  grant-2026 ;  budget questions", "grant-2026", "budget questions"),
    ("LoR;", "LoR", ""),
    ("student requesting a letter", None, None),          # no tag
    ("see notes; later", None, None),                     # words with a space before ';' are not a tag
    ("x" * 25 + "; too long", None, None),
])
def test_tag_in_hint(builder, hint, tag, rest):
    marked = whole(builder.TAG_HINT_RE, hint, builder.TAG_MARK + r"\1")
    if tag is None:
        assert not marked.startswith(builder.TAG_MARK)
        return
    assert marked == builder.TAG_MARK + tag
    assert whole(builder.TAG_REST_RE, hint) == rest


def test_tag_hint_ends_at_the_first_parenthesis(builder):
    line = "xk LoR; student (grad) asking) " + LINE
    assert whole(builder.FEEDBACK_HINT_RE, line) == "LoR; student (grad"
    assert [c for c in "kadlmhcurt" if whole(builder.feedback_code_re(c), "xt LoR;) " + LINE, "HIT") == "HIT"] == ["t"]


def test_body_cleanup_keeps_the_content(builder):
    body = ("Sam is making progress! " + "\u034f \u00ad " * 300 + "[View progress](https://example.com/very/long/"
            + "x" * 900 + ")\n\n\n3 Pages Completed (https://example.com/a)\n"
            + "> On Monday someone wrote:\n> old text\nThanks")
    for pattern, repl in builder.BODY_CLEANUP:
        body = re.sub(pattern, repl.replace("$1", r"\1"), body)
    assert body == "Sam is making progress! View progress\n3 Pages Completed\nThanks"
