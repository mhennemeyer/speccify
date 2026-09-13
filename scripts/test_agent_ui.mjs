// Isolated UI contract test for Spec 038 (ad-hoc agent UI via show_ui).
// Start Vite on 1421; no native MCP — the mock serves the pending question
// and records answers and window closes.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : "playwright");
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
const url = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
try {
  const page = await browser.newPage({ viewport: { width: 700, height: 600 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const answers = () => page.evaluate(() => window.__SPECCIFY_MOCK__.uiAnswers);
  const closes = () => page.evaluate(() => window.__SPECCIFY_MOCK__.windowCloses);

  // Popup window: a form with Tailwind classes, answered through the bridge, then the window closes.
  await page.goto(`${url}?askwin=form`);
  const card = page.locator('[data-ui-interaction="ask-1"]');
  await card.waitFor();
  await page.getByText("Deploy planen").first().waitFor();
  const frame = card.frameLocator("iframe");
  await frame.locator("#go").waitFor();
  const color = await frame.locator("#go").evaluate((el) => getComputedStyle(el).backgroundColor);
  assert.notEqual(color, "rgba(0, 0, 0, 0)", `Tailwind class applied offline (got ${color})`);
  await frame.locator("#go").click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 1);
  assert.deepEqual((await answers())[0], { id: "ask-1", values: { target: "staging", services: ["api"], note: "v1.4", action: "deploy" } });
  await card.getByText(/Antwort: /).waitFor();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.windowCloses.length === 1);
  assert.deepEqual(await closes(), ["ask-1"]);
  console.log("PASS popup form: Tailwind offline, values by name, answer shown, window closes itself");

  // data-answer buttons: the shortest yes/no.
  await page.goto(`${url}?askwin=answer`);
  const second = page.locator('[data-ui-interaction="ask-1"]');
  await second.frameLocator("iframe").getByText("Nein").click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 1);
  assert.deepEqual((await answers())[0], { id: "ask-1", values: { answer: "no" } });
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.windowCloses.length === 1);
  console.log("PASS popup data-answer: click answers without a form");

  // show mode: display only; closing reports {closed: true} and closes the window.
  await page.goto(`${url}?askwin=show`);
  const shown = page.locator('[data-ui-interaction="ask-1"]');
  await shown.frameLocator("iframe").getByText("108 passed").waitFor();
  assert.equal(await shown.getAttribute("data-ui-mode"), "show");
  await shown.getByRole("button", { name: "Schließen", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.uiAnswers.length === 1);
  assert.deepEqual((await answers())[0], { id: "ask-1", values: { closed: true } });
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.windowCloses.length === 1);
  console.log("PASS popup show: display only, close reports back and closes the window");

  // Project window and dashboard do not render HTML questions themselves (the popup does).
  await page.setViewportSize({ width: 1500, height: 1000 });
  await page.goto(`${url}?owner=me`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({ id: "ask-9", kind: "html", prompt: "x", mode: "ask", html: "<p>x</p>" }));
  await page.waitForTimeout(300);
  assert.equal(await page.locator("[data-ui-interaction]").count(), 0, "no inline HTML card in the project window");
  await page.goto(`${url}?dashboard=1`);
  await page.getByRole("button", { name: /Terminal/ }).first().waitFor();
  await page.evaluate(() => window.__SPECCIFY_MOCK__.askUi({ id: "ask-9", kind: "html", prompt: "x", mode: "ask", html: "<p>x</p>" }));
  await page.waitForTimeout(300);
  assert.equal(await page.locator("[data-ui-interaction]").count(), 0, "dashboard leaves HTML questions to the popup");
  assert.equal(await page.locator("aside").count() > 0 && await page.locator("aside").isVisible(), false, "sidebar stays closed for HTML questions");
  console.log("PASS windows: HTML questions live in the popup only");

  assert.deepEqual(errors, []);
  console.log("PASS agent ui: popup per question, sandboxed HTML/Tailwind, form/data-answer/show, self-closing");
} finally {
  await browser.close();
}
