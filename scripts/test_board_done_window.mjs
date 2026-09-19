// Spec 061: the Done column shows only recent specs open and at most N cards
// at once; older ones collapse. Window and N are board settings
// (`board.doneDays`, `board.doneLimit` in the root's settings).
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
  const limit = lane.getByRole("combobox", { name: "Done-Anzahl" });
  const more = lane.locator(":scope > div > [data-done-more]");
  const inOlder = async (id) => (await older.locator(`[data-spec-card=".agent/specs/${id}/SPEC.md"]`).count()) === 1;
  const settings = () => page.evaluate(() => JSON.stringify(window.__SPECCIFY_MOCK__.projectSettings.board));

  // Defaults 14 days / 10 cards: 11 recent (yesterday, eight recent, undated,
  // fixture Done) → 10 open plus a link-styled "Mehr anzeigen"; three weeks
  // and one year collapse under "Älter"; the header counts all 13.
  await lane.getByRole("heading", { name: /Done \(13\)/ }).waitFor();
  assert.equal(await window_.inputValue(), "14");
  assert.equal(await limit.inputValue(), "10");
  await more.waitFor();
  assert.equal(await more.textContent(), "Mehr anzeigen (1 weitere)");
  assert.equal(await more.evaluate(el => getComputedStyle(el).textDecorationLine), "underline");
  assert.deepEqual(await more.evaluate(el => [getComputedStyle(el).borderTopWidth, getComputedStyle(el).backgroundColor]), ["0px", "rgba(0, 0, 0, 0)"]);
  assert.equal(await cards().count(), 12); // 10 open + 2 collapsed under Älter
  await older.getByText("Älter (2)").waitFor();
  assert.equal(await older.getAttribute("open"), null);
  assert.ok(await inOlder("done-month"));
  assert.ok(await inOlder("done-old"));
  assert.ok(!(await inOlder("done-fresh")));
  assert.ok(!(await inOlder("done-undated")));
  // Newest first within the visible part.
  const visibleIds = await lane.locator("details[open] [data-spec-card], :scope > div > [data-spec-card]").evaluateAll(nodes => nodes.map(n => n.getAttribute("data-spec-card")));
  assert.ok(visibleIds.indexOf(".agent/specs/done-fresh/SPEC.md") < visibleIds.indexOf(".agent/specs/done-recent-1/SPEC.md"), visibleIds.join(","));
  assert.ok(visibleIds.indexOf(".agent/specs/done-recent-1/SPEC.md") < visibleIds.indexOf(".agent/specs/done-recent-8/SPEC.md"), visibleIds.join(","));

  // "Mehr anzeigen" reveals the rest and disappears.
  await more.click();
  await page.waitForFunction(() => document.querySelectorAll('[data-station="Done"] [data-spec-card]').length === 13);
  assert.equal(await more.count(), 0);

  // Collapsed specs stay reachable.
  await older.locator(":scope > summary").click();
  await older.locator('[data-spec-card=".agent/specs/done-old/SPEC.md"]').click();
  await page.getByRole("heading", { name: "Vor einem Jahr fertig" }).first().waitFor();

  // N = 5: five open, link names six more; each click adds five; setting written.
  await limit.selectOption("5");
  await more.waitFor();
  assert.equal(await more.textContent(), "Mehr anzeigen (6 weitere)");
  assert.equal(await settings(), JSON.stringify({ doneLimit: 5 }));
  await more.click();
  assert.equal(await more.textContent(), "Mehr anzeigen (1 weitere)");
  // Back to the default removes the key; "all" shows everything without a link.
  await limit.selectOption("10");
  assert.equal(await settings(), undefined);
  await limit.selectOption("0");
  await page.waitForFunction(() => document.querySelectorAll('[data-station="Done"] [data-done-more]').length === 0);
  assert.equal(await settings(), JSON.stringify({ doneLimit: 0 }));
  await limit.selectOption("10");

  // 30 days: the three-week spec moves up; the setting is written as board.doneDays.
  await window_.selectOption("30");
  await older.getByText("Älter (1)").waitFor();
  assert.ok(!(await inOlder("done-month")));
  assert.equal(await settings(), JSON.stringify({ doneDays: 30 }));
  await window_.selectOption("7");
  await older.getByText("Älter (4)").waitFor(); // recent 7 and 8 are 7.5 and 8.5 days old
  await window_.selectOption("14");
  assert.equal(await settings(), undefined);
  await window_.selectOption("0");
  await page.waitForFunction(() => document.querySelector('[data-station="Done"] [data-done-older]') === null);

  // Saved settings are read on load.
  await page.goto(`${url}?donewindow=1&donedays=90&donelimit=20`);
  await lane.getByRole("heading", { name: /Done \(13\)/ }).waitFor();
  await page.waitForFunction(() => document.querySelector('[data-station="Done"] select')?.value === "90");
  assert.equal(await limit.inputValue(), "20");
  await older.getByText("Älter (1)").waitFor();
  assert.equal(await more.count(), 0);

  // Search shows every match regardless of the window.
  await page.getByRole("textbox", { name: "Specs suchen", exact: true }).fill("Vor einem Jahr");
  await lane.getByRole("heading", { name: /Done \(1\)/ }).waitFor();
  assert.equal(await older.count(), 0);
  assert.equal(await cards().count(), 1);

  // Workspace board: same controls, stored at the workspace root.
  await page.goto(`${url}?dashboard=1&workspaces=1&donewindow=1`);
  await page.getByLabel("Ordner", { exact: true }).fill("/private/tmp/demo-workspace");
  await page.getByRole("button", { name: "Öffnen", exact: true }).click();
  await page.getByRole("button", { name: "Alle Specs", exact: true }).click();
  const wsDone = page.getByRole("region", { name: "Workspace-Spalte Done" });
  const wsWindow = wsDone.getByRole("combobox", { name: "Done-Zeitraum" });
  await wsWindow.waitFor();
  assert.equal(await wsWindow.inputValue(), "14");
  await wsWindow.selectOption("7");
  await wsDone.getByRole("combobox", { name: "Done-Anzahl" }).selectOption("5");
  const calls = await page.evaluate(() => window.__SPECCIFY_MOCK__.ownerCalls.filter(c => c.startsWith("settings:board.")));
  assert.deepEqual(calls, ["settings:board.doneDays=7", "settings:board.doneLimit=5"]);
  assert.deepEqual(errors, []);
  console.log("PASS board done window: defaults 14 days/10 cards, link-styled Mehr anzeigen, collapsed older, sorting, per-board settings, reload, search, all");
} finally {
  await browser.close();
}
