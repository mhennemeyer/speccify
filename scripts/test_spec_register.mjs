// Isolated UI contract test for Spec 028 (shared spec register in the project window).
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
  const calls = () => page.evaluate(() => window.__SPECCIFY_MOCK__.registerCalls);

  // No register: nothing is shown, the board is unchanged.
  await page.goto(`${url}?register=none`);
  await page.getByText("notes/zahlen.md mit Quadratzahlen 1–5 anlegen").first().waitFor();
  assert.equal(await page.locator("[data-register]").count(), 0);
  console.log("PASS none: no register, no banner");

  // Migratable: explicit two-step setup, then the mounted status line.
  await page.goto(`${url}?register=migratable`);
  await page.getByText("Specs als gemeinsames Team-Register führen?").waitFor();
  await page.getByRole("button", { name: "Register einrichten…", exact: true }).click();
  await page.getByText(/entfernt den Ordner aus/).waitFor();
  assert.deepEqual(await calls(), [], "nothing runs before the confirmation");
  await page.getByRole("button", { name: "Jetzt einrichten", exact: true }).click();
  await page.locator("[data-register=mounted]").waitFor();
  assert.deepEqual(await calls(), ["setup"]);
  await page.getByLabel("Register-Stand").getByText(/2 nicht gesendet · 1 neu vom Team/).waitFor();
  console.log("PASS migratable: confirmation before setup, mounted status afterwards");

  // Detached (fresh clone): one click mounts.
  await page.goto(`${url}?register=detached`);
  await page.getByText("Team-Register vorhanden, noch nicht eingehängt.").waitFor();
  await page.getByRole("button", { name: "Einhängen", exact: true }).click();
  await page.locator("[data-register=mounted]").waitFor();
  console.log("PASS detached: mount from a fresh clone");

  // Blocked: reason shown, no action offered.
  await page.goto(`${url}?register=blocked`);
  await page.getByText("Spec-Register blockiert.").waitFor();
  await page.getByText(/feature\/alt/).waitFor();
  assert.equal(await page.getByRole("button", { name: /einrichten|Einhängen|Sync/ }).count(), 0);
  console.log("PASS blocked: explanation without a button");

  // Mounted: manual sync, and a native status event updates the line.
  await page.goto(`${url}?register=mounted`);
  await page.getByRole("button", { name: "Sync", exact: true }).click();
  await page.waitForFunction(() => window.__SPECCIFY_MOCK__.registerCalls.includes("sync"));
  await page.getByText(/Sync 12:34 UTC/).waitFor();
  await page.evaluate(() => window.__SPECCIFY_MOCK__.emit("register-changed", {
    project: "/private/tmp/claude-501/w1-projekt",
    status: { mode: "mounted", branch: "specs", remote: true, code_branch: "main", tracked_in_code: false, ahead: 0, behind: 0, unsent: 0, rebasing: false, conflicts: [], last_sync: "2026-09-12T13:00:00Z", last_error: "Fetch: Remote nicht erreichbar", reason: null },
  }));
  await page.getByLabel("Register-Stand").getByText("· aktuell").waitFor();
  await page.getByText(/Fetch: Remote nicht erreichbar/).waitFor();
  console.log("PASS mounted: manual sync and live status events");

  // Conflict: both versions visible, the card is marked, a decision resolves.
  await page.goto(`${url}?register=conflict`);
  const region = page.getByRole("region", { name: "Register-Konflikte" });
  await region.waitFor();
  await region.getByText("Team (origin/specs)").waitFor();
  await region.locator("pre").filter({ hasText: "station: Done" }).waitFor();
  await region.locator("pre").filter({ hasText: "station: Backlog" }).waitFor();
  const conflictId = await page.locator("[data-register-conflict]").getAttribute("data-register-conflict");
  await page.locator(`[data-spec-card$="${conflictId}/SPEC.md"]`).getByText("Konflikt", { exact: true }).waitFor();
  await page.getByLabel("Register-Stand").getByText(/Konflikt in 1 Datei/).waitFor();
  await region.getByRole("button", { name: "Team-Fassung übernehmen", exact: true }).click();
  await page.locator("[data-register-state=ok]").waitFor();
  assert.deepEqual(await calls(), [`resolve:team:.agent/specs/${conflictId}/SPEC.md`]);
  assert.equal(await page.getByText("Konflikt", { exact: true }).count(), 0, "card badge cleared");
  console.log("PASS conflict: both versions, card badge, explicit decision");

  // Abort keeps the local commit and leaves the register ahead/behind.
  await page.goto(`${url}?register=conflict`);
  await page.getByRole("button", { name: /Abbrechen — eigenen Stand behalten/ }).click();
  await page.getByLabel("Register-Stand").getByText(/1 zu pushen · 1 neu vom Team/).waitFor();
  assert.deepEqual(await calls(), ["abort"]);
  console.log("PASS abort: local commit kept, divergence visible");

  assert.deepEqual(errors, []);
  console.log("PASS spec register: none/migratable/detached/blocked/mounted/conflict states, explicit setup and decisions");
} finally {
  await browser.close();
}
