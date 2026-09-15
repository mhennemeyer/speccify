import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
const root = "/private/tmp/demo-workspace";
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 940 } });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}?workspaces=1&workspace-shell=1&workspace-registers=1`);
  const register = name => page.locator(`[data-register-project="${root}/${name}"]`);
  const calls = command => page.evaluate(command => window.__SPECCIFY_MOCK__.workspaceCalls.filter(call => call.command === command), command);
  await register("api").locator('[data-register="migratable"]').waitFor();
  await register("web").locator('[data-register="detached"]').waitFor();
  await register("api-search").locator('[data-register="blocked"]').waitFor();
  assert.equal(await register("infra").locator("[data-register]").count(), 0);
  assert.match(await register("api").innerText(), /API[\s\S]*demo-workspace\/api/);
  assert.equal(await register("api-search").getByRole("button").count(), 0);
  await register("api").getByRole("button", { name: "Register einrichten…", exact: true }).click();
  assert.equal((await calls("project_register_setup")).length, 0);
  await register("api").getByRole("button", { name: "Abbrechen", exact: true }).click();
  await register("api").getByRole("button", { name: "Register einrichten…", exact: true }).click();
  await page.evaluate(root => { window.__SPECCIFY_MOCK__.registerSetupError = `${root}/api`; }, root);
  await register("api").getByRole("button", { name: "Jetzt einrichten", exact: true }).click();
  await register("api").getByText("Error: Push fehlgeschlagen", { exact: true }).waitFor();
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.registerSetupError = null; });
  await register("api").getByRole("button", { name: "Jetzt einrichten", exact: true }).click();
  await register("api").locator('[data-register="mounted"]').waitFor();
  assert.ok((await calls("project_register_setup")).every(call => call.args.project === `${root}/api`));
  await register("web").locator('[data-register="detached"]').waitFor();
  await register("web").getByRole("button", { name: "Einhängen", exact: true }).click();
  assert.equal((await calls("project_register_setup")).at(-1).args.project, `${root}/web`);
  await register("web").getByRole("button", { name: "Sync", exact: true }).click();
  assert.equal((await calls("project_register_sync")).at(-1).args.project, `${root}/web`);
  console.log("PASS setup confirmation/cancel/error/retry, mount and sync stay bound to their repository");

  await page.evaluate(root => {
    const project = `${root}/api`;
    const status = window.__SPECCIFY_MOCK__.workspaceRegisters[project];
    Object.assign(status, { rebasing: true, conflicts: [{ file: ".agent/specs/001-shared/SPEC.md", spec_id: "001-shared", team: "station: Done", mine: "station: Doing" }] });
    window.__SPECCIFY_MOCK__.emit("register-changed", { project, status });
  }, root);
  await register("api").getByRole("region", { name: "Register-Konflikte" }).waitFor();
  assert.equal(await register("web").getByRole("region", { name: "Register-Konflikte" }).count(), 0);
  await register("api").getByRole("button", { name: "Team-Fassung übernehmen", exact: true }).click();
  assert.deepEqual((await calls("project_register_resolve")).at(-1).args, {
    project: `${root}/api`, file: ".agent/specs/001-shared/SPEC.md", choice: "team",
  });
  await register("api").locator('[data-register-state="ok"]').waitFor();
  console.log("PASS live conflicts and resolution are scoped to one repository");

  await page.evaluate(root => { window.__SPECCIFY_MOCK__.registerStatusError = `${root}/infra`; }, root);
  await page.getByRole("button", { name: "Aktualisieren", exact: true }).click();
  await register("infra").getByRole("alert").waitFor();
  await page.evaluate(root => {
    window.__SPECCIFY_MOCK__.registerStatusError = null;
    window.__SPECCIFY_MOCK__.workspaceRegisters[`${root}/infra`].mode = "migratable";
  }, root);
  await register("infra").getByRole("button", { name: "Erneut prüfen", exact: true }).click();
  await register("infra").locator('[data-register="migratable"]').waitFor();
  await page.setViewportSize({ width: 1000, height: 700 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: "/private/tmp/speccify-042-workspace.png" });
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.missingTarget = "tree-web"; });
  await page.getByRole("button", { name: "Aktualisieren", exact: true }).click();
  await register("web").waitFor({ state: "detached" });
  await page.evaluate(() => {
    const workspaces = JSON.parse(localStorage.getItem("speccify.test.workspaces"));
    workspaces[0].repositories = workspaces[0].repositories.filter(repo => repo.id !== "repo-api");
    workspaces[0].revision++;
    localStorage.setItem("speccify.test.workspaces", JSON.stringify(workspaces));
  });
  await page.getByRole("button", { name: "Aktualisieren", exact: true }).click();
  await register("api").waitFor({ state: "detached" });
  assert.deepEqual(errors, []);
  console.log("PASS status failures visible and retryable; unavailable and hidden targets have no register actions");
} finally {
  await browser.close();
}
