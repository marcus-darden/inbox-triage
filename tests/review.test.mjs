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
const page = vm.createContext({ TextDecoder, atob, Blob, Response, DecompressionStream, Uint8Array, DataView });
vm.runInContext(script + "\n;globalThis.api = { decodePayload, parseReport, feedbackLine, submitText, submitUrl };",
                page);
const { decodePayload, parseReport, feedbackLine, submitText, submitUrl } = page.api;
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
