import assert from "node:assert/strict";
import { chromium } from "playwright";
const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}?dashboard=1&workspaces=1`);
  await page.getByLabel("Ordner", { exact: true }).fill("/private/tmp/demo-workspace");
  await page.getByRole("button", { name: "Öffnen", exact: true }).click();
  await page.getByRole("button", { name: "Alle Specs", exact: true }).click();
  const view = page.getByRole("region", { name: "Workspace-Specs", exact: true });
  const cards = view.locator("[data-workspace-spec]");
  await cards.first().waitFor();
  assert.equal(await cards.count(), 3);
  const keys = await cards.evaluateAll(elements => elements.map(element => element.dataset.workspaceSpec));
  assert.equal(new Set(keys).size, 3);
  assert.equal(await view.getByLabel("Workspace-Spec-Liste", { exact: true }).getByRole("button").count(), 3);
  await view.getByLabel("Board-Projekt").selectOption("project-api");
  assert.equal(await cards.count(), 2);
  await view.getByLabel("Workspace-Specs suchen").fill("api-search");
  assert.equal(await cards.count(), 1);
  await cards.first().click();
  const preview = view.getByRole("article", { name: "Workspace-Spec-Vorschau" });
  await preview.getByText("Only api-search.", { exact: true }).waitFor();
  await preview.getByRole("button", { name: /Projektfenster öffnen/ }).click();
  // Spec 027: „Ordner öffnen“ hat zuerst das Arbeitsfenster geöffnet, dann folgt das gezielte Projektfenster.
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.workspaceOpened), [
    { workspaceId: "workspace-demo", window: true },
    { workspaceId: "workspace-demo", worktreeId: "tree-feature" },
  ]);
  assert.ok(await view.getByRole("checkbox").evaluateAll(elements => elements.every(element => element.disabled)), "preview tasks cannot be edited");
  await view.getByLabel("Workspace-Specs suchen").fill("");
  await view.getByLabel("Board-Projekt").selectOption("");
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.boardUnknown = true; window.__SPECCIFY_MOCK__.boardPartial = true; });
  await view.getByRole("button", { name: "Board aktualisieren" }).click();
  await view.getByText("Board unvollständig", { exact: true }).waitFor();
  await view.getByLabel("Workspace-Spalte Review", { exact: true }).waitFor();
  await preview.getByText("Only api-search.", { exact: true }).waitFor();
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.boardError = true; });
  await view.getByRole("button", { name: "Board aktualisieren" }).click();
  await view.getByText(/möglicherweise veraltet/).waitFor();
  assert.equal(await cards.count(), 3);
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.boardError = false; });
  await view.getByRole("button", { name: "Board aktualisieren" }).click();
  await view.getByRole("button", { name: "Board aktualisieren" }).isEnabled();
  await page.screenshot({ path: "/private/tmp/speccify-workspace-board.png", fullPage: true });
  for (const theme of ["light", "dark"]) {
    await page.evaluate(theme => document.documentElement.setAttribute("data-theme", theme), theme);
    await page.setViewportSize({ width: 1000, height: 800 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${theme}: viewport overflow`);
    await view.evaluate(element => { element.style.width = "320px"; });
    assert.ok(await view.evaluate(element => element.scrollWidth <= element.clientWidth), `${theme}: narrow board overflow`);
    await view.evaluate(element => { element.style.width = ""; });
  }
  // A pending old snapshot must never appear under a newly selected workspace.
  await page.evaluate(() => {
    const entries = JSON.parse(localStorage.getItem("speccify.test.workspaces"));
    entries.push({ ...structuredClone(entries[0]), id: "workspace-empty", name: "Empty", projects: [], repositories: [] });
    localStorage.setItem("speccify.test.workspaces", JSON.stringify(entries));
  });
  await page.reload();
  await page.getByRole("button", { name: "Alle Specs", exact: true }).click();
  await cards.first().waitFor();
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.boardDelay = 300; });
  await view.getByRole("button", { name: "Board aktualisieren" }).click();
  await page.getByLabel("Gespeicherter Workspace").selectOption("workspace-empty");
  await view.getByText(/Keine Specs für diese Auswahl/).waitFor();
  assert.equal(await cards.count(), 0);
  assert.equal(await view.getByRole("article").count(), 0);
  assert.deepEqual(errors, []);
  console.log("PASS workspace board: collisions, filters/list, preview, exact worktree, read-only, refresh, partial/error, unknown station, narrow themes and stale workspace response");
} finally { await browser.close(); }
