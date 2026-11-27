// Tests for docs/review.html's pure functions: run with `node --test tests/`.
// The page's script is evaluated without a DOM (boot() only runs when `document` exists).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { deflateRawSync, gzipSync } from "node:zlib";
import vm from "node:vm";

const here = new URL(".", import.meta.url);
const html = readFileSync(new URL("../docs/review.html", here), "utf8");
const script = /<script>([\s\S]*?)<\/script>/.exec(html)[1];
const page = vm.createContext({ TextDecoder, atob, btoa, Blob, Response, DecompressionStream, Uint8Array, DataView });
vm.runInContext(script + "\n;globalThis.api = { decodePayload, parseReport, feedbackLine, submitText, submitUrl, tagOf, buildChoices, " +
                "isProposals, splitBundle, parseProposals, applyRules, replaced, ruleText, rulesUpdateText, " +
                "rejectedBefore, wasRejected };",
                page);
const { decodePayload, parseReport, feedbackLine, submitText, submitUrl, tagOf, buildChoices, isProposals,
        splitBundle, parseProposals, applyRules, replaced, ruleText, rulesUpdateText, rejectedBefore,
        wasRejected } = page.api;
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));   // values from another realm (vm)
const report = readFileSync(new URL("fixtures/demo-report.md", here), "utf8");

const b64url = (buf) => Buffer.from(buf).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

// A one-file zip as Shortcuts' Make Archive writes it (deflate, sizes in the central directory).
function zip(name, data) {
  const body = deflateRawSync(data), n = Buffer.from(name);
  const local = Buffer.alloc(30);
  local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(20, 4); local.writeUInt16LE(8, 8);
  local.writeUInt32LE(body.length, 18); local.writeUInt32LE(data.length, 22); local.writeUInt16LE(n.length, 26);
  const central = Buffer.alloc(46);
  central.writeUInt32LE(0x02014b50, 0); central.writeUInt16LE(8, 10); central.writeUInt32LE(body.length, 20);
  central.writeUInt32LE(data.length, 24); central.writeUInt16LE(n.length, 28); central.writeUInt32LE(0, 42);
  const cdOffset = local.length + n.length + body.length;
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
  end.writeUInt32LE(central.length + n.length, 12); end.writeUInt32LE(cdOffset, 16);
  return Buffer.concat([local, n, body, central, n, end]);
}

test("decodes zip, gzip and plain payloads to the same text", async () => {
  const data = Buffer.from(report);
  for (const bytes of [zip("report.txt", data), gzipSync(data), data]) {
    assert.equal(await decodePayload("#v1." + b64url(bytes)), report);
  }
});

test("rejects a link without a report", async () => {
  await assert.rejects(decodePayload(""), /no report/);
  await assert.rejects(decodePayload("#xyz"), /no report/);
});

