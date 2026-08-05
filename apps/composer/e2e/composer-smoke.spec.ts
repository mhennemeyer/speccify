// UI-Smoke des Composers: derselbe Flow wie der Headless-Agent-E2E
// (apps/web/backend/tests/test_composer_agent_flow.py), aber durch die
// echte Oberfläche — Palette → Composite anlegen → Kind + Prop → eigenes
// Event + Wiring-Regel → Simulation → validieren → speichern → Round-Trip.

import { expect, test } from "@playwright/test";

test("Composite komponieren, verdrahten, speichern und per YAML runden", async ({ page }) => {
  await page.goto("/");

  await test.step("Palette lädt Registry-Specs", async () => {
    await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();
  });

  await test.step("Neue Composite anlegen", async () => {
    await page.locator("#new-name").fill("smoke-widget");
    await page.getByRole("button", { name: "Anlegen" }).click();
    await expect(page.locator(".topbar .badge.accent")).toHaveText(
      "@org/smoke-widget@0.1.0 · ui-component",
    );
  });

  await test.step("Button als Kind hinzufügen und Prop setzen", async () => {
    await page
      .locator(".palette-item")
      .filter({ hasText: "@org/button@" })
      .getByRole("button", { name: "+ als Kind" })
      .click();
    const node = page.locator(".mock-node").filter({ hasText: "button" });
    await expect(node).toBeVisible();
    // Der Canvas rendert den generierten Mock: die Prop steht dort so, wie die
    // Mock-Komponente sie darstellt (kein JSON-Echo des Composers mehr).
    await expect(node.locator("[data-speccify-mock='@org/button']")).toBeVisible();
    // Knoten ist nach dem Hinzufügen selektiert — Inspector zeigt den Prop-Editor.
    await page.locator("#tree-prop-label").fill("Klick mich");
    await expect(node).toContainText("Klick mich");
  });

  await test.step("Eigenes Event anlegen und verdrahten", async () => {
    await page.getByRole("button", { name: "API", exact: true }).click();
    await page.locator("#own-event-name").fill("clicked");
    await page.getByRole("button", { name: "Event speichern" }).click();

    await page.getByRole("button", { name: "Verdrahtung" }).click();
    await page.locator("#wiring-when").selectOption("button.pressed");
    await page.locator("#wiring-emit").selectOption("clicked");
    await page.getByRole("button", { name: "Regel hinzufügen" }).click();
    await expect(page.locator(".rule").filter({ hasText: "wenn button.pressed" })).toBeVisible();
  });

  await test.step("Simulation: Event-Chip des Mocks feuert die Wiring-Regel", async () => {
    // Der Chip kommt aus dem generierten Mock, nicht aus dem Composer.
    await page.locator(".mock-node button").filter({ hasText: "pressed" }).first().click();
    await expect(page.locator(".log-entry").filter({ hasText: "button.pressed" })).toBeVisible();
    await expect(page.locator(".log-entry").filter({ hasText: "emittiert clicked" })).toBeVisible();
  });

  await test.step("Validieren und speichern", async () => {
    await page.getByRole("button", { name: "Validieren" }).click();
    await expect(page.locator(".ok")).toHaveText("✓ Schema + Komposition sauber.");

    await page.getByRole("button", { name: "Speichern" }).click();
    await expect(page.locator(".topbar")).toContainText("Gespeichert: @org/smoke-widget@0.1.0");
    // Gespeichertes ist sofort Palette-Baustein (rekursive Komposition).
    await expect(
      page.locator(".palette-item").filter({ hasText: "@org/smoke-widget@0.1.0" }),
    ).toBeVisible();
  });

  await test.step("YAML-Round-Trip: Version im YAML editieren und übernehmen", async () => {
    const yamlArea = page.locator("textarea.yaml");
    const yaml = await yamlArea.inputValue();
    expect(yaml).toContain("composition:");
    await yamlArea.fill(yaml.replace("version: 0.1.0", "version: 0.2.0"));
    await page.getByRole("button", { name: "übernehmen" }).click();
    await expect(page.locator(".topbar .badge.accent")).toHaveText(
      "@org/smoke-widget@0.2.0 · ui-component",
    );
  });
});

test("Discovery: Spec aus dem Index-Repo als Kind einfügen", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();

  await page.locator("#new-name").fill("index-widget");
  await page.getByRole("button", { name: "Anlegen" }).click();

  await test.step("Index durchsuchen", async () => {
    await page.locator("#index-query").fill("discovery");
    await page.getByRole("button", { name: "Suchen" }).click();
    await expect(page.locator(".index-item")).toHaveCount(1);
    await expect(page.locator(".index-item .meta")).toContainText("git+file://");
  });

  await test.step("Git-Quelle als Kind — Canvas rendert ihren echten Mock", async () => {
    await page.locator(".index-item").getByRole("button", { name: "+ als Kind" }).click();
    const node = page.locator(".mock-node").filter({ hasText: "button" });
    await expect(node).toBeVisible();
    await expect(node.locator("[data-speccify-mock='@org/button']")).toBeVisible();
    // In `uses` steht die Git-Quelle (YAML faltet lange Werte um), der Knoten
    // heißt nach der deklarierten Id.
    await expect(page.locator("textarea.yaml")).toHaveValue(
      /git\+file:\/\/[\s\S]*button-repo@\^0\.1/,
    );
    await expect(page.locator("textarea.yaml")).toHaveValue(/- node: button/);
  });

  await test.step("Validierung löst die Git-Quelle auf", async () => {
    await page.getByRole("button", { name: "Validieren" }).click();
    await expect(page.locator(".ok")).toHaveText("✓ Schema + Komposition sauber.");
  });
});

