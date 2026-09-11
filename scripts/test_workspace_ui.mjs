import assert from "node:assert/strict";
import { chromium } from "playwright";
const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  page.setDefaultTimeout(10000);
  page.setDefaultNavigationTimeout(15000);
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}?dashboard=1&workspaces=1`);
  const view = page.getByRole("region", { name: "Workspaces" });
  await view.getByText(/Noch kein Workspace/).waitFor();
  await view.getByLabel("Arbeitsordner", { exact: true }).fill("/private/tmp/demo-workspace");
  await view.getByRole("button", { name: "Workspace erkennen", exact: true }).click();
  await view.getByText("2 Repos/Ordner · 3 Worktrees", { exact: true }).waitFor();
  assert.equal(await view.locator("article[data-project-id]").count(), 2);
  await view.getByRole("checkbox", { name: /API/ }).check();
  await view.getByRole("checkbox", { name: /Web/ }).check();
  await view.getByLabel("Name der Projektgruppe").fill("Customer Portal");
  await view.getByRole("button", { name: "Als Projekt gruppieren", exact: true }).click();
  await view.getByRole("heading", { name: /Customer Portal/ }).waitFor();
  assert.equal(await view.locator("article[data-project-id]").count(), 1);
  const groupedId = await view.locator("article[data-project-id]").getAttribute("data-project-id");
  await view.getByRole("button", { name: "Umbenennen", exact: true }).click();
  await view.getByLabel("Projektname", { exact: true }).fill("Orbit Suite");
  await view.getByRole("button", { name: "Speichern", exact: true }).click();
  await view.getByRole("heading", { name: /Orbit Suite/ }).waitFor();
  for (const theme of ["light", "dark"]) {
    await page.evaluate(theme => document.documentElement.setAttribute("data-theme", theme), theme);
    const colors = await view.locator(".tone-surface").evaluateAll(elements => elements.map(element => {
      const style = getComputedStyle(element); return { foreground: style.color, background: style.backgroundColor };
    }));
    const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(Number).map(value => value / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
    for (const color of colors) {
      const [low, high] = [luminance(color.foreground), luminance(color.background)].sort((a, b) => a - b);
      assert.ok((high + .05) / (low + .05) >= 4.5, `${theme}: workspace accent contrast`);
    }
  }
  await page.reload();
  await view.getByRole("heading", { name: /Orbit Suite/ }).waitFor();
  assert.equal(await view.locator("article[data-project-id]").getAttribute("data-project-id"), groupedId);
  await view.getByRole("button", { name: "Erneut erkennen", exact: true }).click();
  await view.getByRole("button", { name: "Workspace erkennen", exact: true }).waitFor();
  assert.equal(await view.locator("article[data-project-id]").getAttribute("data-project-id"), groupedId);
  await view.getByRole("button", { name: "Worktree öffnen: /private/tmp/demo-workspace/api-search", exact: true }).click();
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.workspaceOpened), [{ workspaceId: "workspace-demo", worktreeId: "tree-feature" }]);
  await page.screenshot({ path: "/private/tmp/speccify-workspace-grouped.png", fullPage: true });
  await view.locator('[data-repository-id="repo-api"]').getByRole("button", { name: "Aus Gruppe lösen", exact: true }).click();
  await view.locator('[data-project-id="project-api"]').waitFor();
  assert.equal(await view.locator("article[data-project-id]").count(), 2);
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.workspaceStale = true; });
  await view.locator('[data-project-id="project-api"]').getByRole("button", { name: "Umbenennen", exact: true }).click();
  await view.getByLabel("Projektname", { exact: true }).fill("Stale name");
  await view.getByRole("button", { name: "Speichern", exact: true }).click();
  await view.getByText(/WORKSPACE_CHANGED/).waitFor();
  assert.equal(await view.getByRole("heading", { name: /Stale name/ }).count(), 0);
  await view.getByLabel("Arbeitsordner", { exact: true }).fill("/private/tmp/partial");
  await view.getByRole("button", { name: "Workspace erkennen", exact: true }).click();
  await view.getByText("Erkennung unvollständig", { exact: true }).waitFor();
  await view.getByLabel("Arbeitsordner", { exact: true }).fill("/missing");
  await view.getByRole("button", { name: "Workspace erkennen", exact: true }).click();
  await view.getByText(/Kein Verzeichnis: missing/).waitFor();
  assert.equal(await view.locator("article[data-project-id]").count(), 2);
  await page.getByText("Einzelprojekt direkt öffnen / zuletzt geöffnet", { exact: true }).click();
  await page.getByRole("button", { name: "/private/tmp/demo-workspace/legacy", exact: true }).click();
  assert.deepEqual((await page.evaluate(() => window.__SPECCIFY_MOCK__.workspaceOpened)).at(-1), { path: "/private/tmp/demo-workspace/legacy" });
  await page.setViewportSize({ width: 1000, height: 800 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "workspace overflow");
  await view.evaluate(element => { element.style.width = "320px"; });
  const treeDetails = view.locator('[data-repository-id="repo-api"] p[title]').first().locator("..");
  assert.ok((await treeDetails.boundingBox()).width >= 160, "worktree context remains readable beside the terminal");
  assert.ok(await view.evaluate(element => element.scrollWidth <= element.clientWidth), "narrow workspace overflow");
  assert.deepEqual(errors, []);
  console.log("PASS workspace UI: discovery, grouping, rename, light/dark contrast, reload/rescan identity, explicit worktree, ungroup, stale edits, partial/error states, legacy projects");
} finally { await browser.close(); }
