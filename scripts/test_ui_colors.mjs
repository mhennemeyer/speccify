// Isolated visual/contrast contract; no native file writes or Git operations.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
const luminance = rgb => rgb.slice(0, 3).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
  .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
const contrast = (a, b) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05);
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${url}?colors=1`);
  await page.locator(".spec-lane").first().waitFor();
  const kinds = await page.evaluate(async () => {
    const { fileKind } = await import("/src/components/FileTypeIcon.tsx");
    return ["src/APP.TSX", "main.rs", "main.py", "package.json", ".env.local", "Cargo.lock", "README.md", "logo.SVG", "unknown.xyz", "C:\\work\\app.cs"].map(fileKind);
  });
  assert.deepEqual(kinds, ["code", "code", "code", "config", "config", "config", "document", "image", "file", "code"]);
  for (const theme of ["light", "dark"]) {
    if (theme === "dark") await page.getByRole("button", { name: "Dunkel schalten", exact: true }).click();
    await page.waitForFunction(t => document.documentElement.dataset.theme === t, theme);
    const pairs = await page.evaluate(() => {
      const probe = document.createElement("span");
      document.body.append(probe);
      const rgb = value => {
        probe.style.color = value;
        return getComputedStyle(probe).color.match(/[\d.]+/g).map(Number);
      };
      const result = ["blue", "violet", "teal", "amber", "green", "rose", "slate"].map(tone => ({
        tone, ink: rgb(`var(--accent-${tone}-ink)`), soft: rgb(`var(--accent-${tone}-soft)`),
        white: rgb("var(--color-white)"), selected: rgb("var(--accent-blue-soft)"),
      }));
      probe.remove();
      return result;
    });
    for (const pair of pairs) {
      assert.ok(contrast(pair.ink, pair.soft) >= 4.5, `${theme} ${pair.tone}: text contrast`);
      assert.ok(contrast(pair.ink, pair.white) >= 3, `${theme} ${pair.tone}: icon contrast`);
      assert.ok(contrast(pair.ink, pair.selected) >= 3, `${theme} ${pair.tone}: selected icon contrast`);
    }
    const groupTabs = page.getByRole("tablist", { name: "Bereiche", exact: true });
    await groupTabs.getByRole("tab", { name: "Specs", exact: true }).click();
    const tones = await page.locator(".spec-lane").evaluateAll(lanes => lanes.map(el => el.dataset.tone));
    assert.deepEqual(tones, ["slate", "blue", "green"]);
    const card = page.locator(".spec-card").first();
    await card.getByRole("button").click();
    assert.equal(await card.getAttribute("data-selected"), "true");
    await page.screenshot({ path: `/private/tmp/speccify-colors-${theme}.png` });
    await card.getByRole("button").click();
    await groupTabs.getByRole("tab", { name: "Dateien", exact: true }).click();
    const nav = page.locator('[data-nav-slot="files"]');
    await nav.getByRole("button", { name: "src", exact: true }).click();
    for (const kind of ["folder", "code", "config", "document", "image", "file"]) {
      assert.ok(await nav.locator(`[data-file-kind="${kind}"]`).count() > 0, kind);
    }
    const file = nav.getByRole("button", { name: "README.md", exact: true });
    await file.click();
    await page.waitForFunction(() => document.querySelector('.file-row[aria-current="true"]')?.title === "README.md");
    await file.focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    assert.equal(await file.evaluate(el => getComputedStyle(el).outlineStyle), "solid");
    await page.screenshot({ path: `/private/tmp/speccify-files-${theme}.png` });
    // Return folder to original collapsed state for the other theme.
    await nav.getByRole("button", { name: "src", exact: true }).click();
    console.log(`PASS ${theme}: text/icon contrast, navigation, board selection, six file kinds, file selection and keyboard focus`);
  }
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
