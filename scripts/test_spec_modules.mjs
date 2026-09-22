// Spec 063: modules per spec. Cards show the modules a spec touches and warn
// when another spec in Doing names the same module; the inspector lists the
// overlap and marks modules missing from the project catalogue; the catalogue
// (`modules` in the root's settings) is edited from the board header.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${url}?modules=1`);
  const card = (id) => page.locator(`[data-spec-card=".agent/specs/${id}/SPEC.md"]`);
  await card("notizen-zahlen").waitFor();

  // Doing #12 (terminal, board) and Doing live-test (terminal) collide on terminal.
  const twelve = card("notizen-zahlen");
  assert.equal(await twelve.getAttribute("data-spec-modules"), null); // attribute sits on the chip row
  assert.equal(await twelve.locator("[data-spec-modules]").getAttribute("data-spec-modules"), "terminal,board");
  assert.equal((await twelve.locator('[data-module-overlap="terminal"]').textContent()).trim(), "⚠ terminal · auch live-test");
  assert.equal(await twelve.locator('[data-module-overlap="board"]').count(), 0); // board: nobody else in Doing
  assert.equal((await card("live-test").locator('[data-module-overlap="terminal"]').textContent()).trim(), "⚠ terminal · auch #12");

  // Backlog #14 (updates, board): warned about board before Backlog → Doing; updates is quiet.
  const plan = card("module-plan");
  assert.equal((await plan.locator('[data-module-overlap="board"]').textContent()).trim(), "⚠ board · auch #12");
  assert.equal(await plan.locator('[data-module-overlap="updates"]').count(), 0);
  assert.equal(await plan.locator("[data-spec-modules] span").count(), 2);

  // Done never warns and never causes a warning.
  assert.equal(await card("module-done").locator("[data-module-overlap]").count(), 0);

  // Inspector: per-module catalogue state and overlap.
  await plan.getByRole("button", { name: /Updater-Dialog/ }).click();
  const modules = page.getByRole("region", { name: "Module" });
  await modules.waitFor();
  await modules.locator('[data-module-row="updates"]').getByText("nicht im Katalog").waitFor();
  await modules.locator('[data-module-row="board"]').getByText("auch in Doing: #12 notes/zahlen.md mit Quadratzahlen 1–5 anlegen").waitFor();
  assert.equal(await modules.locator('[data-module-row="board"]').getByText("Specs-Board und Inspektor").count(), 1);

  // Editor sheet carries the field, prefilled from the front matter.
  await page.getByRole("button", { name: "Bearbeiten", exact: true }).click();
  // An input with a datalist is a combobox to the accessibility tree.
  const field = page.getByRole("combobox", { name: "Module", exact: true });
  await field.waitFor();
  assert.equal(await field.inputValue(), "updates, board");
  await page.getByRole("button", { name: "Abbrechen" }).click();

  // Catalogue: two entries, the header says so; the sheet suggests the module
  // specs already name; saving writes `modules` into the settings.
  const button = page.locator("[data-modules-button]");
  assert.equal((await button.textContent()).trim(), "Module (2)");
  await button.click();
  const sheet = page.locator("[data-modules-sheet]");
  await sheet.waitFor();
  assert.equal(await sheet.locator("[data-module-entry]").count(), 2);
  await sheet.locator('[data-module-suggest="updates"]').click();
  assert.equal(await sheet.locator("[data-module-entry]").count(), 3);
  await sheet.locator("[data-module-entry]").nth(2).getByRole("textbox", { name: "Beschreibung" }).fill("Updater und Manifest");
  await sheet.getByRole("button", { name: "Speichern" }).click();
  await sheet.waitFor({ state: "hidden" });
  const saved = await page.evaluate(() => JSON.stringify(window.__SPECCIFY_MOCK__.projectSettings.modules));
  assert.equal(saved, JSON.stringify([
    { name: "terminal", description: "PTY, Agent-Start, Sitzungen", paths: ["src-tauri/src/terminal.rs"] },
    { name: "board", description: "Specs-Board und Inspektor" },
    { name: "updates", description: "Updater und Manifest" },
  ]));
  await page.locator("[data-modules-button]").getByText("Module (3)").waitFor();
  await modules.locator('[data-module-row="updates"]').getByText("Updater und Manifest").waitFor();
  assert.equal(await modules.locator('[data-module-row="updates"]').getByText("nicht im Katalog").count(), 0);

  // A rejected name never reaches the settings.
  await page.locator("[data-modules-button]").click();
  await sheet.locator("[data-module-entry]").nth(0).getByRole("textbox", { name: "Modulname" }).fill("Term inal");
  await sheet.getByRole("button", { name: "Speichern" }).click();
  await sheet.getByRole("alert").waitFor();
  await sheet.getByRole("button", { name: "Abbrechen" }).click();

  // Without a catalogue the header button and the inspector say so.
  await page.goto(`${url}?modules=nocatalog`);
  await card("module-plan").waitFor();
  assert.equal((await page.locator("[data-modules-button]").textContent()).trim(), "Module…");
  await card("module-plan").getByRole("button", { name: /Updater-Dialog/ }).click();
  await page.getByRole("region", { name: "Module" }).getByText("Kein Modulkatalog im Projekt").waitFor();
  // Unknown-module marks need a catalogue to compare against.
  assert.equal(await page.getByRole("region", { name: "Module" }).getByText("nicht im Katalog").count(), 0);

  assert.deepEqual(errors, []);
  console.log("test_spec_modules: ok");
} finally {
  await browser.close();
}
