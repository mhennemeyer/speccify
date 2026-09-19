// Spec 061: the Done column shows only recent specs open; older ones collapse.
// The window is a board setting (`board.doneDays` in the root's settings).
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
  await page.goto(`${url}?donewindow=1`);
  const lane = page.locator('[data-station="Done"]');
  await lane.waitFor();
  const cards = () => lane.locator("[data-spec-card]");
  const older = lane.locator("[data-done-older]");
  const window_ = lane.getByRole("combobox", { name: "Done-Zeitraum" });
  const inOlder = async (id) => (await older.locator(`[data-spec-card=".agent/specs/${id}/SPEC.md"]`).count()) === 1;

  // Default 14 days: yesterday, undated and the fixture's Done spec stay open;
  // three weeks and one year collapse under "Älter"; the header counts all.
  await lane.getByRole("heading", { name: /Done \(5\)/ }).waitFor();
  assert.equal(await window_.inputValue(), "14");
  assert.equal(await cards().count(), 5);
  await older.getByText("Älter (2)").waitFor();
  assert.equal(await older.getAttribute("open"), null);
  assert.ok(await inOlder("done-month"));
  assert.ok(await inOlder("done-old"));
  assert.ok(!(await inOlder("done-fresh")));
  assert.ok(!(await inOlder("done-undated")));
  // Newest first within the visible part.
  const visibleIds = await lane.locator("details[open] [data-spec-card], :scope > div > [data-spec-card]").evaluateAll(nodes => nodes.map(n => n.getAttribute("data-spec-card")));
  assert.ok(visibleIds.indexOf(".agent/specs/done-fresh/SPEC.md") < visibleIds.indexOf(".agent/specs/notizen-ordner/SPEC.md"), visibleIds.join(","));

  // Collapsed specs stay reachable.
  await older.locator(":scope > summary").click();
  await older.locator('[data-spec-card=".agent/specs/done-old/SPEC.md"]').click();
  await page.getByRole("heading", { name: "Vor einem Jahr fertig" }).first().waitFor();

  // 30 days: the three-week spec moves up; the setting is written as board.doneDays.
  await window_.selectOption("30");
  await older.getByText("Älter (1)").waitFor();
  assert.ok(!(await inOlder("done-month")));
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.projectSettings.board), { doneDays: 30 });
  // 7 days keeps yesterday open; back to the default removes the key.
  await window_.selectOption("7");
  await older.getByText("Älter (2)").waitFor();
  await window_.selectOption("14");
  assert.equal(await page.evaluate(() => JSON.stringify(window.__SPECCIFY_MOCK__.projectSettings.board)), undefined);
  // "All" restores the old behaviour.
  await window_.selectOption("0");
  await page.waitForFunction(() => document.querySelector('[data-station="Done"] [data-done-older]') === null);

  // A saved setting is read on load.
  await page.goto(`${url}?donewindow=1&donedays=90`);
  await lane.getByRole("heading", { name: /Done \(5\)/ }).waitFor();
  await page.waitForFunction(() => document.querySelector('[data-station="Done"] select')?.value === "90");
  await older.getByText("Älter (1)").waitFor();

  // Search shows every match regardless of the window.
  await page.getByRole("textbox", { name: "Specs suchen", exact: true }).fill("Vor einem Jahr");
  await lane.getByRole("heading", { name: /Done \(1\)/ }).waitFor();
  assert.equal(await older.count(), 0);
  assert.equal(await cards().count(), 1);

  // Workspace board: same control, stored at the workspace root.
  await page.goto(`${url}?dashboard=1&workspaces=1&donewindow=1`);
  await page.getByLabel("Ordner", { exact: true }).fill("/private/tmp/demo-workspace");
  await page.getByRole("button", { name: "Öffnen", exact: true }).click();
  await page.getByRole("button", { name: "Alle Specs", exact: true }).click();
  const wsDone = page.getByRole("region", { name: "Workspace-Spalte Done" });
  const wsWindow = wsDone.getByRole("combobox", { name: "Done-Zeitraum" });
  await wsWindow.waitFor();
  assert.equal(await wsWindow.inputValue(), "14");
  await wsWindow.selectOption("7");
  const calls = await page.evaluate(() => window.__SPECCIFY_MOCK__.ownerCalls.filter(c => c.startsWith("settings:board.doneDays")));
  assert.deepEqual(calls, ["settings:board.doneDays=7"]);
  assert.deepEqual(errors, []);
  console.log("PASS board done window: default 14 days, collapsed older, sorting, per-board setting, reload, search, all");
} finally {
  await browser.close();
}
