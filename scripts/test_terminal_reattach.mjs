// Spec 070: a project window re-attaches to a session that kept running in the
// PTY host — no new PTY, the host's buffer is shown, input reaches the session.
// Runs against the isolated desktop mock (pnpm --filter speccify-desktop dev --port 1421).
import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: process.env.SPECCIFY_TEST_BROWSER ?? "chrome" });
try {
  // 1) A live host session: attach instead of open, buffer visible, no session dialog.
  let page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${base}?live=1&session=missing`);
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__?.terminalAttaches?.length === 1);
  const attach = await page.evaluate(() => window.__SPECCIFY_MOCK__.terminalAttaches[0]);
  assert.equal(attach.id, "term-live-070", "attach uses the host session id");
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.terminalOpens.length), 0, "no new PTY is opened");
  await page.waitForFunction(() => window.__speccifyQa?.terminalText()?.includes("Puffer aus dem PTY-Host"));
  assert.equal(await page.getByText("Sitzung auswählen", { exact: true }).count(), 0, "no session dialog while a live session exists");
  await page.locator(".xterm-helper-textarea").press("x");
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalWrites.some(w => w.id === "term-live-070" && w.data === "x"));
  await page.close();

  // 2) Without a live session the previous behaviour stays: the missing remembered
  //    session is shown for an explicit choice, nothing attaches.
  page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${base}?session=missing`);
  await page.getByText("Sitzung auswählen", { exact: true }).first().waitFor();
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.terminalAttaches.length), 0);
  await page.close();

  // 3) The preference is exposed and round-trips through the mock.
  page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${base}?terminaltest=1`);
  await page.waitForFunction(() => window.__speccifyQa?.terminalReady());
  const persist = page.getByLabel("Terminals überleben App-Neustarts");
  await persist.check();
  await page.waitForFunction(() => JSON.parse(localStorage.getItem("test.terminal-preferences") ?? "{}").persist_sessions === true);
  await persist.uncheck();
  await page.waitForFunction(() => JSON.parse(localStorage.getItem("test.terminal-preferences") ?? "{}").persist_sessions === false);
  assert.deepEqual(errors, []);
  console.log("PASS terminal reattach: live host session attaches with buffer and input, no dialog; without host unchanged; preference round-trips");
} finally { await browser.close(); }
