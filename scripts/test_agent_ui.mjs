// Isolated UI contract test for Spec 038 (ad-hoc agent UI via show_ui).
// Start Vite on 1421; no native MCP — the mock emits the interaction events.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const answers = () => page.evaluate(() => window.__SPECCIFY_MOCK__.uiAnswers);

  // Project window: a form with Tailwind classes, answered through the bridge.
  await page.goto(`${url}?owner=me`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({
    id: "ask-1", kind: "html", prompt: "Deploy?", title: "Deploy planen", mode: "ask",
    html: `<form class="space-y-2"><p class="text-sm">Wohin?</p>
      <label class="block"><input type="radio" name="target" value="staging" checked> staging</label>
      <label class="block"><input type="radio" name="target" value="prod"> prod</label>
      <label class="block"><input type="checkbox" name="services" value="api" checked> api</label>
      <label class="block"><input type="checkbox" name="services" value="web"> web</label>
      <input name="note" value="v1.4">
      <button id="go" name="action" value="deploy" class="rounded bg-emerald-600 px-3 py-1.5 text-white">Los</button></form>`,
  }));
  const card = page.locator('[data-ui-interaction="ask-1"]');
  await card.waitFor();
  await card.getByText("Deploy planen").waitFor();
  const frame = card.frameLocator("iframe");
  await frame.locator("#go").waitFor();
  const color = await frame.locator("#go").evaluate((el) => getComputedStyle(el).backgroundColor);
  assert.notEqual(color, "rgba(0, 0, 0, 0)", `Tailwind class applied offline (got ${color})`);
  assert.equal(await page.locator("[data-spec-card]").count() > 0, true, "board still there");
  await frame.locator("#go").click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 1);
  assert.deepEqual((await answers())[0], { id: "ask-1", values: { target: "staging", services: ["api"], note: "v1.4", action: "deploy" } });
  await card.getByText(/Antwort: /).waitFor();
  assert.equal(await card.getAttribute("data-ui-mode"), "ask");
  console.log("PASS ask: HTML form rendered with Tailwind, values collected by name, answered state shown");

  // data-answer buttons: the shortest yes/no.
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({
    id: "ask-2", kind: "html", prompt: "Weiter?", mode: "ask",
    html: `<button data-answer="yes" class="mr-2">Ja</button><button data-answer="no">Nein</button>`,
  }));
  const second = page.locator('[data-ui-interaction="ask-2"]');
  await second.frameLocator("iframe").getByText("Nein").click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 2);
  assert.deepEqual((await answers())[1], { id: "ask-2", values: { answer: "no" } });
  console.log("PASS data-answer: click answers without a form");

  // show mode: display only, closing reports {closed: true}; second submit is ignored.
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({
    id: "show-1", kind: "html", prompt: "Testlauf", title: "Testlauf", mode: "show",
    html: `<table class="w-full text-sm"><tr><td>Tests</td><td class="text-emerald-700">108 passed</td></tr></table>`,
  }));
  const shown = page.locator('[data-ui-interaction="show-1"]');
  await shown.frameLocator("iframe").getByText("108 passed").waitFor();
  await shown.getByRole("button", { name: "Schließen", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 3);
  assert.deepEqual((await answers())[2], { id: "show-1", values: { closed: true } });
  await shown.getByText("geschlossen").waitFor();
  console.log("PASS show: display only, close reports back");

  // Dashboard renders the same card.
  await page.goto(`${url}?dashboard=1`);
  await page.getByRole("button", { name: /Terminal/ }).first().waitFor();
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({ id: "ask-3", kind: "html", prompt: "Hallo", mode: "ask", html: `<p id="hi" class="font-bold">Hallo</p>` }));
  await page.locator('[data-ui-interaction="ask-3"]').frameLocator("iframe").locator("#hi").waitFor();
  console.log("PASS dashboard: same card in the sidebar");

  assert.deepEqual(errors, []);
  console.log("PASS agent ui: sandboxed HTML/Tailwind forms, data-answer, show mode, project window and dashboard");
} finally {
  await browser.close();
}
