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
      assert.equal(await shots.count(), route === "/" ? 2 : 8);
      if (route === "/features/") {
        assert.deepEqual(await page.locator("[data-feature]").evaluateAll(elements => elements.map(el => el.id)),
          ["skills", "tools", "specs", "playbooks", "agents", "actions", "editor", "git"]);
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
} finally { await browser.close(); }
