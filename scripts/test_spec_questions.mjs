// Spec 065: an agent question renders as Markdown — paragraphs, a list, code —
// and every code span or block carries a copy button that writes exactly its
// content to the clipboard.
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
  await page.goto(`${url}?qmd=1`);
  await page.locator('[data-spec-card=".agent/specs/live-test/SPEC.md"]').getByRole("button", { name: /Live-Reload/ }).click();
  const box = page.locator("[data-question-text]").first();
  await box.waitFor();

  // Structure instead of one block: paragraphs, a list with two items, one code block.
  assert.equal(await box.locator("p").count(), 4);
  assert.equal(await box.locator("li").count(), 2);
  assert.equal(await box.locator("[data-question-block]").count(), 1);
  assert.equal(await box.locator("strong").count(), 1);
  // A single newline in the agent's text stays a line break.
  assert.equal(await box.locator("p br").count(), 1);

  // Inline code: highlighted and each with its own copy button.
  const spans = box.locator("[data-question-code]");
  assert.equal(await spans.count(), 3);
  assert.equal(await spans.nth(0).textContent(), 'ssh billi-vm "ssh-keygen -t ed25519 -f C:\\Users\\billi\\.ssh\\id_deploy"');
  const buttons = box.locator("[data-copy-code]");
  assert.equal(await buttons.count(), 4); // three spans + one block

  // Copying writes exactly the code, without backticks, and the button confirms.
  await buttons.nth(0).click();
  await box.getByRole("button", { name: "✓ kopiert" }).waitFor();
  await buttons.nth(3).click();
  const clipboard = await page.evaluate(() => window.__SPECCIFY_MOCK__.clipboard);
  assert.deepEqual(clipboard, [
    'ssh billi-vm "ssh-keygen -t ed25519 -f C:\\Users\\billi\\.ssh\\id_deploy"',
    "git remote set-url origin git@gitlab:avc/rekas.git\ngit pull",
  ]);
  // The confirmation is transient.
  await box.getByRole("button", { name: "✓ kopiert" }).first().waitFor({ state: "hidden", timeout: 5000 });

  // The answer box still works next to the rendered text.
  await page.getByPlaceholder("Antwort…").waitFor();

  // Plain text questions stay plain: one paragraph, no buttons.
  await page.goto(url);
  await page.locator('[data-spec-card=".agent/specs/live-test/SPEC.md"]').getByRole("button", { name: /Live-Reload/ }).click();
  await box.waitFor();
  assert.equal(await box.locator("p").count(), 1);
  assert.equal(await box.locator("[data-copy-code]").count(), 0);

  assert.deepEqual(errors, []);
  console.log("test_spec_questions: ok");
} finally {
  await browser.close();
}
