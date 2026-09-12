// Isolated UI contract test for Spec 029 (owner and branch per spec).
// Start Vite on 1421; no native Git, no project writes.
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
  const calls = () => page.evaluate(() => window.__SPECCIFY_MOCK__.ownerCalls);
  const doingCard = () => page.locator('[data-station="Doing"] [data-spec-card]').first();
  const ownedCard = () => page.locator("[data-spec-card]").filter({ has: page.locator("[data-owner]") }).first();

  // Without identity: no owner chips, "meine" disabled, no take-over offered.
  await page.goto(`${url}?owner=none`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  assert.equal(await page.locator("[data-owner]").count(), 0);
  assert.equal(await page.getByRole("button", { name: "meine", exact: true }).isDisabled(), true);
  await doingCard().locator("button").first().click();
  assert.equal(await page.getByRole("region", { name: "Besitz und Branch" }).count(), 0);
  console.log("PASS none: optional fields, no identity, nothing invented");

  // My spec: chip with initials, branch, filter "meine", hints, release.
  await page.goto(`${url}?owner=me`);
  await page.locator('[data-owner="demo@example.invalid"]').first().waitFor();
  await ownedCard().getByText(/⎇ spec\//).waitFor();
  await page.getByRole("button", { name: "meine", exact: true }).click();
  assert.equal(await page.locator("[data-spec-card]").count(), 1, "only my spec listed");
  await page.getByRole("button", { name: "Doing nach Person", exact: true }).click();
  const byPerson = page.getByRole("region", { name: "Doing nach Person" });
  await byPerson.getByText("Demo Person (ich)").waitFor();
  await byPerson.getByText(/⎇ spec\//).waitFor();
  await ownedCard().locator("button").first().click();
  const region = page.getByRole("region", { name: "Besitz und Branch" });
  await region.getByText(/Besitz: Demo Person \(ich\)/).waitFor();
  await region.getByText(/Du stehst auf main, die Spec gehört zu spec\//).waitFor();
  await region.getByText(/existiert weder lokal noch auf origin/).waitFor();
  await region.getByRole("button", { name: /Zu spec\/.* wechseln…/ }).click();
  await region.getByRole("button", { name: "Branch anlegen und wechseln", exact: true }).waitFor();
  await region.getByRole("button", { name: "Doch nicht", exact: true }).click();
  await region.getByRole("button", { name: "Abgeben", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.ownerCalls.some(call => call.startsWith("release:")));
  console.log("PASS me: chip, branch, filter, person view, hints, explicit switch, release");

  // Someone else's spec: no release for me, but the observation names them.
  await page.goto(`${url}?owner=other`);
  await page.locator('[data-owner="ben@example.invalid"]').first().waitFor();
  await page.getByRole("button", { name: "meine", exact: true }).click();
  assert.equal(await page.locator("[data-spec-card]").count(), 0, "nothing of mine");
  await page.getByRole("button", { name: "Filter zurücksetzen", exact: true }).click();
  await ownedCard().locator("button").first().click();
  const other = page.getByRole("region", { name: "Besitz und Branch" });
  await other.getByText(/Besitz: Ben Kollege/).waitFor();
  await other.getByText(/Zuletzt hat Ben Kollege auf diesen Branch gepusht \(2026-09-01\)/).waitFor();
  await other.getByText(/Seit 11 Tagen keine Bewegung/).waitFor();
  assert.equal(await other.getByRole("button", { name: "Abgeben", exact: true }).count(), 0);
  assert.equal(await other.getByRole("button", { name: "Übernehmen", exact: true }).count(), 0, "owned by someone else");
  console.log("PASS other: observation shown, no take-over of a colleague's spec");

  // A spec without owner (here in Doing): take-over from the inspector.
  const freeCard = page.locator('[data-station="Doing"] [data-spec-card]').filter({ hasNot: page.locator("[data-owner]") }).first();
  const file = await freeCard.getAttribute("data-spec-card");
  await freeCard.locator("button").first().click();
  await page.getByRole("region", { name: "Besitz und Branch" }).getByRole("button", { name: "Übernehmen", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.ownerCalls.some(call => call.startsWith("take:")));
  assert.ok((await calls()).includes(`take:${file}:`));
  console.log("PASS take: explicit take-over records owner and branch");

  assert.deepEqual(errors, []);
  console.log("PASS spec owner: fields optional, chips, filter meine, Doing nach Person, hints without correction, take/release");
} finally {
  await browser.close();
}
