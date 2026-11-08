import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { build } from 'esbuild';
import { chromium } from '@playwright/test';

let browser, documentHtml;
const fixture = '\ufeff<html><body><h1>Completed email</h1><p>Hello</p></body></html>\r\n';
const file = { file_id: 'file_test', download_url: 'https://files.oaiusercontent.com/output.html' };
const payload = { _meta: { file, file_name: 'completed-email.html' } };
before(async () => {
  browser = await chromium.launch({ headless: true });
  const bundle = await build({ entryPoints: ['src/viewer.js'], bundle: true, write: false, format: 'iife', plugins: [{
    name: 'host-transport-double', setup(build) {
      build.onResolve({ filter: /^@modelcontextprotocol\/ext-apps$/ }, () => ({ path: 'host', namespace: 'test' }));
      build.onLoad({ filter: /.*/, namespace: 'test' }, () => ({ contents: `
        export class App {
          constructor() { window.hostApp = this; }
          connect() { return new Promise(resolve => { window.connectHost = resolve; if (!window.delayConnect) resolve(); }); }
          getHostCapabilities() { return window.hostCapabilities || {downloadFile:{},openLinks:{}}; }
          async downloadFile(value) { window.downloaded = value; return {}; }
          async openLink(value) { window.opened = value; return {}; }
        }` }));
    },
  }] });
  const template = await readFile('src/viewer.html', 'utf8');
  documentHtml = template.replace('<!-- VIEWER_SCRIPT -->', () => `<script>${bundle.outputFiles[0].text.replaceAll('</script', '<\\/script')}</script>`);
});
after(async () => { await browser?.close(); });
async function setup(t, { html = fixture, delayConnect = false, viewport, hold = false } = {}) {
  const context = await browser.newContext({ viewport });
  t.after(() => context.close());
  await context.addInitScript(({delayConnect}) => { window.delayConnect = delayConnect; }, {delayConnect});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  t.after(release);
  await page.route('https://files.oaiusercontent.com/**', async route => {
    if (hold) await gate;
    await route.fulfill({ body: Buffer.from(html), contentType: 'text/html', headers: { 'access-control-allow-origin': '*' } }).catch(() => {});
  });
  await page.route('https://emailui-usa1.mkt.dynamics.com/**', route => route.fulfill({status:404}));
  await page.route('https://preview.test/', route => route.fulfill({body:documentHtml,contentType:'text/html'}));
  await page.goto('https://preview.test/');
  await page.waitForFunction(() => !!window.hostApp && !!window.connectHost);
  t.after(() => assert.deepEqual(errors, []));
  const show = () => page.evaluate(payload => window.hostApp.ontoolresult(payload), payload);
  const loaded = () => page.waitForFunction(() => !document.querySelector('#copy').disabled);
  return {page, show, loaded, release};
}
test('cancelled completed file can load again and downloads retain exact bytes', async t => {
  const {page,show,loaded} = await setup(t);
  await show(); await loaded();
  await page.evaluate(() => window.hostApp.ontoolcancelled());
  assert.equal(await page.locator('#copy').isDisabled(), true);
  await show(); await loaded();
  await page.locator('#download').click();
  await page.waitForFunction(() => !!window.downloaded);
  const blob = await page.evaluate(() => window.downloaded.contents[0].resource.blob);
  assert.deepEqual(Buffer.from(blob,'base64'), Buffer.from(fixture));
});
test('cancel before bridge connection does not restart the file', async t => {
  const {page,show,release} = await setup(t,{delayConnect:true,hold:true});
  await show();
  await page.evaluate(() => { window.hostApp.ontoolcancelled(); window.connectHost(); });
  release();
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#status').textContent(),'Preview cancelled.');
  assert.equal(await page.locator('#copy').isDisabled(),true);
  assert.equal(await page.locator('#retry').isHidden(),true);
});
test('rejected replacement payload invalidates pending work', async t => {
  const {page,show,release} = await setup(t,{hold:true});
  await show();
  await page.evaluate(() => window.hostApp.ontoolresult({edits:[]}));
  release(); await page.waitForTimeout(100);
  assert.match(await page.locator('#status').textContent(),/Replacement payloads/);
  assert.equal(await page.locator('#copy').isDisabled(),true);
});
test('teardown prevents late connection and new results from reviving preview', async t => {
  const {page,show,release} = await setup(t,{hold:true,delayConnect:true});
  await show();
  await page.evaluate(async () => { await window.hostApp.onteardown(); window.connectHost(); });
  release(); await show(); await page.waitForTimeout(100);
  assert.equal(await page.locator('#copy').isDisabled(),true);
  assert.equal(await page.locator('#preview').evaluate(el => el.shadowRoot.childNodes.length),0);
});
test('a local selection wins over an outstanding remote load', async t => {
  const {page,show,loaded,release} = await setup(t,{hold:true});
  await show();
  await page.locator('#local-file').setInputFiles({name:'local.html',mimeType:'text/html',buffer:Buffer.from('<p>Local selection</p>')});
  await loaded(); release(); await page.waitForTimeout(100);
  assert.match(await page.locator('#preview p').innerText(),/Local selection/);
  assert.equal(await page.locator('#source').inputValue(),'<p>Local selection</p>');
});
test('sanitization removes active content without changing downloaded source', async t => {
  const html = '<html><head><style>p{color:red;background-image:url("https://blocked.example/bg.png")}</style></head><body><p>Hello</p><script>window.pwned=true</script><iframe src="https://blocked.example"></iframe><a href="javascript:alert(1)">Link</a><img src="https://blocked.example/a.png" onerror="window.pwned=true"></body></html>';
  const {page,show,loaded} = await setup(t,{html});
  await show(); await loaded();
  assert.equal(await page.evaluate(() => !!window.pwned),false);
  assert.equal(await page.locator('#preview script, #preview iframe, #preview [onerror], #preview [href]').count(),0);
  assert.equal(await page.locator('#preview img').getAttribute('src'),null);
  assert.match(await page.locator('#image-warning').textContent(),/blocked.example/);
  assert.equal(await page.locator('#source').inputValue(),html);
  await page.locator('#download').click();
  await page.waitForFunction(() => !!window.downloaded);
  assert.deepEqual(Buffer.from(await page.evaluate(() => window.downloaded.contents[0].resource.blob),'base64'),Buffer.from(html));
});
test('permitted image failures produce a persistent rendering warning', async t => {
  const {page,show,loaded} = await setup(t,{html:'<p>Hello</p><img src="https://emailui-usa1.mkt.dynamics.com/missing.png">'});
  await show(); await loaded();
  await page.waitForFunction(() => document.querySelector('#image-warning').textContent.includes('could not load'));
  await page.locator('#download').click();
  assert.match(await page.locator('#image-warning').textContent(),/could not load/);
});
test('unsupported-host warning is readable on mobile', async t => {
  const {page,show,loaded} = await setup(t,{viewport:{width:390,height:844},html:'<h1>Completed email</h1><img src="https://assets-gbr.mkt.dynamics.com/example.png">'});
  await show(); await loaded();
  assert.equal(await page.title(),'Email preview');
  assert.match(await page.locator('#preview h1').innerText(),/Completed email/);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
  assert.equal(await page.locator('#image-warning').getAttribute('aria-live'),'polite');
  if (process.env.QA_SCREENSHOT_DIR) {
    await mkdir(process.env.QA_SCREENSHOT_DIR,{recursive:true});
    await page.screenshot({path:process.env.QA_SCREENSHOT_DIR+'/preview-mobile.png',fullPage:true});
  }
});
