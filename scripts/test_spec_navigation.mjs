// Isolated navigation contract; native history and write guards have Rust tests.
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
  await page.goto(`${url}?specnav=1`);
  const nav = page.locator('[data-nav-slot="board"]');
  await nav.locator("[data-spec-file]").first().waitFor();
  assert.equal(await nav.locator("[data-spec-file]").count(), 5);
  assert.equal(await page.getByRole("button", { name: "Archiv", exact: true }).count(), 0);
  const oldFile = ".agent/specs/archive/2026-09-01-notizen-zahlen/SPEC.md";
  const old = nav.locator(`[data-spec-file="${oldFile}"]`);
  await old.focus();
  await page.keyboard.press("Enter");
  assert.equal(await old.getAttribute("aria-current"), "true");
  await page.getByRole("tab", { name: "Historie (1)", exact: true }).click();
  await page.getByText("Eindeutig historische History", { exact: false }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Archivieren", exact: true }).count(), 0);
  assert.equal(await page.getByRole("button", { name: "Bearbeiten", exact: true }).count(), 0);
  await page.getByRole("tab", { name: "Tasks 0/1", exact: true }).click();
  assert.equal(await page.getByRole("checkbox", { name: "Historischer Task", exact: true }).isDisabled(), true);
  assert.equal(await page.locator(`[data-spec-card="${oldFile}"]`).getAttribute("draggable"), "false");
  const activeFile = ".agent/specs/notizen-zahlen/SPEC.md";
  await nav.locator(`[data-spec-file="${activeFile}"]`).click();
  await page.getByRole("tab", { name: "Historie (3)", exact: true }).click();
  assert.equal(await page.getByText("Eindeutig historische History", { exact: false }).count(), 0);
  await page.getByRole("button", { name: "Bearbeiten", exact: true }).waitFor();
  const search = page.getByRole("textbox", { name: "Specs suchen", exact: true });
  await search.fill("Abgenommen");
  assert.equal(await nav.locator("[data-spec-file]").count(), 0); // Search is title/id/path, not station.
  await nav.getByText(/Keine passenden Specs/).waitFor();
  await search.fill("Alte Station");
  await nav.getByRole("button", { name: /Alte Station bleibt lesbar/ }).click();
  await page.getByText("Altbestand", { exact: true }).waitFor();
  await search.fill("12");
  assert.equal(await nav.locator("[data-spec-file]").count(), 2);
  await page.getByRole("button", { name: "Filter zurücksetzen", exact: true }).click();
  await page.getByRole("combobox", { name: "Ober-Spec filtern", exact: true }).selectOption("notizen");
  assert.equal(await nav.locator("[data-spec-file]").count(), 1);
  await page.getByRole("button", { name: "Filter zurücksetzen", exact: true }).click();
  await page.evaluate(() => {
    window.__SPECCIFY_MOCK__.specs[0].title = "Extern aktualisierte Spec";
    window.__SPECCIFY_MOCK__.emit("project-changed", { areas: ["board"] });
  });
  await nav.getByText("Extern aktualisierte Spec", { exact: false }).waitFor();
  await page.getByRole("button", { name: /^Navigator ausblenden/ }).click();
  await page.getByRole("button", { name: /^Inspektor ausblenden/ }).click();
  await search.fill("Alte Station");
  await page.locator('[data-station="Abgenommen"] .spec-card button').click();
  await page.getByText("Altbestand", { exact: true }).waitFor();
  await search.fill("Extern aktualisiert");
  await page.locator(`[data-spec-card="${activeFile}"]`).getByRole("button").click();
  await page.getByRole("tab", { name: "Tasks 2/3", exact: true }).waitFor();
  await page.screenshot({ path: "/private/tmp/speccify-spec-navigation-hidden.png" });
  await page.getByRole("button", { name: /^Navigator einblenden/ }).click();
  await page.getByRole("button", { name: "Filter zurücksetzen", exact: true }).click();
  await page.screenshot({ path: "/private/tmp/speccify-spec-navigation.png" });
  await page.goto(`${url}?empty=1`);
  await page.getByText("Noch keine Spec", { exact: true }).waitFor();
  assert.deepEqual(errors, []);
  console.log("PASS spec navigation: all/legacy/unknown station, path identity, read-only, keyboard, search/reset, parent filter, watcher, hidden panels, empty state");
} finally {
  await browser.close();
}
