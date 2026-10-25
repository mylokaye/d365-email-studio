import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
import { z } from 'zod';

// Exercise the real registration schemas and fetch guard without starting a
// Worker runtime. The SDK bindings are replaced at their registration boundary.
const source = (await readFile(new URL('../src/index.js', import.meta.url), 'utf8'))
  .replace(/^import .*;\n/gm, '').replace('export default {', 'globalThis.worker = {');
function harness() {
  const registered = new Map();
  const resources = [];
  const context = vm.createContext({
    z, URL, Request, Response, Uint8Array, skill: 'guide', validator: 'validator', viewerHtml: '<html></html>',
    McpServer: class { registerTool(name, config, handler) { registered.set(name, { config, handler }); } },
    registerAppResource(server, name, uri, config, handler) { resources.push({ name, uri, config, handler }); }, RESOURCE_MIME_TYPE: 'text/html',
    registerAppTool(server, name, config, handler) { registered.set(name, { config, handler }); },
    createMcpHandler(createServer) { createServer(); return async () => new Response('handled'); },
  });
  vm.runInContext(source, context);
  return { worker: context.worker, registered, resources };
}
const file = { file_id: 'file_output', download_url: 'https://files.oaiusercontent.com/output.html', mime_type: 'text/html' };

test('preview schema rejects email HTML and replacement lists at every input level', () => {
  const { registered } = harness();
  const schema = registered.get('show_completed_email').config.inputSchema;
  assert.equal(schema.safeParse({ file }).success, true);
  for (const value of [
    { file, edits: [{ old: 'Customer text', new: 'Translated text' }] },
    { file, html: '<p>Customer text</p>' },
    { file: { ...file, html: '<p>Customer text</p>' } },
    { file: { ...file, edits: [] } },
  ]) assert.equal(schema.safeParse(value).success, false);
});

test('preview handler returns only file reference metadata', async () => {
  const { registered } = harness();
  const output = await registered.get('show_completed_email').handler({ file });
  assert.deepEqual(JSON.parse(JSON.stringify(output.structuredContent)), {
    status: 'ready', file_name: 'completed-email.html',
  });
  assert.deepEqual(JSON.parse(JSON.stringify(output._meta.file)), file);
  assert.equal(registered.get('show_completed_email').config.outputSchema.safeParse(output.structuredContent).success, true);
});

test('guide tools reject unexpected arguments', () => {
  const { registered } = harness();
  for (const name of ['get_email_studio_guide', 'get_email_validator_source']) {
    assert.equal(registered.get(name).config.inputSchema.safeParse({ html: 'private' }).success, false);
  }
});

test('oversized streamed requests are rejected without Content-Length', async () => {
  const { worker } = harness();
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(65537)); controller.close(); } });
  const request = new Request('https://example.test/mcp', { method: 'POST', body: stream, duplex: 'half' });
  assert.equal(request.headers.has('content-length'), false);
  assert.equal((await worker.fetch(request)).status, 413);
});

test('bounded requests reach the handler', async () => {
  const { worker } = harness();
  const request = new Request('https://example.test/mcp', { method: 'POST', body: '{}' });
  assert.equal(await (await worker.fetch(request)).text(), 'handled');
});


test('preview policy preserves the host-confirmed explicit Dynamics image origin', async () => {
  const { resources, registered } = harness();
  const uri = registered.get('show_completed_email').config._meta.ui.resourceUri;
  const resource = resources.find(item => item.uri === uri);
  assert.ok(resource);
  const { contents } = await resource.handler();
  for (const metadata of [resource.config._meta, contents[0]._meta]) {
    const origins = Array.from(metadata.ui.csp.resourceDomains);
    assert.ok(origins.includes('https://emailui-usa1.mkt.dynamics.com'));
    for (const origin of origins) {
      assert.equal(new URL(origin).origin, origin);
      assert.ok(!origin.includes('*') && !origin.includes('%'));
    }
    assert.equal(metadata.ui.csp.frameDomains.length, 0);
  }
});
