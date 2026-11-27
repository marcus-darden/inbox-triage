"""Round trip: the review page's Submit text, read by the same patterns the InboxTriage shortcut runs.

Node evaluates docs/review.html's functions on the demo report; Python applies the shortcut's patterns.
"""
import json
import os
import re
import shutil
import subprocess

import pytest
from conftest import REPO
from test_patterns import whole

NODE = shutil.which("node")
SCRIPT = r"""
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[1], "utf8");
const ctx = vm.createContext({ TextDecoder, atob, Blob, Response, DecompressionStream, Uint8Array, DataView });
vm.runInContext(/<script>([\s\S]*?)<\/script>/.exec(html)[1] + ";globalThis.api={parseReport,submitText};", ctx);
const r = ctx.api.parseReport(fs.readFileSync(process.argv[2], "utf8"));
const items = r.sections.flatMap((s) => s.items);
const choices = [{ code: "d", hint: "", line: items[0].line },
                 { code: "m", hint: "regular work (dept) business", line: items[1].line },
                 { code: "r", hint: "", line: items[2].line },
                 { code: "t", hint: "LoR; student asking for a letter", line: items[3].line }];
process.stdout.write(JSON.stringify({ text: ctx.api.submitText(r.title, choices),
                                      ids: choices.map((c, i) => items[i].id),
                                      decisions: choices.map((c, i) => items[i].decision) }));
"""


@pytest.fixture(scope="module")
def submitted():
    if not NODE:
        pytest.skip("node is not installed")
    out = subprocess.run([NODE, "-e", SCRIPT, os.path.join(REPO, "docs", "review.html"),
                          os.path.join(REPO, "tests", "fixtures", "demo-report.md")],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def test_input_is_routed_to_feedback(submitted):
    # InboxTriage treats text input containing "id:" as a shared note.
    assert "id:" in submitted["text"]
    assert submitted["text"].startswith("Review page: Inbox Triage DEMO")


def test_each_line_parses_like_a_tagged_note_line(builder, submitted):
    lines = [ln for ln in submitted["text"].split("\n")
             if whole(builder.FEEDBACK_MARK_RE, ln, "MARKED") == "MARKED"]
    assert len(lines) == 4
    codes = [[c for c in "kadlmhcurt" if whole(builder.feedback_code_re(c), ln, "HIT") == "HIT"] for ln in lines]
    assert codes == [["d"], ["m"], ["r"], ["t"]]
    assert [whole(builder.FEEDBACK_ID_RE, ln) for ln in lines] == submitted["ids"]
    assert [whole(builder.FEEDBACK_ORIGINAL_RE, ln) for ln in lines] == submitted["decisions"]
    assert whole(builder.FEEDBACK_HINT_RE, lines[1]) == "regular work (dept business"
    assert whole(builder.FEEDBACK_HINT_RE, lines[0]) == ""
    assert not re.search(r"\) \)", lines[1])
    hint = whole(builder.FEEDBACK_HINT_RE, lines[3])
    assert whole(builder.TAG_HINT_RE, hint, builder.TAG_MARK + r"\1") == builder.TAG_MARK + "LoR"
    assert whole(builder.TAG_REST_RE, hint) == "student asking for a letter"
