import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const url = 'http://127.0.0.1:1421/dev/mock.html?terminaltest=1';
const server = spawn(process.execPath, [fileURLToPath(new URL('../apps/desktop/node_modules/vite/bin/vite.js', import.meta.url)), '--host','127.0.0.1','--port','1421','--strictPort'], {cwd:fileURLToPath(new URL('../apps/desktop',import.meta.url)),stdio:'ignore'});
let browser;
try {
  for(let i=0;i<100;i++) {
    if(server.exitCode!==null) throw Error('Test server exited');
    try { if((await fetch(url)).ok) break; } catch {}
    await new Promise(r=>setTimeout(r,100));
  }
  browser=await chromium.launch({channel:process.env.SPECCIFY_TEST_BROWSER??'chrome'});
  const page=await browser.newPage({viewport:{width:1100,height:800}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);
  await page.waitForFunction(()=>window.__speccifyQa?.terminalReady());
  const appearance=()=>page.evaluate(()=>window.__speccifyQa.terminalAppearance());
  assert.equal((await appearance()).background,'#ffffff');
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.emit('term-out',{id:window.__SPECCIFY_MOCK__.terminalOpens[0].id,data:'Grüße aus dem Terminal\r\n\x1b[31mRot\x1b[0m\r\n'}));
  await page.waitForFunction(()=>window.__speccifyQa.terminalText().includes('Grüße'));
  const old=await appearance();
  await page.getByLabel('Terminal-Schriftgröße',{exact:true}).selectOption('24');
  await page.waitForFunction(()=>window.__speccifyQa.terminalAppearance().fontSize===24);
  await page.waitForFunction(cols=>window.__speccifyQa.terminalAppearance().cols<cols,old.cols);
  assert.ok((await appearance()).cols<old.cols);
  assert.ok(await page.evaluate(()=>window.__speccifyQa.terminalText().includes('Grüße')));
  await page.evaluate(()=>document.documentElement.dataset.theme='dark');
  await page.waitForFunction(()=>window.__speccifyQa.terminalAppearance().background==='#0f172a');
  await page.evaluate(()=>document.documentElement.dataset.theme='light');
  await page.waitForFunction(()=>window.__speccifyQa.terminalAppearance().background==='#ffffff');
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalOpens.length),1,'Appearance must not restart PTY');
  assert.ok(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalResizes.some(r=>r.cols===window.__speccifyQa.terminalAppearance().cols)));
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.emit('terminal-preferences',{font_size:18,popups:true,system_notifications:true}));
  await page.waitForFunction(()=>window.__speccifyQa.terminalAppearance().fontSize===18);
  await page.getByLabel('Terminal-Schriftgröße',{exact:true}).selectOption('32');
  assert.equal(await page.getByLabel('Terminal-Schrift vergrößern').isDisabled(),true);
  await page.reload();
  await page.waitForFunction(()=>window.__speccifyQa?.terminalReady() && window.__speccifyQa.terminalAppearance().fontSize===32);
  await page.getByLabel('Terminal-Schriftgröße',{exact:true}).selectOption('8');
  assert.equal(await page.getByLabel('Terminal-Schrift verkleinern').isDisabled(),true);
  await page.getByRole('button',{name:'Terminal umschalten'}).click();
  const output = data => page.evaluate(data => window.__SPECCIFY_MOCK__.emit('term-out',{
    id:window.__SPECCIFY_MOCK__.terminalOpens[0].id,data}),data);
  await output('\x1b[2J\x1b[HWould you like to run the following com');
  await output('mand?\r\n\x1b[32m1. Yes\x1b[0m\r\n2. No\r\n');
  const notice=page.getByRole('alert',{name:'Terminal braucht Aufmerksamkeit'});
  await notice.waitFor({state:'visible'});
  assert.equal(await page.getByTestId('terminal-pane').isVisible(),false,'Popup escapes hidden pane');
  assert.match(await notice.innerText(),/\/test\/project/);
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalAttention.length),1);
  await notice.getByRole('button',{name:'Schließen',exact:true}).click();
  await output('\x1b[2J\x1b[HWould you like to run the following command?\r\n1. Yes\r\n2. No\r\n');
  await page.waitForTimeout(650);
  assert.equal(await notice.count(),0,'Redraw must not repeat dismissed question');
  await output('\x1b]9;Approval needed\x07');
  await notice.waitFor({state:'visible'});
  await notice.getByRole('button',{name:'Zum Terminal'}).click();
  assert.equal(await page.getByTestId('terminal-pane').isVisible(),true);
  assert.deepEqual(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalWrites),[],'Attention never answers or approves');
  await page.getByLabel('Systemmeldungen bei inaktivem Fenster').uncheck();
  const notifications=await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalAttention.length);
  await page.waitForTimeout(2100);
  await output('\x1b[2J\x1b[HBefehl echo test zulassen?\r\n');
  await notice.waitFor({state:'visible'});
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalAttention.length),notifications);
  await page.getByLabel('Rückfragen als Popup anzeigen').uncheck();
  assert.equal(await notice.count(),0);
  await page.getByLabel('Rückfragen als Popup anzeigen').check();
  await notice.getByRole('button',{name:'Schließen',exact:true}).click();
  await page.locator('.xterm-helper-textarea').press('a');
  await output('\x1b]9;Approval needed\x07');
  await notice.waitFor({state:'visible'});
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalAttention.length),notifications,'System notifications remain off');
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.emit('term-exit',{id:window.__SPECCIFY_MOCK__.terminalOpens[0].id,data:''}));
  await page.waitForFunction(()=>!document.querySelector('[aria-label="Terminal braucht Aufmerksamkeit"]'));
  // Real browser key events must emit one distinct sequence, never a trailing CR.
  await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalWrites.length=0);
  const input=page.locator('.xterm-helper-textarea');
  await input.press('Shift+Enter');
  await input.press('Enter');
  await input.press('Alt+Enter');
  await input.press('Control+c');
  assert.deepEqual(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalWrites.map(w=>w.data)),['\x1b[13;2u','\r','\x1b\r','\x03']);
  // Spec 068: ⌘C kopiert die xterm-Auswahl über das Clipboard-Plugin, sendet kein ^C
  // und schließt das Tastenereignis ab (kein Fehlerton) — auch mit Fokus außerhalb.
  await output('\r\nKOPIERTEST 068\r\n');
  await page.waitForFunction(()=>window.__speccifyQa.terminalText().includes('KOPIERTEST 068'));
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.terminalWrites.length=0; window.__SPECCIFY_MOCK__.clipboard=[];});
  assert.ok(await page.evaluate(()=>window.__speccifyQa.terminalSelect('KOPIERTEST 068')));
  const prevented=await page.evaluate(()=>new Promise(resolve=>{
    window.addEventListener('keydown',e=>{ if(e.key==='c') setTimeout(()=>resolve(e.defaultPrevented),0); },{once:true});
    document.querySelector('.xterm-helper-textarea').dispatchEvent(new KeyboardEvent('keydown',{key:'c',code:'KeyC',metaKey:true,bubbles:true,cancelable:true}));
  }));
  assert.equal(prevented,true,'⌘C with a selection must be marked handled');
  await page.waitForFunction(()=>window.__SPECCIFY_MOCK__.clipboard.at(-1)==='KOPIERTEST 068');
  await page.getByRole('status',{name:'Zwischenablage'}).waitFor({state:'visible'});
  assert.deepEqual(await page.evaluate(()=>window.__SPECCIFY_MOCK__.terminalWrites),[],'⌘C with selection never sends ^C');
  await page.evaluate(()=>{window.__SPECCIFY_MOCK__.clipboard.length=0; document.body.focus();});
  await page.keyboard.press('Meta+c');
  await page.waitForFunction(()=>window.__SPECCIFY_MOCK__.clipboard.at(-1)==='KOPIERTEST 068');
  await page.evaluate(()=>{window.__speccifyQa.terminalClearSelection(); window.__SPECCIFY_MOCK__.clipboard.length=0;});
  await input.press('Meta+c');
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>window.__SPECCIFY_MOCK__.clipboard.length),0,'no selection: ⌘C stays with the terminal');
  assert.deepEqual(errors,[]);
  console.log('PASS terminal: themes, font/PTY resize, persistence, hidden-pane prompt, split/ANSI output, redraw dedupe, OSC notification, focus, no automatic answers, preferences, copy shortcut');
} finally {await browser?.close();server.kill();}
