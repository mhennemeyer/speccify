// Isolated UI contract test for Spec 030 (team signals over Git).
// Start Vite on 1421; no native Git, no network.
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
  const calls = () => page.evaluate(() => window.__SPECCIFY_MOCK__.ownerCalls);

  // Foreign register commits mark the card until confirmed; own changes never do.
  await page.goto(`${url}?changes=1&owner=me`);
  await page.evaluate(() => localStorage.removeItem("speccify.register.seen:/private/tmp/claude-501/w1-projekt"));
  await page.reload();
  const mark = page.locator("[data-spec-new]").first();
  await mark.waitFor();
  assert.match(await mark.innerText(), /neu · 2 von Ben Kollege/);
  assert.match(await mark.getAttribute("title"), /Task 2/);
  await mark.click();
  await page.locator("[data-spec-new]").waitFor({ state: "detached" });
  await page.reload();
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  assert.equal(await page.locator("[data-spec-new]").count(), 0, "confirmation survives a reload");
  // A live register event reloads the change list.
  await page.evaluate(() => { localStorage.removeItem("speccify.register.seen:/private/tmp/claude-501/w1-projekt"); });
  await page.reload();
  await page.locator("[data-spec-new]").first().waitFor();
  console.log("PASS changes: foreign commits marked with authors and subjects, click confirms, own commits ignored");

  // Questions addressed to me are highlighted and counted; others' questions are not.
  await page.goto(`${url}?owner=me&question=me`);
  await page.getByText("Frage an Dich", { exact: true }).waitFor();
  await page.locator("[data-questions-for-me='1']").waitFor();
  await page.getByRole("button", { name: "braucht mich", exact: true }).click();
  assert.equal(await page.locator("[data-spec-card]").count(), 1);
  await page.goto(`${url}?owner=me&question=other`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  assert.equal(await page.getByText("Frage an Dich", { exact: true }).count(), 0, "not my email, no highlight");
  await page.goto(`${url}?owner=me`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  assert.equal(await page.getByText("Frage an Dich", { exact: true }).count(), 0, "question without addressee");
  console.log("PASS questions: an: <email> highlights only the addressee");

  // Webhook is a per-project setting with a test message; nothing is sent by default.
  await page.goto(`${url}?owner=me`);
  await page.getByRole("button", { name: "Einstellungen", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Einstellungen" });
  const toggle = dialog.getByRole("checkbox", { name: /Webhook für dieses Projekt/ });
  assert.equal(await toggle.isChecked(), false);
  await toggle.check();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.ownerCalls.includes("settings:webhook.enabled=true"));
  await dialog.getByRole("button", { name: "Testnachricht senden", exact: true }).click();
  await dialog.getByText(/Testnachricht gesendet an https:\/\/hooks\.example\.invalid/).waitFor();
  assert.ok((await calls()).includes("webhook-test"));
  console.log("PASS webhook: explicit per-project switch and test message");

  assert.deepEqual(errors, []);
  console.log("PASS team signals: new-since-sync marks, questions to a person, outgoing webhook only when enabled");
} finally {
  await browser.close();
}