test("Vorschau rendert den Dokument-Mock mit eigener Verdrahtung", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();

  await page.locator("#new-name").fill("preview-widget");
  await page.getByRole("button", { name: "Anlegen" }).click();
  await page
    .locator(".palette-item")
    .filter({ hasText: "@org/button@" })
    .getByRole("button", { name: "+ als Kind" })
    .click();

  // Eigenes Event + Wiring-Regel: button.pressed → clicked.
  await page.getByRole("button", { name: "API", exact: true }).click();
  await page.locator("#own-event-name").fill("clicked");
  await page.getByRole("button", { name: "Event speichern" }).click();
  await page.getByRole("button", { name: "Verdrahtung" }).click();
  await page.locator("#wiring-when").selectOption("button.pressed");
  await page.locator("#wiring-emit").selectOption("clicked");
  await page.getByRole("button", { name: "Regel hinzufügen" }).click();

  await page.getByRole("button", { name: "Vorschau" }).click();
  // Gerendert wird der generierte Composite-Mock des Dokuments selbst.
  const preview = page.locator(".preview-pane [data-speccify-mock='@org/preview-widget']");
  await expect(preview).toBeVisible();
  await expect(preview).toContainText("mock · composite");

  // Die Verdrahtung läuft im generierten Code — der Callback landet im Log.
  await preview.locator("button").filter({ hasText: "pressed" }).first().click();
  await expect(page.locator(".log-entry").filter({ hasText: "emittiert clicked" })).toBeVisible();
});

test("Undo/Redo rollt Kind-Hinzufügen als einen Schritt zurück und vor", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();

  await page.locator("#new-name").fill("undo-widget");
  await page.getByRole("button", { name: "Anlegen" }).click();
  await page
    .locator(".palette-item")
    .filter({ hasText: "@org/button@" })
    .getByRole("button", { name: "+ als Kind" })
    .click();
  const node = page.locator(".mock-node").filter({ hasText: "button" });
  await expect(node).toBeVisible();

  await page.getByRole("button", { name: "Rückgängig" }).click();
  await expect(node).toHaveCount(0);

  await page.getByRole("button", { name: "Wiederholen" }).click();
  await expect(node).toBeVisible();

  // Zweites Undo bis vor „Anlegen": keine Spec mehr geöffnet.
  await page.getByRole("button", { name: "Rückgängig" }).click();
  await page.getByRole("button", { name: "Rückgängig" }).click();
  await expect(page.locator(".topbar")).toContainText("keine Spec geöffnet");
});

test("Drag & Drop: aus der Palette in den Canvas und in eine Slot-Zone, Knoten umhängen", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();

  await page.locator("#new-name").fill("dnd-widget");
  await page.getByRole("button", { name: "Anlegen" }).click();

  // Palette → Canvas-Hintergrund: neuer Top-Level-Knoten.
  await page
    .locator(".palette-item")
    .filter({ hasText: "@org/button@" })
    .dragTo(page.locator(".canvas"));
  const button = page.locator(".mock-node").filter({ hasText: "@org/button@" });
  await expect(button).toBeVisible();

  // Palette → Slot-Zone: der Knoten landet im Slot, nicht auf Top-Level.
  const slotZone = page.locator(".slot-zone").filter({ hasText: "icon_leading" });
  await page.locator(".palette-item").filter({ hasText: "@org/text-input@" }).dragTo(slotZone);
  const nested = page.locator(".slot-zone .mock-node").filter({ hasText: "text_input" });
  await expect(nested).toBeVisible();
  await expect(page.locator("textarea.yaml")).toHaveValue(/icon_leading/);

  // Knoten am Griff zurück auf den Canvas ziehen → wieder Top-Level.
  await nested.locator(".head").dragTo(page.locator(".canvas-bar"));
  await expect(page.locator(".slot-zone .mock-node")).toHaveCount(0);
  await expect(page.locator("#node-placement")).toHaveValue("");
});

test("Slot-Befüllen: Kind in Slot-Zone einfügen und wieder auf Top-Level ziehen", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".palette-item").filter({ hasText: "@org/button@" })).toBeVisible();

  await page.locator("#new-name").fill("slot-widget");
  await page.getByRole("button", { name: "Anlegen" }).click();
  await page
    .locator(".palette-item")
    .filter({ hasText: "@org/button@" })
    .getByRole("button", { name: "+ als Kind" })
    .click();

  // Slot-Zone des Buttons als Einfüge-Ziel aktivieren.
  const slotZone = page.locator(".slot-zone").filter({ hasText: "icon_leading" });
  await slotZone.click();
  await expect(slotZone).toHaveClass(/target/);

  // text-input landet im Slot, nicht auf Top-Level.
  await page
    .locator(".palette-item")
    .filter({ hasText: "@org/text-input@" })
    .getByRole("button", { name: "+ als Kind" })
    .click();
  await expect(page.locator(".slot-zone .mock-node").filter({ hasText: "text_input" })).toBeVisible();
  await expect(page.locator("textarea.yaml")).toHaveValue(/icon_leading/);

  // Platzierung im Inspector zurück auf Top-Level.
  await expect(page.locator("#node-placement")).toHaveValue("button.icon_leading");
  await page.locator("#node-placement").selectOption("");
  await expect(page.locator(".slot-zone .mock-node")).toHaveCount(0);
  await expect(page.locator(".mock-node").filter({ hasText: "@org/text-input@" })).toBeVisible();
});
