// UI smoke for the playbook viewer: list, open, click through steps, select a
// source and an asset. Selection is what a context-aware agent reads, so it is
// worth pinning.

import { expect, test } from "@playwright/test";

test("open a playbook, walk its steps, select a source and an asset", async ({ page }) => {
  await page.goto("/");

  await test.step("the library lists the reference playbooks", async () => {
    await expect(page.locator(".library-item")).toHaveCount(2);
    await expect(page.locator(".library-item").first()).toContainText("Developer ID");
  });

  await test.step("opening shows steps, pitfalls and sources", async () => {
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/macos-notarize-tauri@1.0.0",
    );
    await expect(page.locator(".steps > li")).toHaveCount(5);
    await expect(page.locator(".pitfalls")).toContainText("unsigned sidecars");
  });

  await test.step("clicking a step selects it", async () => {
    const step = page.locator(".card.step").filter({ hasText: "notarytool" });
    await step.click();
    await expect(step).toHaveClass(/selected/);
  });

  await test.step("a source chip can be selected", async () => {
    const chip = page.locator(".chip").filter({ hasText: "Notarizing macOS" }).first();
    await chip.click();
    await expect(chip).toHaveClass(/selected/);
  });

  await test.step("an asset shows its content", async () => {
    await page.locator(".chip").filter({ hasText: "verify-signatures.sh" }).first().click();
    await expect(page.locator(".asset-view pre")).toContainText("codesign --verify");
  });

  await test.step("a delegated step links to its child playbook", async () => {
    await page.locator(".link").filter({ hasText: "apple-developer-id-cert" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/apple-developer-id-cert@1.0.0",
    );
  });
});
