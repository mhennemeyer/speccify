// UI contract in an isolated mock; native mutation safety is covered by Rust temp repositories.
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
  const openGit = async () => {
    await page.getByRole("button", { name: /^Navigator (ein|aus)blenden/ }).waitFor();
    const showNavigator = page.getByRole("button", { name: /^Navigator einblenden/ });
    if (await showNavigator.isVisible()) await showNavigator.click();
    await page.getByRole("tablist", { name: "Bereiche", exact: true }).getByRole("tab", { name: "Dateien", exact: true }).click();
    await page.getByRole("tab", { name: "Git", exact: true }).click();
    await page.getByRole("form", { name: "Commit erstellen" }).waitFor();
  };
  await page.goto(`${url}?git=1`);
  await openGit();
  const composer = page.getByRole("form", { name: "Commit erstellen" });
  const subject = composer.getByRole("textbox", { name: "Commit-Betreff", exact: true });
  const body = composer.getByRole("textbox", { name: "Beschreibung (optional)", exact: true });
  const commit = composer.getByRole("button", { name: /gestagete Datei/ });
  assert.equal(await commit.isDisabled(), true);
  await subject.fill("feat: workspace");
  await body.fill("Detailed body\nsecond line");
  await page.locator('[data-nav-slot="git"]').getByRole("button", { name: /README.md/ }).click();
  assert.equal(await subject.inputValue(), "feat: workspace");
  await page.getByRole("button", { name: /^Inspektor ausblenden/ }).click();
  await page.getByRole("button", { name: /^Navigator ausblenden/ }).click();
  assert.equal(await composer.isVisible(), true);
  await page.reload();
  await openGit();
  assert.equal(await subject.inputValue(), "feat: workspace");
  assert.equal(await body.inputValue(), "Detailed body\nsecond line");
  await page.goto(`${url}?git=1&project=${encodeURIComponent("/private/tmp/second-repo")}`);
  await openGit();
  assert.equal(await subject.inputValue(), "");
  await page.goto(`${url}?git=1`);
  await openGit();
  assert.equal(await subject.inputValue(), "feat: workspace");
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.gitFailure = "hook rejected commit"; window.__SPECCIFY_MOCK__.gitDelay = 700; });
  await subject.focus();
  await page.keyboard.press("Control+Enter");
  await page.keyboard.press("Control+Enter");
  await page.getByRole("alert").filter({ hasText: "hook rejected commit" }).waitFor();
  // A polling refresh must not silently clear an action error.
  await page.evaluate(() => window.dispatchEvent(new Event("speccify:worktree-changed")));
  assert.equal(await page.getByRole("alert").isVisible(), true);
  assert.equal(await subject.inputValue(), "feat: workspace");
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.gitCalls.length), 1);
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.gitFailure = null; });
  await commit.click();
  await page.waitForFunction(() => document.querySelector('input[placeholder="feat: …"]')?.value === "");
  const calls = await page.evaluate(() => window.__SPECCIFY_MOCK__.gitCalls);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].message, "feat: workspace\n\nDetailed body\nsecond line");
  assert.equal(calls[1].project, "/private/tmp/claude-501/w1-projekt");
  assert.equal(calls.some(c => c.command === "stage"), false);
  await subject.fill("next commit");
  await composer.getByText(/Erst Dateien oder Hunks stagen/).waitFor();
  assert.equal(await commit.isDisabled(), true);
  await page.getByRole("button", { name: /main · Branches/ }).click();
  const branches = page.getByRole("region", { name: "Branch-Verwaltung" });
  const row = name => branches.locator(`[data-branch="${name}"]`);
  assert.equal(await row("main").getByRole("button", { name: "Löschen…", exact: true }).isDisabled(), true);
  assert.equal(await row("origin/main").getByRole("button").count(), 0);
  const search = branches.getByRole("textbox", { name: "Branches suchen", exact: true });
  await search.fill("NOTIZEN");
  assert.equal(await branches.locator("[data-branch]").count(), 1);
  await row("feature/notizen").getByRole("button", { name: "Wechseln", exact: true }).click();
  const confirm = branches.getByRole("form", { name: "Branch-Aktion bestätigen" });
  await confirm.getByText(/aktuell: main/).waitFor();
  await confirm.getByRole("button", { name: "Abbrechen", exact: true }).click();
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.gitCalls.length), 2);
  await row("feature/notizen").getByRole("button", { name: "Wechseln", exact: true }).click();
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.gitFailure = "local changes would be overwritten"; });
  await confirm.getByRole("button", { name: "Bestätigen", exact: true }).click();
  await page.getByRole("alert").filter({ hasText: "local changes would be overwritten" }).waitFor();
  assert.equal(await confirm.isVisible(), true);
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.gitFailure = null; });
  await confirm.getByRole("button", { name: "Bestätigen", exact: true }).click();
  await page.getByRole("button", { name: /feature\/notizen · Branches/ }).waitFor();
  await search.fill("");
  await row("feature/notizen").getByRole("button", { name: "Umbenennen", exact: true }).click();
  await confirm.getByRole("textbox", { name: "Branch-Name", exact: true }).fill("feature/renamed");
  await confirm.getByRole("button", { name: "Bestätigen", exact: true }).click();
  await page.getByRole("button", { name: /feature\/renamed · Branches/ }).waitFor();
  await branches.getByRole("button", { name: "Neuer Branch", exact: true }).click();
  await confirm.getByRole("textbox", { name: "Branch-Name", exact: true }).fill("feature/new");
  await confirm.getByRole("button", { name: "Bestätigen", exact: true }).click();
  await page.getByRole("button", { name: /feature\/new · Branches/ }).waitFor();
  await row("feature/renamed").getByRole("button", { name: "Löschen…", exact: true }).click();
  await confirm.getByText(/Kein Force-Delete/).waitFor();
  await confirm.getByRole("button", { name: "Bestätigen", exact: true }).click();
  await row("feature/renamed").waitFor({ state: "detached" });
  assert.equal(await subject.inputValue(), "next commit");
  for (const theme of ["light", "dark"]) {
    if (theme === "dark") await page.getByRole("button", { name: "Dunkel schalten", exact: true }).click();
    await page.getByRole("region", { name: "Git-Arbeitsbereich", exact: true }).evaluate(el => el.parentElement.scrollTop = 0);
    const colors = await page.locator("button.tone-surface[data-tone=blue]").evaluate(el => {
      const style = getComputedStyle(el);
      const rgb = text => text.match(/[\d.]+/g).map(Number);
      return [rgb(style.color), rgb(style.backgroundColor)];
    });
    const luminance = rgb => rgb.slice(0, 3).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const values = colors.map(luminance);
    assert.ok((Math.max(...values) + .05) / (Math.min(...values) + .05) >= 4.5, `${theme}: branch button contrast`);
    await page.screenshot({ path: `/private/tmp/speccify-git-workspace-${theme}.png` });
  }
  assert.deepEqual(errors, []);
  console.log("PASS Git workspace: visible composer, hidden panels, reload/project drafts, multiline commit, index only, no double-start, persistent errors, branch search/confirmation/switch/create/rename/delete, remote read-only");
  await page.goto(`${url}?actions=manual&listeners=delayed`);
  await openGit();
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("speccify:git", { detail: "fetch" }));
    window.dispatchEvent(new CustomEvent("speccify:git", { detail: "fetch" }));
  });
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.actionStarts.length === 1);
  await page.getByText("Erste Ausgabe direkt beim Start", { exact: true }).waitFor();
  const fetch = page.locator('[data-nav-slot="git"]').getByRole("button", { name: "fetch", exact: true });
  await page.evaluate(() => window.__SPECCIFY_MOCK__.emit("action-exit", { run_id: "git:unrelated", exit_code: 0, error: null }));
  assert.equal(await fetch.isDisabled(), true);
  await page.evaluate(() => window.__SPECCIFY_MOCK__.emit("action-exit", {
    run_id: window.__SPECCIFY_MOCK__.actionStarts[0], exit_code: 1, error: "remote unavailable",
  }));
  await page.getByText(/Erste Ausgabe direkt beim Start\nremote unavailable/).waitFor();
  assert.equal(await fetch.isDisabled(), false);
  await page.goto(`${url}?listeners=fail`);
  await openGit();
  await page.locator('[data-nav-slot="git"]').getByRole("button", { name: "fetch", exact: true }).click();
  await page.getByText("mock listener failed", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.actionStarts.length), 0);
  assert.deepEqual(errors, []);
  console.log("PASS Git remote output: listener readiness, immediate output, no duplicate start, unrelated exit ignored, failure visible, failed listener prevents launch");
} finally { await browser.close(); }
