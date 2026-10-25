import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';

test('bundled MCP Apps SDK remains valid JavaScript inside the HTML template', async () => {
  execFileSync(process.execPath, ['build-viewer.mjs']);
  const { viewerHtml } = await import(`../src/viewer-content.js?test=${Date.now()}`);
  const scripts = [...viewerHtml.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length, 1);
  new vm.Script(scripts[0][1]);
  assert.equal(viewerHtml.includes('<!-- VIEWER_SCRIPT -->'), false);
  assert.equal(viewerHtml.includes('<iframe'), false);
  assert.ok(viewerHtml.includes('ui/download-file'));
});
