// UI smoke for the playbook viewer: list, open, click through steps, select a
// source and an asset. Selection is what a context-aware agent reads, so it is
// worth pinning.

import { expect, test } from "@playwright/test";

test("open a playbook, walk its steps, select a source and an asset", async ({ page }) => {
  await page.goto("/");

  await test.step("the library lists the reference playbooks and filters", async () => {
    // `count()` does not auto-wait — make sure the list has loaded first.
    await expect(page.locator(".library-item").first()).toBeVisible();
    const all = await page.locator(".library-item").count();
    expect(all).toBeGreaterThanOrEqual(4);
    await page.locator("#library-filter").fill("tauri");
    await expect(page.locator(".library-item")).toHaveCount(1);
    await page.locator("#library-filter").fill("");
    await expect(page.locator(".library-item")).toHaveCount(all);
  });

  await test.step("opening shows steps, pitfalls and sources", async () => {
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/macos-notarize-tauri@1.0.0",
    );
    await expect(page.locator(".steps > li")).toHaveCount(5);
    await expect(page.locator(".pitfalls")).toContainText("unsigned sidecars");
  });

  await test.step("the workflow diagram mirrors the steps and drives selection", async () => {
    await expect(page.locator(".step-flow .flow-node")).toHaveCount(5);
    // The first step delegates to a child playbook.
    await expect(page.locator(".step-flow .flow-node").first()).toHaveClass(/delegated/);
    await page.locator(".step-flow .flow-node").nth(3).click();
    await expect(page.locator(".card.step").filter({ hasText: "notarytool" })).toHaveClass(
      /selected/,
    );
  });

  await test.step("step detail renders as markdown, not as raw text", async () => {
    const step = page.locator(".card.step").filter({ hasText: "notarytool" });
    await step.click();
    await expect(step).toHaveClass(/selected/);
    // The fenced block in the YAML becomes a real <pre><code>.
    await expect(step.locator(".markdown pre code").first()).toContainText(
      "xcrun notarytool submit",
    );
  });

  await test.step("inline markdown is rendered, not shown as backticks", async () => {
    // Prerequisites and verify criteria contain `code` — it must render.
    await expect(page.locator(".card").first().locator("li code").first()).toContainText(
      "pnpm tauri build",
    );
    await expect(page.locator(".verify code").first()).toBeVisible();
  });

  await test.step("source chips show their age", async () => {
    await expect(page.locator(".chip").filter({ hasText: "Notarizing macOS" }).first()).toContainText(
      "retrieved today",
    );
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

  await test.step("the index can be searched from the viewer", async () => {
    await page.locator("#library-filter").fill("discovery");
    await page.getByRole("button", { name: /Search the index/ }).click();
    await expect(page.locator(".library-item.index-item")).toHaveCount(1);
  });

  await test.step("selecting pushes context the agent can read", async () => {
    await page.locator(".card.step").filter({ hasText: "notarytool" }).click();
    const selection = await page.request.get("/api/v1/selection");
    const body = await selection.json();
    expect(body.selection.step.id).toBe("notarize");
    expect(body.selection.playbook.id).toBe("@speccify/macos-notarize-tauri");
  });

  await test.step("an agent proposal shows as a diff and only applies on request", async () => {
    const current = await (
      await page.request.get("/api/v1/playbook", {
        params: { source: "@speccify/macos-notarize-tauri" },
      })
    ).json();
    const proposed = current.yaml.replace(
      "pitfalls:",
      "pitfalls:\n  - Proposed by an agent during the smoke test.",
    );
    const posted = await page.request.post("/api/v1/proposal", {
      data: {
        source: "@speccify/macos-notarize-tauri",
        playbook_yaml: proposed,
        rationale: "One more pitfall.",
      },
    });
    expect(posted.ok()).toBeTruthy();

    const panel = page.locator(".card.proposal");
    await expect(panel).toBeVisible({ timeout: 10_000 });
    await expect(panel.locator(".diff-line.added")).toContainText("Proposed by an agent");
    // The Apply button must be readable, not white on white (regression: two
    // CSS rules of equal specificity, primary lost to the generic one).
    const apply = panel.getByRole("button", { name: "Apply" });
    await expect(apply).toBeVisible();
    await expect(apply).toHaveCSS("background-color", "rgb(15, 118, 110)");
    await apply.click();
    await expect(panel).toBeHidden();
    await expect(page.locator(".pitfalls")).toContainText("Proposed by an agent");
  });

  await test.step("a delegated step links to its child playbook", async () => {
    // The filter is still narrowed from the index search — clear it first.
    await page.locator("#library-filter").fill("");
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await page.locator(".link").filter({ hasText: "apple-developer-id-cert" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/apple-developer-id-cert@1.0.0",
    );
  });
});
