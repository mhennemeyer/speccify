// Isolated UI contract test for Spec 009 (session identity and explicit choice).
// Start Vite on 1421; no native project writes, no PTY.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const opens = () => page.evaluate(() => window.__SPECCIFY_MOCK__.terminalOpens);
  const choice = () => page.locator("[data-session-state]");
  const state = async () => choice().getAttribute("data-session-state");

  // Known, existing session → resumed automatically with exactly that id.
  await page.goto(`${url}?session=exact`);
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  let open = (await opens())[0];
  assert.deepEqual(open.session, { mode: "resume", host: "claude", id: "11111111-2222-4333-8444-555555555555" });
  assert.equal(open.autostart, "claude", "the base command stays untouched; the native side appends --resume");
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.sessionChecks), [{ host: "claude", id: "11111111-2222-4333-8444-555555555555" }]);
  console.log("PASS exact: remembered claude session is checked and resumed by id");

  // Session vanished from the host store → visible notice, explicit choice, no automatic start.
  await page.goto(`${url}?session=missing`);
  await page.getByText(/Die gemerkte Sitzung 99999999 wurde im Speicher des Hosts nicht gefunden/).waitFor();
  assert.equal(await state(), "missing");
  assert.equal((await opens()).length, 0, "nothing starts on its own");
  await page.getByRole("button", { name: "Sitzung auswählen", exact: true }).waitFor();
  await page.getByRole("button", { name: "Neueste Sitzung", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  assert.deepEqual((await opens())[0].session, { mode: "latest" });
  console.log("PASS missing: visible notice, explicit choice, latest is a labelled convenience");

  // Legacy marker "1" → unknown identity → picker offered, no automatic start.
  await page.goto(`${url}?session=legacy`);
  await page.getByText(/keine Sitzungs-ID bekannt/).waitFor();
  assert.equal(await state(), "unknown");
  assert.equal((await opens()).length, 0);
  await page.getByRole("button", { name: "Sitzung auswählen", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  assert.deepEqual((await opens())[0].session, { mode: "pick" });
  console.log("PASS legacy: old marker means picker, not --continue");

  // Codex has no chosen id → picker; a new start records host without id.
  await page.goto(`${url}?session=codex`);
  await page.getByText(/codex vergibt beim Start keine wählbare Sitzungs-ID/).waitFor();
  assert.equal((await opens()).length, 0);
  await page.getByRole("button", { name: "Neu starten", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  assert.deepEqual((await opens())[0].session, { mode: "new" });
  assert.equal((await opens())[0].autostart, "codex");
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("speccify.project.agentSession:/private/tmp/claude-501/w1-projekt")));
  assert.equal(stored.host, "codex");
  assert.equal(stored.id, null);
  console.log("PASS codex: no id at start, explicit picker, record without id");

  // Host changed since the session was recorded → notice, no blind append.
  await page.goto(`${url}?session=host`);
  await page.getByText(/Die gemerkte Sitzung gehört zu codex/).waitFor();
  assert.equal(await state(), "host");
  assert.equal((await opens()).length, 0);
  console.log("PASS host: changed host is shown instead of appending a resume flag");

  // Native side rejects the resume → error in the start view, not "resumed".
  await page.goto(`${url}?session=reject`);
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  await page.getByRole("alert").getByText(/nicht gefunden/).waitFor();
  await page.getByRole("button", { name: "Sitzung auswählen", exact: true }).waitFor();
  assert.equal(await page.getByText("Agent-Terminal", { exact: true }).count(), 0, "no running terminal header");
  await page.getByRole("button", { name: "Neu starten", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 2);
  assert.deepEqual((await opens())[1].session, { mode: "new" });
  const fresh = await page.evaluate(() => JSON.parse(localStorage.getItem("speccify.project.agentSession:/private/tmp/claude-501/w1-projekt")));
  assert.equal(fresh.id, "aaaaaaaa-0000-4000-8000-000000000001", "the new identity replaces the stale marker");
  console.log("PASS reject: failed resume is an error with choices; a fresh start records the new id");

  // Fresh project without marker: one button, new session, id recorded.
  await page.goto(url);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: "Agent-Terminal starten", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  assert.deepEqual((await opens())[0].session, { mode: "new" });
  console.log("PASS fresh: no marker means a plain start with a new identity");

  // Dashboard uses the same choice.
  await page.goto(`${url}?dashboard=1&session=missing`);
  await page.getByText(/Die gemerkte Sitzung 99999999/).waitFor();
  assert.equal((await opens()).length, 0);
  console.log("PASS dashboard: same explicit choice in the sidebar");

  assert.deepEqual(errors, []);
  console.log("PASS terminal session: exact resume, visible choice for missing/unknown/host change, failure stays visible");
} finally {
  await browser.close();
}
