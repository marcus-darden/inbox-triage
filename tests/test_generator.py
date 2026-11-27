"""Invariants of the generated shortcuts. Each one guards against a failure seen on a real iPhone."""
import pytest
from conftest import NAMES

# Every action the generator may emit. A typo'd identifier imports as an unknown action.
KNOWN_ACTIONS = {
    "is.workflow.actions." + a for a in [
        "alert", "appendnote", "appendvariable", "askllm", "base64encode", "choosefrommenu", "comment",
        "conditional", "count", "detect.dictionary", "detect.text", "dictionary", "documentpicker.open",
        "documentpicker.save", "downloadurl", "exit", "filter.notes", "format.date", "getrichtextfromhtml",
        "gettext", "getvalueforkey", "notification", "output", "repeat.each", "runworkflow", "setvariable",
        "text.replace", "text.split", "urlencode", "ask", "adjustdate", "makezip", "openurl", "url",
    ]
} | {
    "com.apple.mobilenotes.SharingExtension",       # Create Note
    "com.apple.Notes.DeleteNotesLinkAction",        # Delete Notes
    "app.locallyai.Locally.AskLocallyIntent",       # Locally AI
}
TEXT_CONDITIONS = {4, 5, 8, 9, 99, 999}  # is, is not, begins with, ends with, contains, does not contain
VALUE_CONDITIONS = {100, 101}            # has any value, does not have any value
BUILTIN_VARIABLES = {"Repeat Item", "Repeat Item 2", "Repeat Index"}


def actions_of(shortcuts, name):
    return shortcuts[name]["WFWorkflowActions"]


def all_actions(shortcuts):
    for name in NAMES:
        for a in actions_of(shortcuts, name):
            yield name, a["WFWorkflowActionIdentifier"], a["WFWorkflowActionParameters"]


def walk(value):
    """Yield every dict nested anywhere in a parameter value."""
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def if_input(params):
    return params["WFInput"]["Variable"]["Value"]


def is_text_typed(ref):
    return any(a.get("CoercionItemClass") == "WFStringContentItem" for a in ref.get("Aggrandizements", []))


def test_all_three_build(shortcuts):
    assert set(shortcuts) == set(NAMES)
    for name in NAMES:
        assert actions_of(shortcuts, name), name


@pytest.mark.parametrize("name", NAMES)
def test_control_blocks_are_balanced(shortcuts, name):
    stack = []
    for a in actions_of(shortcuts, name):
        p = a["WFWorkflowActionParameters"]
        mode = p.get("WFControlFlowMode")
        if mode is None:
            continue
        group = p["GroupingIdentifier"]
        if mode == 0:
            stack.append(group)
        elif mode == 1:
            assert stack and stack[-1] == group, "Otherwise outside its block"
        else:
            assert stack and stack.pop() == group, "End without a matching start"
    assert not stack, "unclosed block"


def test_every_action_identifier_is_known(shortcuts):
    unknown = {ident for _, ident, _ in all_actions(shortcuts)} - KNOWN_ACTIONS
    assert not unknown


def test_no_dotted_dictionary_keys(shortcuts):
    """A missing key anywhere in 'a.b.c' stops the whole run on iOS, so keys are read one at a time."""
    dotted = [(n, p["WFDictionaryKey"]) for n, i, p in all_actions(shortcuts)
              if i.endswith("getvalueforkey") and "." in str(p.get("WFDictionaryKey", ""))]
    assert not dotted


def test_text_comparisons_have_typed_inputs(shortcuts):
    """An untyped variable makes 'is' / 'contains' show as an invalid (red) condition in the editor."""
    bad = []
    for name, ident, p in all_actions(shortcuts):
        if ident.endswith("conditional") and p.get("WFCondition") in TEXT_CONDITIONS:
            ref = if_input(p)
            if not (is_text_typed(ref) or ref.get("Type") == "ActionOutput"):
                bad.append((name, ref.get("VariableName")))
    assert not bad


def test_text_variables_never_use_has_value(shortcuts):
    """An empty Text counts as 'has any value'; emptiness must be tested as 'value|' == '|'."""
    bad = [(name, if_input(p).get("VariableName")) for name, ident, p in all_actions(shortcuts)
           if ident.endswith("conditional") and p.get("WFCondition") in VALUE_CONDITIONS
           and is_text_typed(if_input(p))]
    assert not bad


@pytest.mark.parametrize("name", NAMES)
def test_every_variable_read_is_set_somewhere(shortcuts, name):
    """A variable that is read but never set is a typo; Shortcuts would silently treat it as empty."""
    acts = actions_of(shortcuts, name)
    written = BUILTIN_VARIABLES | {a["WFWorkflowActionParameters"]["WFVariableName"] for a in acts
                                   if a["WFWorkflowActionIdentifier"].endswith(("setvariable", "appendvariable"))}
    read = {d["VariableName"] for a in acts for d in walk(a["WFWorkflowActionParameters"])
            if d.get("Type") == "Variable" and "VariableName" in d}
    assert read <= written, sorted(read - written)


def test_create_note_uses_the_ios_body_key(shortcuts):
    """On iOS 26 the body goes in WFCreateNoteInput; 'contents' is ignored and leaves an empty note."""
    notes = [p for _, i, p in all_actions(shortcuts) if i == "com.apple.mobilenotes.SharingExtension"]
    assert notes
    for p in notes:
        assert "WFCreateNoteInput" in p and "contents" not in p


