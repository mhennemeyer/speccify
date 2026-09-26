// Spec 073: the UI language follows the setting, switches at once and is
// persisted through save_settings. Runs against the isolated desktop mock
// (pnpm --filter speccify-desktop dev --port 1421).
import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: process.env.SPECCIFY_TEST_BROWSER ?? "chrome" });
try {
  const errors = [];
  // 1) Setting "en": English labels, <html lang="en">.
  let page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${base}?lang=en`);
  await page.locator("[data-spec-card]").first().waitFor();
  await page.waitForFunction(() => document.documentElement.lang === "en");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Settings" });
  await dialog.waitFor();
  assert.equal(await dialog.getByRole("heading", { name: "Language" }).count(), 1, "settings sheet shows the Language section in English");
  // 2) Switch to German in the sheet: labels change without reload, setting saved.
  await dialog.getByRole("radio", { name: "Deutsch" }).click();
  await page.waitForFunction(() => document.documentElement.lang === "de");
  await page.getByRole("dialog", { name: "Einstellungen" }).getByRole("heading", { name: "Sprache" }).waitFor();
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("speccify.test.settings") ?? "{}").language);
  assert.equal(saved, "de", "language is persisted through save_settings");
  // 3) Back to English through the same control; unknown entries fall back to German, never a key.
  await page.getByRole("dialog", { name: "Einstellungen" }).getByRole("radio", { name: "English" }).click();
  await page.waitForFunction(() => document.documentElement.lang === "en");
  await page.getByRole("dialog", { name: "Settings" }).waitFor();
  assert.equal(await page.getByText(/^\{t\(|undefined$/).count(), 0, "no raw keys or undefined in the UI");
  await page.close();
  // 4) Default from the mock (de) keeps every existing suite German.
  page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(base);
  await page.locator("[data-spec-card]").first().waitFor();
  await page.waitForFunction(() => document.documentElement.lang === "de");
  assert.equal(await page.getByRole("button", { name: "Einstellungen", exact: true }).count(), 1);
  assert.deepEqual(errors, []);
  console.log("PASS language: en from settings, live switch to de and back, persisted, mock default de");
} finally { await browser.close(); }
