import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 940 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}?workspaces=1&workspace-shell=1`);
  await page.getByRole("button", { name: "Registerquellen…", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Registerquellen bearbeiten" });
  const manifest = {
    version: 1, id: "portable-team", name: "Portable team",
    sources: [{ id: "api-register", name: "Canonical API" }, { id: "web-register", name: "Web" }],
    repositories: [{ id: "api", name: "API" }, { id: "web", name: "Web" }], default_source: "api-register",
  };
  await dialog.getByRole("textbox", { name: "Registermanifest" }).fill(JSON.stringify(manifest, null, 2));
  await dialog.getByRole("combobox", { name: "Schreibziel Canonical API", exact: true }).selectOption("tree-api");
  await dialog.getByRole("combobox", { name: "Schreibziel Web", exact: true }).selectOption("tree-web");
  await dialog.getByRole("checkbox", { name: /API · api-search vergleichen/ }).first().check();
  await dialog.getByRole("button", { name: "Bindung speichern", exact: true }).click();
  await page.getByText("2 gebundene Register · Portable team").waitFor();
  await page.reload();
  await page.getByText("2 gebundene Register · Portable team").waitFor();
  assert.equal(await page.getByRole("combobox", { name: "Kanonisches Register" }).inputValue(), "api-register");
  await page.getByRole("button", { name: "+ Übergreifende Spec", exact: true }).click();
  await page.getByRole("textbox", { name: "Betroffene Code-Repos" }).fill("api@topic, web@topic");
  await page.getByPlaceholder("Titel — was gebaut wird, in einem Satz").fill("Shared task");
  await page.getByRole("button", { name: "Speichern", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.workspaceCalls.some(call => call.command === "project_ticket_create"));
  const calls = await page.evaluate(() => window.__SPECCIFY_MOCK__.workspaceCalls);
  const created = calls.find(call => call.command === "project_ticket_create");
  assert.equal(created.args.project, "/private/tmp/demo-workspace/api");
  assert.equal(created.args.repositories, "api@topic, web@topic");
  assert.deepEqual(errors, []);
  console.log("PASS portable register UI: bind, compare, persist, canonical creation with multi-repo references");
} finally { await browser.close(); }
