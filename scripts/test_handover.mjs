// Isolated UI contract test for Spec 011 (one confirmed handover to the agent).
// Start Vite on 1421; the mock records terminal writes.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
const ESC = String.fromCharCode(27);
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const writes = () => page.evaluate(() => window.__SPECCIFY_MOCK__.terminalWrites);

  await page.goto(`${url}?owner=me`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  const card = page.locator('[data-station="Doing"] [data-spec-card]').first();
  const file = await card.getAttribute("data-spec-card");
  await card.locator("button").first().click();
  await page.getByRole("button", { name: "Auftrag…", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Auftrag" });
  const text = dialog.getByLabel("Auftragstext");
  await text.waitFor();
  let preview = await text.inputValue();
  assert.match(preview, /^Projekt: \/private\/tmp\/claude-501\/w1-projekt\n/);
  assert.match(preview, new RegExp(`Spec .* \\(Station Doing\\) — Datei: ${file.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`));
  assert.match(preview, /Auftrag: Arbeite diese Spec nach dem Spec-Workflow/);
  assert.match(preview, /Regeln: `\.agent\/agent\.md`/);
  assert.match(preview, /```md\n/);
  assert.equal(await dialog.locator("[data-terminal-ready]").getAttribute("data-terminal-ready"), "false");
  console.log("PASS preview: project, spec id, station, path, intent and rules from the current file");

  // No terminal: nothing is typed, the sheet says so and offers copy/start.
  await dialog.getByRole("button", { name: "Ins Terminal einfügen", exact: true }).click();
  await dialog.getByRole("status").filter({ hasText: /Kein Agent-Terminal bereit/ }).waitFor();
  assert.deepEqual(await writes(), []);
  // Spec 039: der QA-Haken liest die Terminal-Bereitschaft und den Puffer.
  assert.equal(await page.evaluate(() => window.__speccifyQa.terminalReady()), false);
  assert.equal(await page.evaluate(() => window.__speccifyQa.terminalText()), null);
  await dialog.getByRole("button", { name: "Terminal starten", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.terminalOpens.length === 1);
  await page.waitForFunction(() => window.__speccifyQa.terminalReady());
  assert.equal(typeof await page.evaluate(() => window.__speccifyQa.terminalText()), "string");
  console.log("PASS qa hooks: terminalReady and terminalText follow the terminal");
  await page.waitForFunction(() => document.querySelector("[data-terminal-ready]")?.getAttribute("data-terminal-ready") === "true");
  console.log("PASS no terminal: visible refusal, explicit start");

  // Review intent changes the order; delivery is one bracketed paste without Enter.
  await dialog.getByRole("button", { name: "Prüfen", exact: true }).click();
  preview = await text.inputValue();
  assert.match(preview, /Auftrag: Prüfe diese Spec gegen ihre Acceptance-Punkte/);
  await dialog.getByRole("button", { name: "Ins Terminal einfügen", exact: true }).click();
  await dialog.getByRole("status").filter({ hasText: /Eingefügt — im Terminal mit Enter absenden/ }).waitFor();
  const sent = await writes();
  assert.equal(sent.length, 1);
  assert.ok(sent[0].data.startsWith(`${ESC}[200~Projekt:`), "bracketed paste start");
  assert.ok(sent[0].data.endsWith(`${ESC}[201~`), "bracketed paste end, no trailing newline");
  assert.ok(!sent[0].data.includes("\r"), "Enter stays with the human");
  assert.ok(sent[0].data.includes("Prüfe diese Spec"));
  console.log("PASS delivery: single paste block, confirmed, no auto-submit");

  // The file changed after selection: the sheet reads the current content and says so.
  await dialog.getByRole("button", { name: "Schließen", exact: true }).click();
  await page.evaluate((f) => { const spec = window.__SPECCIFY_MOCK__.specs.find(s => s.file === f); spec.body += "\n\nNachträglich geändert."; }, file);
  await page.getByRole("button", { name: "Auftrag…", exact: true }).click();
  await dialog.getByRole("status").filter({ hasText: /seit der Auswahl geändert/ }).waitFor();
  assert.match(await text.inputValue(), /Nachträglich geändert/);
  console.log("PASS staleness: current file wins and the change is visible");

  // Board moves and selection never type anything.
  await dialog.getByRole("button", { name: "Schließen", exact: true }).click();
  const before = (await writes()).length;
  await page.locator('[data-station="Done"] [data-spec-card]').first().locator("button").first().click();
  await page.waitForTimeout(300);
  assert.equal((await writes()).length, before, "selection alone sends nothing");
  console.log("PASS no auto-orders: selection and board changes stay silent");

  assert.deepEqual(errors, []);
  console.log("PASS handover: one preview for specs, confirmed delivery, refusal without terminal, staleness, no auto-submit");
} finally {
  await browser.close();
}