test("parses the demo report into sections and items", () => {
  const r = parseReport(report);
  assert.equal(r.title, "Inbox Triage DEMO, Thu Nov 19 7:00 AM (dry run)");
  assert.match(r.info[0], /^DRY RUN/);
  const items = r.sections.flatMap((s) => s.items);
  assert.equal(items.length, 8);
  const chair = items.find((i) => i.id === "18f3c2a9e0b4d704");
  assert.equal(chair.sender, "Department Chair");
  assert.equal(chair.subject, "Call for teaching award nominations");
  assert.equal(chair.decision, "SUMMARIZE");
  assert.equal(chair.level, "high");
  assert.match(chair.summary, /^Nominations close Dec 5/);
  assert.match(chair.mail, /^message:\/\//);
  assert.equal(r.sections[0].heading, "Needs you");
});

test("feedback lines use the Notes tag format and drop ')' from hints", () => {
  const line = "Shop — Sale · KEEP · keep · model · id:abc";
  assert.equal(feedbackLine("a", "", line), "xa) " + line);
  assert.equal(feedbackLine("m", " work (dept) stuff\n", line), "xm work (dept stuff) " + line);
});

test("submit URL runs InboxTriage with the title and one line per choice", () => {
  const choices = [{ code: "d", hint: "", line: "A — B · KEEP · keep · model · id:1" },
                   { code: "l", hint: "sales", line: "C — D · ARCHIVE · archive · rule · id:2" }];
  const url = submitUrl("Run 1", choices);
  assert.ok(url.startsWith("shortcuts://run-shortcut?name=InboxTriage&input=text&text="));
  assert.equal(decodeURIComponent(url.split("text=")[1]), submitText("Run 1", choices));
  assert.equal(submitText("Run 1", choices),
               "Review page: Run 1\nxd) A — B · KEEP · keep · model · id:1\nxl sales) C — D · ARCHIVE · archive · rule · id:2\n");
});

test("a tag on the report line is parsed, and the id still is", () => {
  const r = parseReport("## Would keep\n\nA — B · KEEP · keep · rule · #LoR · id:abc\n");
  const it = r.sections[0].items[0];
  assert.equal(it.tag, "LoR");
  assert.equal(it.id, "abc");
  assert.equal(it.src, "rule");
});

test("tags: an identifier and a semicolon at the start of the hint", () => {
  assert.equal(tagOf("LoR; student requesting a letter"), "LoR");
  assert.equal(tagOf(" grant-2026 ; budget"), "grant-2026");
  assert.equal(tagOf("see notes; later"), "");
  assert.equal(tagOf("no tag here"), "");
  assert.equal(tagOf("x".repeat(25) + "; long"), "");
});

test("a tag typed without a button is a tag-only correction; other hints alone are not", () => {
  const chosen = new Map([["1", { code: "d", line: "L1 · id:1" }]]);
  const hints = new Map([["1", { hint: "sales", line: "L1 · id:1" }],
                         ["2", { hint: "LoR; student asking", line: "L2 · id:2" }],
                         ["3", { hint: "just a note", line: "L3 · id:3" }]]);
  const out = buildChoices(chosen, hints);
  // JSON: the page's arrays come from another realm (vm), so compare their contents.
  assert.equal(JSON.stringify(out.map((c) => [c.code, c.hint])), JSON.stringify([["d", "sales"], ["t", "LoR; student asking"]]));
});

const RULES = { _comment: "kept", rules: [{ from: "@deals.example.com", subject: "", action: "UNSUBSCRIBE", level: "", flag: "" },
                                       { from: "bot@example.org", subject: "Weekly", action: "DELETE", level: "", flag: "" }],
                content: [{ keyword: "letter of recommendation", action: "KEEP", level: "", flag: "needs-you" }] };
const PROPOSALS = "```json\n" + JSON.stringify({
  sender_rules: [{ from: "promo@deals.example.com", subject: "", action: "summarize", level: "Low", tag: "", reason: "sales" },
                 { from: "x@example.com", action: "SUMMARIZE", level: "", reason: "no level" },
                 { from: "", action: "DELETE" }],
  content_rules: [{ keyword: "Letter of Recommendation", action: "KEEP", level: "", tag: "LoR", reason: "students" },
                  { keyword: "grant", action: "ARCHIVE", tag: "bad tag" }] }) + "\n```";

test("a proposals bundle is told apart from a report and split into its parts", () => {
  const text = "# Proposed rules, Fri\n=== proposals ===\n{}\n=== rules ===\n{\"rules\":[]}\n=== log ===\n\n";
  assert.ok(isProposals(text));
  assert.ok(!isProposals(readFileSync(new URL("fixtures/demo-report.md", here), "utf8")));
  same(splitBundle(text), { title: "Proposed rules, Fri", proposals: "{}", rules: '{"rules":[]}', log: "" });
});

test("proposals are normalized and invalid ones are set aside", () => {
  const p = parseProposals(PROPOSALS);
  same(p.ok.map((x) => [x.kind, x.rule]), [
    ["sender", { from: "promo@deals.example.com", subject: "", action: "SUMMARIZE", level: "low", flag: "" }],
    ["content", { keyword: "Letter of Recommendation", action: "KEEP", level: "", flag: "", tag: "LoR" }]]);
  same(p.bad.map((x) => x.error), ["SUMMARIZE needs a level", "sender rule without 'from'", "bad tag 'bad tag'"]);
  assert.equal(parseProposals("Sorry, I can't").bad.length, 1);
});

test("approved rules replace the rules they supersede; others stay", () => {
  const p = parseProposals(PROPOSALS).ok;
  same(replaced(RULES, p[0].kind, p[0].rule).map((r) => r.from), []);   // broader rule stays
  const out = applyRules(RULES, p);
  same(out.rules.map((r) => r.from), ["@deals.example.com", "bot@example.org", "promo@deals.example.com"]);
  same(out.content.map((r) => r.tag || ""), ["LoR"]);
  assert.equal(out._comment, "kept");
  assert.equal(RULES.rules.length, 2);   // input untouched
  assert.equal(ruleText("content", p[1].rule), "Subject or preview contains “Letter of Recommendation” → keep, label #LoR");
});

test("the rules update carries its length and decodes to the same JSON", () => {
  const rules = { rules: [{ from: "café@example.com", subject: "", action: "KEEP", level: "", flag: "" }], content: [] };
  const text = rulesUpdateText(rules, [{ decision: "approved", kind: "sender", rule: rules.rules[0] }]);
  const [head, r64, l64] = text.split("\n");
  const json = Buffer.from(r64, "base64").toString("latin1");
  assert.equal(head, "RULES-UPDATE v1 len=" + json.length);
  assert.ok(/^[\x00-\x7f]*$/.test(json));          // ASCII, so the shortcut counts the same characters
  same(JSON.parse(json), rules);
  assert.match(Buffer.from(l64, "base64").toString(), /"decision": "approved"/);
});

test("rejected proposals are recognized from the log", () => {
  const rule = { keyword: "grant", action: "ARCHIVE", level: "", flag: "" };
  const log = JSON.stringify({ decision: "rejected", kind: "content", rule }) + "\nnot json\n" +
              JSON.stringify({ decision: "approved", kind: "content", rule: { keyword: "x", action: "KEEP" } });
  const rej = rejectedBefore(log);
  assert.equal(rej.length, 1);
  assert.ok(wasRejected(rej, "content", { ...rule, keyword: "Grant" }));
  assert.ok(!wasRejected(rej, "content", { ...rule, action: "DELETE" }));
});
