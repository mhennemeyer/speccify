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
    colorScheme: "dark", locale: "de-DE", timezoneId: "Europe/Berlin", reducedMotion: "reduce" });
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
  const board = await page.screenshot({ animations: "disabled" });
  await page.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
  await page.getByRole("tab", { name: "Git", exact: true }).click();
  await page.getByRole("textbox", { name: "Commit-Betreff", exact: true }).fill("feat: Notizen nach Titel und Inhalt durchsuchen");
  await page.getByRole("textbox", { name: "Beschreibung (optional)", exact: true }).fill("Lokale Suche mit Vorschau. Tastaturbedienung folgt in Spec 005.");
  await page.getByRole("button", { name: /2 gestagete Datei/ }).waitFor();
  await page.locator("input:focus, textarea:focus").evaluateAll(elements => elements.forEach(el => el.blur()));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const git = await page.getByRole("region", { name: "Git-Arbeitsbereich", exact: true }).screenshot({ animations: "disabled" });
  assert.deepEqual(errors, []);
  assert.deepEqual(await page.evaluate(() => window.__SPECCIFY_MOCK__.gitCalls), []);
  await mkdir(output, { recursive: true });
  await writeFile(new URL("board.png", output), board);
  await writeFile(new URL("git.png", output), git);
  console.log(`PASS: board + Git detail captured in ${fileURLToPath(output)} (real UI, isolated demo, no native mutations)`);
} finally {
  await browser?.close();
  if (server.exitCode === null) { const exited = once(server, "exit"); server.kill("SIGTERM"); await exited; }
}
