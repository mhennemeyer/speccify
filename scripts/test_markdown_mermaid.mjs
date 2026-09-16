import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const base = process.env.SPECCIFY_MOCK_URL ?? "http://127.0.0.1:1421/dev/mock.html";
assert.ok(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const fence = source => `\n\n\`\`\`mermaid\n${source}\n\`\`\`\n`;
const document = "# Diagrams\n\nOrdinary **Markdown**.\n\n```text\nkeep this code\n```"
  + fence('flowchart LR\n subgraph IN["Inputs"]\n A[("Snapshot<br/>Test data")]\n end\n A --> B["Output · Comparison"]')
  + fence('sequenceDiagram\n participant A as Alice\n participant B as Bob\n A->>B: Hello')
  + fence('this is not a diagram')
  + fence('flowchart LR\n A["Safe"] --> B["Result"]\n click A call evil()');
const server = process.argv.includes("--serve") ? spawn(process.execPath, [
  fileURLToPath(new URL("../apps/desktop/node_modules/vite/bin/vite.js", import.meta.url)),
  "--host", "127.0.0.1", "--port", new URL(base).port, "--strictPort",
], { cwd: fileURLToPath(new URL("../apps/desktop", import.meta.url)), stdio: "ignore" }) : null;
let browser;
try {
  if (server) {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (server.exitCode !== null) throw Error(`Test server exited: ${server.exitCode}`);
      try { ready = (await fetch(base)).ok; } catch { /* Server is starting. */ }
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(ready, "Test server did not start");
  }
  browser = await chromium.launch({ channel: process.env.SPECCIFY_TEST_BROWSER ?? "chrome" });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  const remote = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    if (["127.0.0.1", "localhost"].includes(url.hostname)) return route.continue();
    remote.push(url.origin); return route.abort();
  });
  await page.addInitScript(content => {
    localStorage.setItem("speccify.test.playbookFiles", JSON.stringify({
      ".agent/playbooks/diagrams.md": content,
      ".agent/playbooks/plain.md": "# Plain\n\nNo diagram here.",
    }));
    window.evil = () => { window.callbackExecuted = true; };
  }, document);
  await page.goto(`${base}?playbook-drafts=1`);
  await page.getByRole("tab", { name: "Orga", exact: true }).click();
  await page.getByRole("tab", { name: "Playbooks", exact: true }).click();
  await page.getByRole("button", { name: /^Diagrams/ }).click();
  const diagrams = page.locator(".mermaid-diagram");
  await diagrams.nth(3).locator("svg").waitFor();
  assert.equal(await diagrams.count(), 4);
  assert.equal(await diagrams.locator("svg").count(), 3);
  assert.match(await diagrams.first().locator('svg').textContent(), /Snapshot/);
  assert.match(await diagrams.nth(1).locator('svg').textContent(), /Alice/);
  assert.equal(await diagrams.nth(2).locator("details").getAttribute("open"), "");
  assert.match(await diagrams.nth(2).innerText(), /konnte nicht dargestellt/);
  assert.equal(await page.locator(".markdown-body pre > code.language-text").innerText(), "keep this code\n");
  assert.equal(await diagrams.locator("script, foreignObject, a, image").count(), 0);
  await diagrams.nth(3).getByText("Safe", { exact: true }).click();
  assert.equal(await page.evaluate(() => !!window.callbackExecuted), false);
  const before = await diagrams.first().locator("svg").getAttribute("id");
  await page.evaluate(() => { document.documentElement.dataset.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; });
  await page.waitForFunction(id => {
    const svg = document.querySelector('.mermaid-diagram svg');
    return svg && svg.id !== id;
  }, before);
  await diagrams.nth(3).locator("svg").waitFor();
  const ids = await diagrams.locator("svg").evaluateAll(nodes => nodes.map(n => n.id));
  assert.equal(new Set(ids).size, ids.length);
  // Unmount while queued rendering is possible, then reselect the document.
  await page.getByRole("button", { name: /^Plain/ }).click();
  await page.getByText("No diagram here.", { exact: true }).waitFor();
  assert.equal(await diagrams.count(), 0);
  await page.getByRole("button", { name: /^Diagrams/ }).click();
  await diagrams.nth(3).locator("svg").waitFor();
  // An optional local reproduction stays outside committed fixtures and external services.
  if (process.env.SPECCIFY_MERMAID_DOCUMENT) {
    const content = await readFile(process.env.SPECCIFY_MERMAID_DOCUMENT, "utf8");
    await page.getByRole("button", { name: /^Plain/ }).click();
    await page.evaluate(content => { window.__SPECCIFY_MOCK__.playbookFiles['.agent/playbooks/diagrams.md'] = content; }, content);
    await page.getByRole("button", { name: /^Diagrams/ }).click();
    const count = [...content.matchAll(/^```mermaid\r?$/gm)].length;
    await page.waitForFunction(count => document.querySelectorAll('.mermaid-diagram svg').length === count, count);
    assert.equal(await diagrams.locator('.mermaid-error').count(), 0);
    const box = await diagrams.first().locator('svg').boundingBox();
    assert.ok(box.width > 300 && box.height > 100);
    console.log(`PASS local reproduction: ${count} diagram(s)`);
  }
  assert.deepEqual(remote, []);
  assert.deepEqual(errors, []);
  console.log("PASS Mermaid: flowchart, sequence, syntax fallback, theme, navigation, isolated IDs, no callbacks or remote requests; normal code unchanged");
} finally { await browser?.close(); server?.kill(); }
