// Run against the isolated desktop mock, never against a user's native window.
// pnpm --filter speccify-desktop dev --host 127.0.0.1 --port 1421
// PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/test_action_output.mjs
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import { DEFAULT_LAYOUT, loadLayout, saveLayout } from "../apps/desktop/src/lib/layout.ts";

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
};
saveLayout("fixture", { ...DEFAULT_LAYOUT, rightTab: "output:test", rightWidth: 550 });
assert.equal(loadLayout("fixture").rightTab, "inspector");
assert.equal(loadLayout("fixture").rightWidth, 550);
saveLayout("fixture", { ...DEFAULT_LAYOUT, rightTab: "terminal", terminalDock: "right" });
assert.equal(loadLayout("fixture").rightTab, "terminal");
saveLayout("fixture", { ...DEFAULT_LAYOUT, rightTab: "terminal" });
assert.equal(loadLayout("fixture").rightTab, "inspector");
console.log("PASS layout restore: transient output, right terminal, bottom terminal");

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
try {
  for (const dock of ["bottom", "right"]) {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(({ dock, layout }) => {
      const key = "speccify.project.layout:/private/tmp/claude-501/w1-projekt";
      if (!localStorage.getItem(key)) localStorage.setItem(key,
        JSON.stringify({ ...layout, terminalDock: dock, rightShown: false }));
    }, { dock, layout: DEFAULT_LAYOUT });
    await page.goto(`${process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html"}?actions=manual&listeners=delayed`);
    const output = page.getByLabel("Aktionsausgabe", { exact: true });
    const tests = page.getByRole("button", { name: "Tests — uv run pytest", exact: true });
    const testsTab = page.getByRole("button", { name: "Ausgabe: Tests", exact: true });
    await tests.click();
    await testsTab.waitFor({ state: "visible" });
    await output.getByText("Erste Ausgabe direkt beim Start", { exact: true }).waitFor();
    assert.equal(await output.isVisible(), true);
    // The board remains visible; output does not navigate to the Actions main tab.
    assert.equal(await page.getByText("Live-Reload Beweisticket", { exact: true }).first().isVisible(), true);
    assert.equal(await page.getByRole("button", { name: "Ausgabe schließen: Tests", exact: true }).isDisabled(), true);
    await tests.click();
    assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.actionStarts.length), 1);
    const emit = (event, payload) => page.evaluate(({ event, payload }) => {
      window.__SPECCIFY_MOCK__.emit(event, payload);
    }, { event, payload });
    await emit("action-output", { run_id: "uv run pytest", line: '{"kind":"chart","series":[{"name":"Messung","points":[[1,2],[2,4]]}]}' });
    await output.locator("svg").waitFor();
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("speccify:run-action", { detail: "ls notes" })));
    await page.getByRole("button", { name: "Ausgabe: Notizen zählen", exact: true }).waitFor();
    await emit("action-output", { run_id: "ls notes", line: "Nur im Notizen-Tab" });
    await output.getByText("Nur im Notizen-Tab", { exact: true }).waitFor();
    await testsTab.click();
    assert.equal(await output.getByText("Nur im Notizen-Tab", { exact: true }).count(), 0);
    await output.locator("svg").waitFor();
    await page.evaluate(() => { window.__SPECCIFY_MOCK__.failStop = true; });
    await output.getByRole("button", { name: "Stop", exact: true }).click();
    await output.getByText(/Stop fehlgeschlagen:.*mock stop failed/).waitFor();
    await page.evaluate(() => { window.__SPECCIFY_MOCK__.failStop = false; });
    await output.getByRole("button", { name: "Stop", exact: true }).click();
    await output.getByText("Fehler: gestoppt", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Ausgabe schließen: Tests", exact: true }).click();
    await testsTab.waitFor({ state: "detached" });
    assert.equal(await page.getByRole("button", { name: "Inspektor", exact: true }).getAttribute("aria-pressed"), "true");
    await page.evaluate(() => { window.__SPECCIFY_MOCK__.failStart = true; });
    await tests.click();
    await output.getByText(/Fehler:.*mock start failed/).waitFor();
    await page.evaluate(() => { window.__SPECCIFY_MOCK__.failStart = false; });
    await tests.click();
    await output.getByText("Erste Ausgabe direkt beim Start", { exact: true }).waitFor();
    assert.equal(await output.getByText(/mock start failed/).count(), 0);
    await page.evaluate(() => {
      for (let n = 0; n < 2005; n++) window.__SPECCIFY_MOCK__.emit("action-output", { run_id: "uv run pytest", line: `Zeile ${n}` });
    });
    await output.getByText("Zeile 2004", { exact: true }).waitFor();
    assert.equal(await output.getByText("Zeile 4", { exact: true }).count(), 0);
    assert.equal(await output.getByText("Zeile 5", { exact: true }).count(), 1);
    await emit("action-exit", { run_id: "uv run pytest", exit_code: 1, duration_ms: 1500, error: null });
    await output.getByText("exit 1 · 2s", { exact: true }).waitFor();
    assert.match(await testsTab.getAttribute("title"), /fehlgeschlagen/);
    await emit("action-exit", { run_id: "ls notes", exit_code: 0, duration_ms: 100, error: null });
    await page.getByRole("button", { name: "Ausgabe schließen: Notizen zählen", exact: true }).click();
    assert.equal(await testsTab.getAttribute("aria-pressed"), "true");
    await page.getByRole("button", { name: "Inspektor", exact: true }).click();
    assert.equal(await output.isVisible(), false);
    if (dock === "right") {
      await page.getByRole("button", { name: "Terminal", exact: true }).click();
      assert.equal(await page.getByRole("button", { name: "Terminal", exact: true }).getAttribute("aria-pressed"), "true");
    }
    await testsTab.click();
    await output.getByText("exit 1 · 2s", { exact: true }).waitFor();
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("speccify:show-tab", { detail: "actions" })));
    await page.locator('[data-action="uv run pytest"]').getByRole("button", { name: "Ausführen", exact: true }).click();
    await output.getByText("Erste Ausgabe direkt beim Start", { exact: true }).waitFor();
    await emit("action-exit", { run_id: "uv run pytest", exit_code: 0, duration_ms: 1000, error: null });
    await output.getByText("exit 0 · 1s", { exact: true }).waitFor();
    await page.reload();
    await page.getByRole("button", { name: "Inspektor", exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Inspektor", exact: true }).getAttribute("aria-pressed"), "true");
    assert.equal(await testsTab.count(), 0);
    assert.deepEqual(errors, []);
    await page.close();
    console.log(`PASS ${dock} dock: toolbar/board, hidden sidebar, immediate output, duplicate start, charts, parallel runs, stop/error, close, retry, output limit, terminal, reload`);
  }
  const page = await browser.newPage();
  await page.goto(`${process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html"}?listeners=fail`);
  await page.getByRole("button", { name: "Tests — uv run pytest", exact: true }).click();
  await page.getByLabel("Aktionsausgabe", { exact: true }).getByText("Fehler: mock listener failed", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.actionStarts.length), 0);
  await page.close();
  console.log("PASS failed listener: visible error, no unobservable process started");
} finally {
  await browser.close();
}
