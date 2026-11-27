"""bin/learn: turning feedback rows into proposed sender rules (never applied without approval)."""

RULES = {"rules": [{"from": "@deals.example.com", "subject": "", "action": "UNSUBSCRIBE", "level": "", "flag": ""},
                   {"from": "noreply@github.example", "subject": "Dependabot", "action": "DELETE", "level": "",
                    "flag": ""}],
         "content": []}
ADDRESSES = {"m1": "promo@deals.example.com", "m2": "promo@deals.example.com", "m3": "jane@example.org",
             "m4": "jane@example.org", "m5": "noreply@github.example", "m6": "bob@example.org"}


def row(msg_id, original, corrected, line="xa a hint) Sender — Subject · X · op · src · id:x"):
    return ["2026-11-19 10:00", "Inbox Triage, Thu Nov 19", msg_id, original, corrected, line]


def propose(learn, rows):
    return learn.propose(rows, RULES, ADDRESSES.get)


def test_to_rule(learn):
    assert learn.to_rule("SUMMARIZE moderate") == ("SUMMARIZE", "moderate", "")
    assert learn.to_rule("ARCHIVE") == ("ARCHIVE", "", "")
    assert learn.to_rule("RELEASE") is None
    assert learn.to_rule("TAG", "KEEP", "LoR") == ("KEEP", "", "LoR")


def test_duplicates_from_sharing_twice_are_dropped(learn):
    rows = [row("m1", "UNSUBSCRIBE", "SUMMARIZE low"), row("m1", "UNSUBSCRIBE", "SUMMARIZE low"), ["short"]]
    assert len(learn.unique_rows(rows)) == 1


def test_consistent_sender_becomes_a_rule_and_replaces_the_old_one(learn):
    rules, manual, senders = propose(learn, [row("m1", "UNSUBSCRIBE", "SUMMARIZE low"),
                                             row("m2", "UNSUBSCRIBE", "SUMMARIZE low")])
    froms = {r["from"]: r for r in rules["rules"]}
    assert "@deals.example.com" not in froms                     # old broader rule replaced
    assert froms["promo@deals.example.com"]["action"] == "SUMMARIZE"
    assert froms["promo@deals.example.com"]["level"] == "low"
    assert not manual and senders == 1


def test_subject_rules_are_kept(learn):
    rules, _, _ = propose(learn, [row("m5", "DELETE", "ARCHIVE")])
    assert any(r.get("subject") == "Dependabot" for r in rules["rules"])


def test_single_keep_is_not_a_sender_rule(learn):
    rules, manual, _ = propose(learn, [row("m6", "ARCHIVE", "KEEP")])
    assert rules == RULES and len(manual) == 1


def test_two_keeps_from_one_sender_become_a_rule(learn):
    rules, manual, _ = propose(learn, [row("m3", "ARCHIVE", "KEEP"), row("m4", "SUMMARIZE", "KEEP")])
    assert {"from": "jane@example.org", "subject": "", "action": "KEEP", "level": "", "flag": ""} in rules["rules"]
    assert not manual


def test_conflicting_corrections_need_a_person(learn):
    rules, manual, _ = propose(learn, [row("m3", "ARCHIVE", "KEEP"), row("m4", "KEEP", "DELETE")])
    assert rules == RULES and len(manual) == 2


def test_release_is_never_a_rule(learn):
    rules, manual, _ = propose(learn, [row("m6", "KEEP", "RELEASE")])
    assert rules == RULES and len(manual) == 1


def test_input_rules_are_not_modified(learn):
    before = repr(RULES)
    propose(learn, [row("m1", "UNSUBSCRIBE", "ARCHIVE")])
    assert repr(RULES) == before


def test_hint_is_read_like_the_shortcut(learn):
    assert learn.hint("xm regular work business) A — B · KEEP · keep · model · id:1") == "regular work business"
    assert learn.hint("Xd) A (dept) — B · KEEP · keep · model · id:1") == ""
    assert learn.hint("• xa  sales ) A — B · id:1") == "sales"


def test_corrections_without_a_hint_are_actions_only(learn):
    rows = [row("m1", "KEEP", "DELETE", "xd) Shop — Sale · KEEP · keep · model · id:m1"),
            row("m2", "KEEP", "DELETE", "xd not interested in sales) Shop — Sale · KEEP · keep · model · id:m2")]
    hinted, action_only = learn.split_hinted(rows)
    assert [r[2] for r in hinted] == ["m2"] and [r[2] for r in action_only] == ["m1"]


def test_tag_and_hint(learn):
    line = "xk LoR; student asking for a letter) A — B · id:1"
    assert learn.tag_and_hint(line) == ("LoR", "student asking for a letter")
    assert learn.tag_and_hint("xk see notes; later) A — B · id:1") == ("", "see notes; later")
    assert learn.tag_and_hint("xt LoR;) A — B · id:1") == ("LoR", "")


def test_tag_only_without_explanation_is_an_action(learn):
    rows = [row("m1", "KEEP", "TAG", "xt LoR;) A — B · KEEP · keep · model · id:m1")]
    assert learn.split_hinted(rows) == ([], rows)


def test_tagged_corrections_become_tagged_rules(learn):
    line = "xt LoR; student asking for a letter) A — B · KEEP · keep · model · id:m3"
    rules, manual, _ = propose(learn, [row("m3", "KEEP", "TAG", line), row("m4", "KEEP", "TAG", line)])
    assert {"from": "jane@example.org", "subject": "", "action": "KEEP", "level": "", "flag": "",
            "tag": "LoR"} in rules["rules"]
    assert not manual
