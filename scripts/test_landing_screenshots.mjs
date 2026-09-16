import assert from "node:assert/strict";
import { chromium } from "playwright";
const url = process.env.MARKETING_URL ?? "http://127.0.0.1:4321";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(url).hostname), "Use a local preview, not production.");
const browser = await chromium.launch({ channel: process.env.SCREENSHOT_BROWSER === "chromium" ? undefined : "chrome" });
try {
  for (const route of ["/", "/features/"]) {
    for (const width of [1440, 390, 320]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 1 });
      page.setDefaultTimeout(10000);
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(`${url}${route}`);
      assert.equal(await page.locator("html").getAttribute("lang"), "en");
      await page.getByRole("navigation", { name: "Main navigation", exact: true }).getByRole("link", { name: "Features", exact: true }).waitFor();
      const shots = page.locator(".app-screenshot img");
      assert.equal(await shots.count(), route === "/" ? 2 : 9);
      if (route === "/features/") {
        assert.deepEqual(await page.locator("[data-feature]").evaluateAll(elements => elements.map(el => el.id)),
          ["skills", "tools", "specs", "workspaces", "playbooks", "agents", "actions", "editor", "git"]);
        for (const section of await page.locator("[data-feature]").all()) assert.equal(await section.locator(".app-screenshot").count(), 1);
        for (const link of await page.getByRole("navigation", { name: "Feature index" }).getByRole("link").all()) {
          const id = await link.getAttribute("href");
          assert.equal(await page.locator(id).count(), 1);
        }
      } else {
        assert.match(await shots.nth(1).getAttribute("alt"), /Skills/);
      }
      for (const img of await shots.all()) {
        await img.scrollIntoViewIfNeeded();
        await img.evaluate(el => el.decode());
        assert.ok((await img.getAttribute("alt")).length > 30);
        assert.ok((await img.getAttribute("srcset")).includes("640w") || (await img.getAttribute("srcset")).includes("768w"));
        assert.ok(await img.evaluate(el => el.naturalWidth > 0 && el.getAttribute("width") && el.getAttribute("height")));
        const source = await img.evaluate(el => el.currentSrc);
        assert.ok(source.includes(".webp"));
        const response = await page.request.get(source);
        assert.equal(response.status(), 200);
        assert.ok((await response.body()).length < 200_000, "Served image should stay below 200 kB");
      }
      assert.equal(await shots.first().getAttribute("loading"), "eager");
      assert.equal(await shots.nth(1).getAttribute("loading"), "lazy");
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route} ${width}: overflow`);
      await page.evaluate(() => window.scrollTo(0, 0));
      const bounds = await shots.first().boundingBox();
      if (route === "/") assert.ok(bounds.y < 820, `${route} ${width}: preview appears early`);
      const fullSize = page.locator(".app-screenshot-link").first();
      await fullSize.focus();
      assert.equal(await fullSize.evaluate(el => getComputedStyle(el).outlineStyle), "solid");
      const response = await page.request.get(new URL(await fullSize.getAttribute("href"), url).href);
      assert.equal(response.status(), 200);
      assert.ok(response.headers()["content-type"].startsWith("image/"));
      await page.locator("h1").click();
      const slug = route === "/" ? "landing" : "features";
      await page.screenshot({ path: `/private/tmp/speccify-${slug}-en-${width}.png`, fullPage: true });
      await page.screenshot({ path: `/private/tmp/speccify-${slug}-en-${width}-entry.png` });
      assert.deepEqual(errors, []);
      console.log(`PASS ${route} ${width}px: images, responsive sources, size budget, feature order, no overflow, keyboard/full-size link`);
      await page.close();
    }
  }
  const noJs = await browser.newPage({ javaScriptEnabled: false });
  await noJs.goto(`${url}/features/`);
  await noJs.getByRole("navigation", { name: "Feature index" }).getByRole("link", { name: /Tool contracts/ }).click();
  assert.ok(noJs.url().endsWith("#tools"));
  await noJs.locator(".app-screenshot img").first().waitFor();
  await noJs.locator(".app-screenshot-link").first().click();
  assert.ok(noJs.url().endsWith(".png"));
  console.log("PASS full-size image remains usable without JavaScript");
  const page = await browser.newPage();
  await page.goto(`${url}/de/`);
  await page.waitForURL(`${url}/`);
  assert.equal(await page.locator("html").getAttribute("lang"), "en");
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Features", exact: true }).click();
  await page.waitForURL(`${url}/features/`);
  assert.equal(await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Features", exact: true }).getAttribute("aria-current"), "page");
  for (const href of new Set(await page.locator("main a[href^='/']").evaluateAll(links => links.map(link => link.getAttribute("href"))))) {
    assert.equal((await page.request.get(new URL(href, url).href)).status(), 200, href);
  }
  console.log("PASS deferred DE landing, Features navigation and internal documentation links");
  for (const width of [1440, 320]) {
    const docs = await browser.newPage({ viewport: { width, height: 1000 } });
    for (const route of ["/app/workspaces/", "/releases/0-7-0/", "/releases/0-8-0/", "/releases/0-8-1/"]) {
      assert.equal((await docs.goto(`${url}${route}`)).status(), 200);
      await docs.getByRole("heading", { level: 1 }).waitFor();
      for (const img of await docs.locator("main img").all()) {
        await img.scrollIntoViewIfNeeded();
        await img.evaluate(el => el.decode());
      }
      assert.ok(await docs.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route} ${width}: overflow`);
    }
    await docs.route("https://api.github.com/repos/mhennemeyer/speccify/releases/latest", route => route.fulfill({
      json: { tag_name: "v0.7.0", published_at: "2026-09-15T10:00:00Z", html_url: "https://github.com/mhennemeyer/speccify/releases/tag/v0.7.0", assets: [
        "Speccify_0.7.0_aarch64.dmg", "Speccify_0.7.0_x64-setup.exe", "Speccify_0.7.0_x64_en-US.msi",
        "Speccify_0.7.0_amd64.AppImage", "Speccify_0.7.0_aarch64.AppImage", "Speccify_0.7.0_amd64.deb",
        "Speccify_0.7.0_arm64.deb", "Speccify-0.7.0-1.x86_64.rpm", "Speccify-0.7.0-1.aarch64.rpm",
      ].map(name => ({ name, size: 1000000, browser_download_url: `https://github.com/mhennemeyer/speccify/releases/download/v0.7.0/${name}` })) },
    }));
    await docs.goto(`${url}/download/`);
    await docs.locator('[data-platform="linux"] a').first().waitFor();
    const linuxLinks = await docs.locator('[data-platform="linux"] a').allTextContents();
    assert.equal(linuxLinks.length, 6);
    assert.equal(linuxLinks.filter(label => label.includes("arm64")).length, 3);
    assert.equal(linuxLinks.filter(label => label.includes("x86_64")).length, 3);
    assert.equal(await docs.locator('[data-platform="mac"] a').count(), 1);
    assert.equal(await docs.locator('[data-platform="windows"] a').count(), 2);
    await docs.getByText("Windows: SmartScreen warns on first launch", { exact: true }).waitFor();
    assert.equal(await docs.getByText("macOS downloads are signed and notarized.", { exact: true }).count()
      + await docs.getByText("Gatekeeper will complain on first launch", { exact: true }).count(), 1);
    assert.ok(await docs.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `download ${width}: overflow`);
    await docs.screenshot({ path: `/private/tmp/speccify-download-${width}.png`, fullPage: true });
    await docs.close();
  }
  console.log("PASS workspace/release docs and architecture-specific downloads at desktop/phone widths");
} finally { await browser.close(); }
