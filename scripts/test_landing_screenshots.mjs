import assert from "node:assert/strict";
import { chromium } from "playwright";
const url = process.env.MARKETING_URL ?? "http://127.0.0.1:4321";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(url).hostname), "Use a local preview, not production.");
const browser = await chromium.launch({ channel: process.env.SCREENSHOT_BROWSER === "chromium" ? undefined : "chrome" });
try {
  for (const lang of ["en", "de"]) {
    for (const width of [1440, 390, 320]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 1 });
      page.setDefaultTimeout(10000);
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(`${url}${lang === "de" ? "/de/" : "/"}`);
      assert.equal(await page.locator("html").getAttribute("lang"), lang);
      const shots = page.locator(".app-screenshot img");
      assert.equal(await shots.count(), 2);
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
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${lang} ${width}: overflow`);
      await page.evaluate(() => window.scrollTo(0, 0));
      const bounds = await shots.first().boundingBox();
      assert.ok(bounds.y < 780, `${lang} ${width}: preview appears early`);
      const fullSize = page.locator(".app-screenshot-link").first();
      await fullSize.focus();
      assert.equal(await fullSize.evaluate(el => getComputedStyle(el).outlineStyle), "solid");
      const response = await page.request.get(new URL(await fullSize.getAttribute("href"), url).href);
      assert.equal(response.status(), 200);
      assert.ok(response.headers()["content-type"].startsWith("image/"));
      await page.locator("h1").click();
      await page.screenshot({ path: `/private/tmp/speccify-landing-${lang}-${width}.png`, fullPage: true });
      await page.screenshot({ path: `/private/tmp/speccify-landing-${lang}-${width}-entry.png` });
      assert.deepEqual(errors, []);
      console.log(`PASS ${lang} ${width}px: images, responsive sources, size budget, early placement, no overflow, keyboard/full-size link`);
      await page.close();
    }
  }
  const noJs = await browser.newPage({ javaScriptEnabled: false });
  await noJs.goto(`${url}/de/`);
  await noJs.locator(".app-screenshot img").first().waitFor();
  await noJs.locator(".app-screenshot-link").first().click();
  assert.ok(noJs.url().endsWith(".png"));
  console.log("PASS full-size image remains usable without JavaScript");
} finally { await browser.close(); }