def test_gmail_token_only_goes_to_google(shortcuts):
    """The unsubscribe POST goes to a sender's URL, so it must never carry the Gmail Authorization header."""
    for _, ident, p in all_actions(shortcuts):
        if ident.endswith("downloadurl") and "Authorization" in str(p.get("WFHTTPHeaders", "")):
            url = p["WFURL"]["Value"]
            assert "googleapis.com" in url["string"] or url["attachmentsByRange"], url


def test_unsubscribe_post_has_no_headers(shortcuts):
    posts = [p for _, i, p in all_actions(shortcuts)
             if i.endswith("downloadurl") and "One-Click" in str(p.get("WFFormValues", ""))]
    assert posts
    for p in posts:
        assert "WFHTTPHeaders" not in p


def test_menu_skipped_for_the_automation(shortcuts):
    """The automation passes 'default'; the front end must branch on it before showing the menu."""
    acts = actions_of(shortcuts, "InboxTriage")
    first_menu = next(i for i, a in enumerate(acts) if a["WFWorkflowActionIdentifier"].endswith("choosefrommenu"))
    assert any(a["WFWorkflowActionParameters"].get("WFConditionalActionString") == "default"
               for a in acts[:first_menu])


def test_forced_decision_lookup_works(shortcuts):
    """Feedback runs look up 'id=ACTION level' in a force string with a pattern that contains the id.

    The pattern must be the Find text (a token string with the id variable in it), not the replacement:
    that mistake once turned every forced decision into garbage.
    """
    import re

    engine = actions_of(shortcuts, "InboxTriage Engine")
    finds = [a["WFWorkflowActionParameters"]["WFReplaceTextFind"] for a in engine
             if a["WFWorkflowActionIdentifier"].endswith("text.replace")
             and isinstance(a["WFWorkflowActionParameters"].get("WFReplaceTextFind"), dict)
             and "MsgId" in str(a["WFWorkflowActionParameters"]["WFReplaceTextFind"])]
    assert len(finds) == 1
    token = finds[0]["Value"]
    (ref,) = token["attachmentsByRange"].values()
    assert ref["VariableName"] == "MsgId"
    force = "aaa111=DELETE;bbb222=SUMMARIZE moderate;ccc333=KEEP;"
    for msg_id, want in [("aaa111", "DELETE"), ("bbb222", "SUMMARIZE moderate"), ("ccc333", "KEEP")]:
        pattern = token["string"].replace("￼", msg_id)
        assert re.sub(pattern, r"\1", force, count=1) == want
    pattern = token["string"].replace("￼", "zzz999")
    assert re.sub(pattern, r"\1", force, count=1) == force  # not forced: unchanged, the shortcut checks this


def test_every_prompt_file_read_ships_as_an_example(shortcuts):
    """bin/deploy seeds missing prompts from icloud/prompts/, so each prompt a shortcut reads must exist there."""
    import os

    from conftest import REPO
    paths = {p["WFGetFilePath"] for _, i, p in all_actions(shortcuts)
             if i.endswith("documentpicker.open") and isinstance(p.get("WFGetFilePath"), str)
             and p["WFGetFilePath"].startswith("EmailTriage/prompts/")}
    assert "EmailTriage/prompts/summary-keep.txt" in paths
    missing = [p for p in paths if not os.path.exists(os.path.join(REPO, "icloud", "prompts", os.path.basename(p)))]
    assert not missing


LABELS_JSON = """{
  "labels": [
    {
      "id": "CHAT",
      "name": "CHAT",
      "type": "system"
    },
    {
      "id": "Label_7",
      "name": "LOR",
      "type": "user"
    },
    {
      "id": "Label_8",
      "name": "LoRe",
      "type": "user"
    }
  ]
}"""


@pytest.mark.parametrize("name", NAMES[1:])
def test_tag_label_lookup_finds_existing_labels_in_any_case(shortcuts, name):
    """Tags reuse a Gmail label with the same name in any case; no match leaves the JSON (starting '{')."""
    import re

    finds = [a["WFWorkflowActionParameters"]["WFReplaceTextFind"]["Value"] for a in actions_of(shortcuts, name)
             if a["WFWorkflowActionIdentifier"].endswith("text.replace")
             and isinstance(a["WFWorkflowActionParameters"].get("WFReplaceTextFind"), dict)
             and '"name"' in str(a["WFWorkflowActionParameters"]["WFReplaceTextFind"])]
    assert finds
    for token in finds:
        for tag, want in [("LoR", "Label_7"), ("lor", "Label_7"), ("LoRe", "Label_8"), ("CHAT", "CHAT")]:
            assert re.sub(token["string"].replace("￼", tag), r"\1", LABELS_JSON, count=1) == want
        assert re.sub(token["string"].replace("￼", "Grants"), r"\1", LABELS_JSON, count=1).startswith("{")


@pytest.mark.parametrize("name, variables", [("InboxTriage Engine", {"SenderName", "Subject", "Summary"}),
                                             ("InboxTriage", {"SenderName", "Subject"})])
def test_note_text_has_no_bare_at_signs(shortcuts, name, variables):
    """Notes turns an address (a Google Calendar invite puts one in the subject) into a link with a large gap
    after it, so text written into notes shows '@' as the full-width '＠', as '&' became '＆'."""
    replaced = set()
    for a in actions_of(shortcuts, name):
        p = a["WFWorkflowActionParameters"]
        if a["WFWorkflowActionIdentifier"].endswith("text.replace") and p.get("WFReplaceTextFind") == "@":
            assert p["WFReplaceTextReplace"]["Value"]["string"] == "\uff20"
            refs = p["WFInput"]["Value"]["attachmentsByRange"].values()
            replaced |= {r.get("VariableName") for r in refs}
    assert variables <= replaced
