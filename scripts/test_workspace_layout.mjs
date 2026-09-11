import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
// Exercise the exact drag handler bundled by the locked native dependency.
const lock = await readFile(new URL("../Cargo.lock", import.meta.url), "utf8");
const version = lock.match(/name = "tauri"\nversion = "([^"]+)"/)[1];
const registry = join(process.env.CARGO_HOME ?? join(homedir(), ".cargo"), "registry", "src");
let dragSource;
for (const index of await readdir(registry)) {
  try { dragSource = await readFile(join(registry, index, `tauri-${version}`, "src/window/scripts/drag.js"), "utf8"); break; }
  catch (error) { if (error.code !== "ENOENT") throw error; }
}
assert.ok(dragSource, "locked Tauri source must be available after cargo build");
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const root = "/private/tmp/demo-workspace";
  const pane = id => page.locator(`[data-worktree-id="tree-${id}"]`);
  const calls = command => page.evaluate(command => window.__SPECCIFY_MOCK__.workspaceCalls.filter(call => call.command === command), command);
  await page.goto(`${base}?workspaces=1&workspace-shell=1&actions=manual`);
  await page.locator("[data-workspace-spec]").first().waitFor();
  const groups = page.getByRole("tablist", { name: "Bereiche", exact: true });
  assert.deepEqual(await groups.getByRole("tab").evaluateAll(nodes => nodes.map(node => node.getAttribute("aria-label"))), ["Dateien", "Orga", "Technik", "Specs", "Hilfe"]);
  const single = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  await single.goto(base);
  await single.locator(".spec-lane").first().waitFor();
  const chrome = async p => ({
    nav: await p.getByRole("tablist", { name: "Bereiche", exact: true }).innerHTML(),
    height: (await p.locator("header").boundingBox()).height,
    splitters: await p.getByRole("separator").count(),
  });
  assert.deepEqual(await chrome(page), await chrome(single), "shared navigation, titlebar height and splitter layout");
  await single.close();

  await page.evaluate(() => {
    const invoke = window.__TAURI_INTERNALS__.invoke;
    window.dragCalls = [];
    window.__TAURI_INTERNALS__.invoke = (cmd, ...args) => {
      if (cmd.startsWith("plugin:window|")) { window.dragCalls.push(cmd); return Promise.resolve(); }
      return invoke(cmd, ...args);
    };
  });
  await page.addScriptTag({ content: dragSource.replace("__TEMPLATE_os_name__", '"macos"') });
  for (const selector of ["header h1", "header p", "header"]) {
    await page.locator(selector).dispatchEvent("mousedown", { button: 0, detail: 1 });
  }
  assert.equal(await page.evaluate(() => window.dragCalls.length), 3, "title, path and background all drag");
  await page.getByRole("button", { name: "Einstellungen", exact: true }).dispatchEvent("mousedown", { button: 0, detail: 1 });
  assert.equal(await page.evaluate(() => window.dragCalls.length), 3, "interactive toolbar controls do not drag");

  const navigator = page.getByRole("navigation", { name: "Workspace-Projekte" });
  const widthBefore = (await navigator.boundingBox()).width;
  const splitter = page.getByRole("separator").first();
  const box = await splitter.boundingBox();
  await page.mouse.move(box.x + 2, box.y + 80);
  await page.mouse.down(); await page.mouse.move(box.x + 52, box.y + 80); await page.mouse.up();
  assert.equal((await navigator.boundingBox()).width, widthBefore + 50);
  await page.keyboard.press("Meta+0"); assert.equal(await navigator.isVisible(), false);
  await page.keyboard.press("Meta+0"); assert.equal(await navigator.isVisible(), true);
  await page.keyboard.press("Meta+1");
  await navigator.getByRole("tablist", { name: "Dateien", exact: true }).getByRole("tab", { name: "Git", exact: true }).waitFor();
  await page.keyboard.press("Meta+4");
  await page.getByRole("region", { name: "Projektgruppe API", exact: true }).getByRole("button", { name: "API", exact: true }).click();
  assert.equal(await pane("api").isVisible(), false);
  await page.getByRole("region", { name: "Projektgruppe API", exact: true }).getByRole("button", { name: "API", exact: true }).click();
  assert.equal(await pane("api").isVisible(), true);

  const terminal = page.getByRole("region", { name: `Terminal ${root}`, exact: true });
  await terminal.getByRole("button", { name: "Agent-Terminal starten", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.workspaceCalls.some(call => call.command === "terminal_open"));
  const terminalId = (await calls("terminal_open"))[0].args.id;
  await page.getByRole("region", { name: "Agent-Terminal", exact: true }).getByTitle("Terminal nach rechts legen", { exact: true }).click();
  await terminal.locator(".xterm").waitFor();
  await page.getByRole("region", { name: "Agent-Terminal", exact: true }).getByTitle("Terminal nach unten legen", { exact: true }).click();
  assert.equal((await calls("terminal_open")).length, 1, "docking does not create a new PTY");
  assert.ok((await calls("terminal_kill")).every(call => call.args.id !== terminalId), "docking keeps the running PTY alive");

  const tests = page.locator("header").getByRole("button", { name: /^Tests —/ });
  await tests.click();
  const apiRun = (await calls("project_action_run")).at(-1).args;
  assert.equal(apiRun.project, `${root}/api`);
  await pane("web").getByRole("button", { name: "Web web", exact: true }).click();
  await tests.click();
  const webRun = (await calls("project_action_run")).at(-1).args;
  assert.equal(webRun.project, `${root}/web`);
  assert.notEqual(apiRun.runId, webRun.runId, "identical commands in different projects have independent runs");
  await page.evaluate(({ apiRun, webRun }) => {
    window.__SPECCIFY_MOCK__.emit("action-output", { run_id: apiRun.runId, line: "only-api-output" });
    window.__SPECCIFY_MOCK__.emit("action-output", { run_id: webRun.runId, line: "only-web-output" });
  }, { apiRun, webRun });
  const output = page.getByLabel("Aktionsausgabe", { exact: true });
  await output.getByText("only-web-output", { exact: true }).waitFor();
  assert.equal(await output.getByText("only-api-output", { exact: true }).isVisible(), false);
  await output.getByRole("button", { name: "Stop", exact: true }).click();
  assert.equal((await calls("project_action_stop")).at(-1).args.runId, webRun.runId);
  await pane("api").getByRole("button", { name: /^API · api api/ }).click();
  await page.getByRole("button", { name: "Ausgabe: Tests", exact: true }).click();
  await output.getByText("only-api-output", { exact: true }).waitFor();
  assert.equal(await output.getByText("only-web-output", { exact: true }).isVisible(), false);
  assert.equal(await page.getByRole("button", { name: "Ausgabe schließen: Tests", exact: true }).isDisabled(), true, "other project's exit cannot end this run");
  await output.getByRole("button", { name: "Stop", exact: true }).click();
  assert.equal((await calls("project_action_stop")).at(-1).args.runId, apiRun.runId);
  await page.getByRole("button", { name: "Inspektor", exact: true }).click();
  await page.screenshot({ path: "/private/tmp/speccify-026-familiar-workspace.png" });
  await page.reload();
  await page.locator("[data-workspace-spec]").first().waitFor();
  assert.equal((await navigator.boundingBox()).width, widthBefore + 50, "layout survives reload");
  assert.deepEqual(errors, []);
  console.log("PASS workspace layout: project chrome parity, actual Tauri drag handler, splitters/shortcuts/groups, stable terminal docking, isolated toolbar action streams and stop, saved layout");
} finally { await browser.close(); }
