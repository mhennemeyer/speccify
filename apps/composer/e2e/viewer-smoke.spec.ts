// UI smoke for the skill viewer: list, open, click through steps, select a
// source and a bundled file. Selection is what a context-aware agent reads, so
// it is worth pinning.

import { expect, test } from "@playwright/test";

test("open a skill, walk its steps, select a source and a file", async ({ page }) => {
  await page.goto("/");

  await test.step("the library lists the shipped skills and filters", async () => {
    // `count()` does not auto-wait — make sure the list has loaded first.
    await expect(page.locator(".library-item").first()).toBeVisible();
    const all = await page.locator(".library-item").count();
    expect(all).toBeGreaterThanOrEqual(4);
    // "tauri" is a stack, not a keyword — the filter has to reach the axes.
    await page.locator("#library-filter").fill("tauri");
    await expect(page.locator(".library-item")).toHaveCount(1);
    // ...and the axes are visible, so a human can see *why* it matched.
    await expect(page.locator(".library-item .axis").filter({ hasText: "tauri" })).toBeVisible();
    await page.locator("#library-filter").fill("");
    await expect(page.locator(".library-item")).toHaveCount(all);
  });

  await test.step("opening shows the skill and what it builds on", async () => {
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/macos-notarize-tauri@1.0.0",
    );
    // The description is what an agent sees before loading the skill.
    await expect(page.locator(".card").first()).toContainText("Gatekeeper");
    await expect(page.locator(".card").first()).toContainText("builds on");
  });

  await test.step("the workflow diagram mirrors the inferred steps", async () => {
    await expect(page.locator(".step-flow .flow-node")).toHaveCount(5);
    await page.locator(".step-flow .flow-node").nth(3).click();
    await expect(page.locator(".steps .chip").filter({ hasText: "notarytool" })).toHaveClass(
      /selected/,
    );
  });

  await test.step("the markdown is rendered as markdown, not as raw text", async () => {
    const body = page.locator(".markdown").first();
    // Fenced blocks become real <pre><code> — somewhere in the document, not
    // necessarily first; the order is the skill author's business.
    await expect(body.locator("pre code").filter({ hasText: "notarytool submit" })).toHaveCount(1);
    // Prose is prose. `.detail` is monospace because it also renders raw file
    // content; when markdown is rendered into it, the font has to come back —
    // the same specificity trap that once made the Apply button invisible.
    const proseFont = await body
      .locator("p")
      .first()
      .evaluate((node) => getComputedStyle(node).fontFamily);
    expect(proseFont).not.toMatch(/mono/i);
    const codeFont = await body
      .locator("pre code")
      .first()
      .evaluate((node) => getComputedStyle(node).fontFamily);
    expect(codeFont).toMatch(/mono/i);
  });

  await test.step("source chips show their age", async () => {
    // Not "retrieved today" — that assertion only held on the day the skill was
    // written and went red the morning after. What matters is that an age is
    // shown at all, and that a fresh source is not flagged as stale.
    const chip = page.locator(".chip").filter({ hasText: "Notarizing macOS" }).first();
    await expect(chip).toContainText(/retrieved today|day[s]? old|months old/);
    await expect(chip).not.toHaveClass(/stale/);
    await chip.click();
    await expect(chip).toHaveClass(/selected/);
  });

  await test.step("a bundled file shows its content", async () => {
    await page.locator(".chip").filter({ hasText: "reference.sh" }).first().click();
    await expect(page.locator(".asset-view pre")).toContainText("codesign --verify");
  });

  await test.step("the index can be searched from the viewer", async () => {
    await page.locator("#library-filter").fill("discovery");
    await page.getByRole("button", { name: /Search the index/ }).click();
    await expect(page.locator(".library-item.index-item")).toHaveCount(1);
  });

  await test.step("selecting pushes context the agent can read", async () => {
    await page.locator("#library-filter").fill("");
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await page.locator(".steps .chip").filter({ hasText: "notarytool" }).click();

    const selection = await page.request.get("/api/v1/selection");
    const body = await selection.json();
    expect(body.selection.skill.id).toBe("@speccify/macos-notarize-tauri");
    expect(body.selection.step.title).toContain("notarytool");
    // Resolved, not just an identifier: the agent gets the text of the step.
    expect(body.selection.step.body).toContain("notarytool submit");
  });

  await test.step("an agent proposal shows as a diff and only applies on request", async () => {
    const current = await (
      await page.request.get("/api/v1/skill", {
        params: { source: "@speccify/macos-notarize-tauri" },
      })
    ).json();
    const proposed = current.raw.replace(
      "## Pitfalls\n",
      "## Pitfalls\n\n- Proposed by an agent during the smoke test.\n",
    );
    expect(proposed).not.toBe(current.raw);

    const posted = await page.request.post("/api/v1/proposal", {
      data: {
        source: "@speccify/macos-notarize-tauri",
        skill_markdown: proposed,
        rationale: "One more pitfall.",
      },
    });
    expect(posted.ok()).toBeTruthy();

    const panel = page.locator(".card.proposal");
    await expect(panel).toBeVisible({ timeout: 10_000 });
    await expect(
      panel.locator(".diff-line.added").filter({ hasText: "Proposed by an agent" }),
    ).toHaveCount(1);
    // The Apply button must be readable, not white on white (regression: two
    // CSS rules of equal specificity, primary lost to the generic one).
    const apply = panel.getByRole("button", { name: "Apply" });
    await expect(apply).toBeVisible();
    await expect(apply).toHaveCSS("background-color", "rgb(15, 118, 110)");
    await apply.click();
    await expect(panel).toBeHidden();
    await expect(page.locator(".markdown").first()).toContainText("Proposed by an agent");
  });

  await test.step("a skill links to the one it builds on", async () => {
    await page.locator("#library-filter").fill("");
    await page.locator(".library-item").filter({ hasText: "notarize" }).click();
    await page.locator(".link").filter({ hasText: "apple-developer-id-cert" }).click();
    await expect(page.locator(".topbar .badge.accent")).toContainText(
      "@speccify/apple-developer-id-cert@1.0.0",
    );
  });
});
