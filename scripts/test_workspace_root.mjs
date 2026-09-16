import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 940 } });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}?workspaces=1&workspace-shell=1`);
  const root = "/private/tmp/demo-workspace";
  const nav = page.getByRole("navigation", { name: "Workspace-Projekte" });
  await nav.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
  const rootNav = page.locator('[data-worktree-id="root:workspace-demo"]');
  const rootArea = page.getByRole("region", { name: `Arbeitsbereich ${root}`, exact: true });
  await rootNav.getByRole("button", { name: "notes.md", exact: true }).click();
  await rootArea.locator(".cm-content").fill("Root note\n");
  await rootArea.locator(".cm-content").press("Meta+s");
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.workspaceCalls.some(call => call.command === "project_write_file" && call.args.file === "notes.md"));
  await rootNav.getByRole("button", { name: "Resourcen", exact: true }).click();
  await rootNav.getByRole("button", { name: "nested", exact: true }).click();
  await rootNav.getByRole("button", { name: "info.md", exact: true }).click();
  await rootArea.locator(".cm-content").fill("Resource draft\n");
  const rootInspector = page.getByRole("region", { name: `Inspektor ${root}`, exact: true });
  assert.equal(await rootInspector.getByRole("checkbox", { name: /Blame/ }).count(), 0);
  assert.equal(await rootInspector.getByRole("tab", { name: /Historie/ }).count(), 0);

  // A file opened through two roots must retain the stale editor's draft.
  await rootNav.getByRole("button", { name: "api", exact: true }).click();
  await rootNav.getByRole("button", { name: /^shared\.txt/ }).click();
  await rootArea.locator(".cm-content").fill("Root version\n");
  const childNav = page.locator('[data-worktree-id="tree-api"]');
  const childArea = page.getByRole("region", { name: `Arbeitsbereich ${root}/api`, exact: true });
  await childNav.getByRole("button", { name: "shared.txt", exact: true }).click();
  await childArea.locator(".cm-content").fill("Child version\n");
  await childArea.locator(".cm-content").press("Meta+s");
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.workspaceCalls.some(call => call.command === "project_write_file" && call.args.project.endsWith("/api")));
  await rootNav.getByRole("button", { name: /^shared\.txt/ }).click();
  await rootArea.locator(".cm-content").press("Meta+s");
  await rootInspector.getByText(/Datei wurde zwischenzeitlich geändert/).waitFor();
  assert.match(await rootArea.locator(".cm-content").innerText(), /Root version/);
  await rootNav.getByRole("button", { name: /^info\.md/ }).click();
  assert.match(await rootArea.locator(".cm-content").innerText(), /Resource draft/);
  await page.getByRole("button", { name: "Aktualisieren", exact: true }).click();
  assert.match(await rootArea.locator(".cm-content").innerText(), /Resource draft/);
  assert.equal(await nav.getByRole("region", { name: /^Projektgruppe/ }).count(), 3);
  await page.reload();
  await nav.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
  await rootNav.getByRole("button", { name: /Workspace-Ordner/, exact: false }).click();
  await rootArea.getByText(/Resource draft/).waitFor();
  assert.deepEqual(errors, []);
  console.log("PASS root files: plain folders, nested browsing at depth 1, isolated Git, stale-write conflict, retained drafts and reopen");
} finally {
  await browser.close();
}
