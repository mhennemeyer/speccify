import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const base = process.env.SPECCIFY_MOCK_URL ?? 'http://127.0.0.1:1421/dev/mock.html';
assert.ok(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const server = process.argv.includes('--serve') ? spawn(process.execPath, [
  fileURLToPath(new URL('../apps/desktop/node_modules/vite/bin/vite.js', import.meta.url)),
  '--host', '127.0.0.1', '--port', new URL(base).port, '--strictPort',
], {cwd:fileURLToPath(new URL('../apps/desktop', import.meta.url)), stdio:'ignore'}) : null;
let browser;
try {
  if (server) {
    let ready = false;
    for (let attempt=0;attempt<100;attempt++) {
      if (server.exitCode !== null) throw Error(`Test server exited: ${server.exitCode}`);
      try { ready=(await fetch(base)).ok; } catch { /* Starting. */ }
      if (ready) break;
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    assert.ok(ready, 'Test server did not start');
  }
  browser = await chromium.launch({channel:process.env.SPECCIFY_TEST_BROWSER ?? 'chrome'});
  const page = await browser.newPage();
  await page.goto(`${base}?dashboard=1&updates=1`);
  await page.locator('[data-update-ui]').waitFor({state:'attached'});
  await page.evaluate(()=>window.dispatchEvent(new Event('speccify:updates')));
  const dialog=page.getByRole('dialog',{name:'Speccify-Updates'});
  await dialog.waitFor();
  await dialog.getByLabel('Automatisch nach Updates suchen').click();
  await page.waitForFunction(()=>!window.__SPECCIFY_MOCK__.update.preferences.automatic);
  await page.waitForFunction(()=>!document.querySelector('[data-update-ui] input').checked);
  await dialog.getByLabel('Update-Suchintervall').selectOption('6');
  await page.reload();
  await page.locator('[data-update-ui]').waitFor({state:'attached'});
  await page.evaluate(()=>window.dispatchEvent(new Event('speccify:updates')));
  await dialog.waitFor();
  assert.equal(await dialog.getByLabel('Automatisch nach Updates suchen').isChecked(),false);
  assert.equal(await dialog.getByLabel('Update-Suchintervall').inputValue(),'6');
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.updateOffline=true;});
  await dialog.getByRole('button',{name:'Jetzt suchen'}).click();
  await dialog.getByRole('alert').filter({hasText:'offline'}).waitFor();
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.updateOffline=false;});
  await dialog.getByRole('button',{name:'Jetzt suchen'}).click();
  await dialog.getByRole('button',{name:'Update herunterladen'}).waitFor();
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.updateInstalls),0);
  await dialog.getByRole('button',{name:'Update herunterladen'}).click();
  await dialog.getByLabel('Update-Download').waitFor();
  await dialog.getByRole('button',{name:'Download abbrechen'}).click();
  await dialog.getByRole('button',{name:'Update herunterladen'}).click();
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.finishUpdateDownload(false));
  await dialog.getByRole('alert').filter({hasText:'Invalid signature'}).waitFor();
  assert.equal(await dialog.getByRole('button',{name:'Installieren und neu starten'}).count(),0);
  await dialog.getByRole('button',{name:'Update herunterladen'}).click();
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.finishUpdateDownload());
  const install=dialog.getByRole('button',{name:'Installieren und neu starten'});
  await install.waitFor();
  await page.evaluate(()=>{ const editor=document.createElement('textarea');editor.id='test-editor';editor.value='Unsaved work';document.body.append(editor); });
  await install.click();
  await dialog.getByRole('alert').filter({hasText:'Editoransichten'}).waitFor();
  assert.equal(await page.locator('#test-editor').inputValue(),'Unsaved work');
  assert.equal(await page.evaluate(()=>document.documentElement.inert),false);
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.updateInstalls),0);
  await page.locator('#test-editor').evaluate(el=>el.remove());
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.updateProcessRunning=true;});
  await install.click();
  await dialog.getByRole('alert').filter({hasText:'Terminals'}).waitFor();
  // A blocked install must explain itself without scrolling (058).
  const viewport = page.viewportSize();
  await page.setViewportSize({width:900,height:420});
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.update.notes='# Notes\n\n'+Array.from({length:40},(_,i)=>`- Item ${i+1}`).join('\n');});
  await dialog.getByText('Item 40').waitFor({state:'attached'});
  await install.click();
  const alert = dialog.getByRole('alert').filter({hasText:'Terminals'});
  await alert.waitFor();
  // Wherever the dialog content is scrolled to, the message stays in view.
  await dialog.evaluate(el=>{ for (const node of [el,...el.querySelectorAll('*')]) node.scrollTop=0; });
  const box = await alert.boundingBox();
  const frame = await dialog.boundingBox();
  assert.ok(box && frame && box.y >= frame.y && box.y + box.height <= Math.min(420, frame.y + frame.height),
    `Install error outside the visible dialog: ${JSON.stringify({box,frame})}`);
  await page.setViewportSize(viewport);
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.updateProcessRunning=false;});
  await install.click();
  await page.waitForFunction(()=>window.__SPECCIFY_MOCK__.updateInstalls===1);
  assert.equal(await page.evaluate(()=>document.documentElement.inert),false);
  console.log('PASS updates: preference persistence, offline/retry, explicit download, progress/cancel, invalid signature, editor/process guard, explicit install');
} finally {await browser?.close(); server?.kill();}
