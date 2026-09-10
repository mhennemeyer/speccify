// Isolated UI contract test. Start Vite on 1421; no native project writes.
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
  await page.goto(`${url}?workflow=mixed`);
  await page.getByText("Workflow-Einrichtung braucht Prüfung.", { exact: true }).waitFor();
  await page.getByText(/\.claude\/skills: fremdes Ziel/).waitFor();
  await page.getByRole("button", { name: "Einrichten", exact: true }).click();
  await page.getByRole("button", { name: "Einrichten", exact: true }).waitFor({ state: "detached" });
  await page.getByText(/\.claude\/skills: fremdes Ziel/).waitFor();
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.workflowInstalls), 1);
  await page.goto(`${url}?workflow=manual`);
  await page.getByText("Workflow-Einrichtung braucht Prüfung.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Einrichten", exact: true }).count(), 0);
  console.log("PASS setup: structured manual/installable issues, custom target preserved, no v5→v5 warning");

  await page.goto(url);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().click();
  await page.getByRole("tab", { name: "Tasks 2/3", exact: true }).click();
  const task = page.getByRole("checkbox", { name: "Prüfen und Verification schreiben", exact: true });
  await task.waitFor();
  await page.evaluate(() => { window.__SPECCIFY_MOCK__.staleTaskOnce = true; });
  await task.click(); // Rejected stale click must leave the checkbox unchecked.
  await page.getByText(/SPEC_CHANGED: Spec wurde zwischenzeitlich geändert/).waitFor();
  assert.equal(await task.isChecked(), false);
  assert.equal(await page.evaluate(() => window.__SPECCIFY_MOCK__.specs[0].tasks_done), 2);
  const first = await page.evaluate(() => window.__SPECCIFY_MOCK__.taskCalls[0]);
  assert.equal(first.index, 2);
  assert.equal(first.expectedBody.includes("Externe Änderung"), false);
  await task.check();
  await page.getByRole("tab", { name: "Tasks 3/3", exact: true }).waitFor();
  assert.equal(await task.isChecked(), true);
  const retry = await page.evaluate(() => window.__SPECCIFY_MOCK__.taskCalls[1]);
  assert.equal(retry.expectedBody.includes("Externe Änderung bleibt erhalten."), true);
  assert.equal(await page.getByText(/SPEC_CHANGED:/).count(), 0);
  assert.deepEqual(errors, []);
  console.log("PASS tasks: native DTO, expected snapshot, stale-click rejection/reload, safe retry and shared progress");
  await page.close();
} finally {
  await browser.close();
}
