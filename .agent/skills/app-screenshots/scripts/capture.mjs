import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const output = new URL("../../../../apps/marketing/src/assets/landing/", import.meta.url);
assert.equal(process.platform, "darwin", "Published screenshots must be captured on macOS.");
const desktop = fileURLToPath(new URL("../../../../apps/desktop/", import.meta.url));
const vite = fileURLToPath(new URL("../../../../apps/desktop/node_modules/vite/bin/vite.js", import.meta.url));
const server = spawn(process.execPath, [vite, "--host", "127.0.0.1", "--port", "0"], {
  cwd: desktop, stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, NO_COLOR: "1" },
});
let browser;
try {
  const address = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error("Vite did not announce its loopback URL")), 15000);
    let log = "";
    const fail = error => { clearTimeout(timer); reject(error); };
    server.once("error", fail);
    server.once("exit", code => fail(Error(`Vite exited (${code}): ${log}`)));
    for (const stream of [server.stdout, server.stderr]) stream.on("data", data => {
      log += data.toString();
      const match = log.match(/http:\/\/127\.0\.0\.1:\d+\//);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
  });
  browser = await chromium.launch({ channel: process.env.SCREENSHOT_BROWSER === "chromium" ? undefined : "chrome" });
  const context = await browser.newContext({ viewport: { width: 1344, height: 840 }, deviceScaleFactor: 2,
    colorScheme: "dark", locale: "en-US", timezoneId: "Europe/Berlin", reducedMotion: "reduce" });
  const errors = [];
  await context.route("**/*", route => {
    const target = new URL(route.request().url());
    if (target.origin === new URL(address).origin) return route.continue();
    errors.push(`External request: ${target.origin}`);
    return route.abort();
  });
  const project = "/Users/demo/Projects/OrbitNotes";
  await context.addInitScript(project => {
    localStorage.setItem(`speccify.project.layout:${project}`, JSON.stringify({
      navWidth: 240, navShown: true, rightWidth: 320, rightShown: true, rightTab: "inspector",
      bottomHeight: 210, bottomShown: true, terminalDock: "bottom", resumeAgent: false,
    }));
    localStorage.setItem("speccify.theme", "dark");
  }, project);
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.setDefaultNavigationTimeout(15000);
  await page.clock.setFixedTime(new Date("2026-09-01T10:00:00Z"));
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${address}dev/mock.html?marketing=1`);
  await page.locator('.spec-card').first().waitFor();
  assert.equal(await page.locator('.spec-card').count(), 6);
  await page.locator('[data-spec-card=".agent/specs/005-suche/SPEC.md"] button').click();
  await page.getByRole("tab", { name: "Tasks 2/3", exact: true }).click();
  await page.getByRole("button", { name: "Agent-Terminal starten", exact: true }).click();
  await page.waitForFunction(() => !!window.__SPECCIFY_MOCK__.marketingTerminal);
  await page.evaluate(() => window.__SPECCIFY_MOCK__.marketingTerminalOutput());
  await page.locator('[title="Aktivität — Klick für die Liste"] .animate-spin').waitFor({ state: "hidden" });
  // Wait for fonts and xterm layout; no fake UI styling or DOM text replacement.
  await page.evaluate(async () => { await document.fonts.ready; await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
  await page.mouse.move(0, 839);
  await page.locator("button:focus").evaluateAll(buttons => buttons.forEach(button => button.blur()));
  const visibleText = await page.locator("body").innerText();
  for (const privateFragment of ["mhennemeyer", "w1-projekt", "claude-501", "Beweisticket", "Conversation"]) {
    assert.ok(!visibleText.includes(privateFragment), `Private/stale fixture fragment: ${privateFragment}`);
  }
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
  const captures = new Map();
  const capture = async (name, target = page) => {
    await page.locator("input:focus, textarea:focus, button:focus").evaluateAll(elements => elements.forEach(el => el.blur()));
    await page.mouse.move(0, 839);
    await page.evaluate(async () => { await document.fonts.ready; await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
    const text = await page.locator("body").innerText();
    for (const fragment of ["mhennemeyer", "w1-projekt", "claude-501", "Beweisticket", "/Users/me/", "(leer)"]) {
      assert.ok(!text.includes(fragment), `${name}: private or incomplete fixture: ${fragment}`);
    }
    captures.set(name, await target.screenshot({ animations: "disabled" }));
  };
  await capture("board");
  await page.keyboard.press("Meta+Shift+Y");
  const group = name => page.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name, exact: true }).click();
  await group("Orga");
  await page.getByRole("tab", { name: "Skills", exact: true }).click();
  await page.locator('[data-nav-slot="skills"]').getByRole("button", { name: /markdown-export/ }).click();
  await page.getByRole("heading", { name: "Reliable Markdown export", exact: true }).waitFor();
  await capture("skills");
  await page.getByRole("tab", { name: "Playbooks", exact: true }).click();
  await page.getByRole("button", { name: /Product direction Vision/ }).click();
  await page.getByRole("heading", { name: "A quieter place for your notes", exact: true }).waitFor();
  await capture("playbooks");
  await group("Technik");
  await page.getByRole("tab", { name: "Tools", exact: true }).click();
  await page.locator('[data-nav-slot="tools"]').getByRole("button", { name: /validate-note/ }).click();
  await page.getByRole("heading", { name: "Examples", exact: true }).waitFor();
  await capture("tools");
  await page.getByRole("tab", { name: "MCPs", exact: true }).click();
  await page.locator('[data-nav-slot="mcps"]').getByRole("button", { name: /speccify-exec/ }).click();
  await page.locator('[data-slot="mcps"]').getByText(".codex/config.toml", { exact: true }).waitFor();
  await capture("mcps");
  await page.getByRole("tab", { name: "Aktionen", exact: true }).click();
  await page.locator('[data-action="pnpm bench:search"]').getByRole("button", { name: "Ausführen", exact: true }).click();
  await page.getByLabel("Aktionsausgabe", { exact: true }).locator("svg").waitFor();
  await page.getByText("exit 0 · 1s", { exact: true }).waitFor();
  await capture("actions");
  await page.getByRole("button", { name: "Inspektor", exact: true }).click();
  await page.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
  await page.getByRole("tablist", { name: "Dateien", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
  await page.locator('[data-nav-slot="files"]').getByText("src", { exact: true }).click();
  await page.locator('[data-nav-slot="files"]').getByText("search", { exact: true }).click();
  await page.locator('[data-nav-slot="files"]').getByText("index.ts", { exact: true }).click();
  await page.locator(".cm-content").filter({ hasText: "export interface Note" }).waitFor();
  await capture("files");
  await page.getByRole("tab", { name: "Git", exact: true }).click();
  await page.getByRole("textbox", { name: "Commit-Betreff", exact: true }).fill("feat: search note titles and content");
  await page.getByRole("textbox", { name: "Beschreibung (optional)", exact: true }).fill("Local search with a preview. Keyboard review follows in Spec 005.");
  await page.getByRole("button", { name: /2 gestagete Datei/ }).waitFor();
  await page.locator("input:focus, textarea:focus").evaluateAll(elements => elements.forEach(el => el.blur()));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await capture("git", page.getByRole("region", { name: "Git-Arbeitsbereich", exact: true }));
  assert.deepEqual(errors, []);
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.gitCalls), []);
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.actionStarts), ["pnpm bench:search"]);
  // Workspace window (Specs 015/024/026): the public OrbitNotes demo workspace with
  // three repositories in two project groups and one shared board. No terminal is
  // started; the parent agent stays an explicit click.
  await page.goto(`${address}dev/mock.html?marketing=1&workspaces=1&workspace-shell=1`);
  const cards = page.locator("[data-workspace-spec]");
  await cards.first().waitFor();
  assert.equal(await cards.count(), 9, "six OrbitNotes specs, two sync specs, one website spec");
  await cards.filter({ hasText: "Find the note you need" }).first().click();
  await page.getByRole("region", { name: `Inspektor ${project}`, exact: true }).getByRole("tab", { name: "Tasks 2/3", exact: true }).click();
  await page.keyboard.press("Meta+Shift+Y");
  await page.getByRole("region", { name: "Agent-Terminal", exact: true }).waitFor({ state: "hidden" });
  assert.equal(await page.getByRole("region", { name: `Terminal /Users/demo/Projects`, exact: true }).count(), 0, "workspace opens no terminal by itself");
  await capture("workspace");
  assert.deepEqual(errors, []);
  await mkdir(output, { recursive: true });
  for (const [name, buffer] of captures) await writeFile(new URL(`${name}.png`, output), buffer);
  console.log(`PASS: ${[...captures.keys()].join(", ")} captured in ${fileURLToPath(output)} (real UI, isolated demo, no native mutations)`);
} finally {
  await browser?.close();
  if (server.exitCode === null) { const exited = once(server, "exit"); server.kill("SIGTERM"); await exited; }
}
