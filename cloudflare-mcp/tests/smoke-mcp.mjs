import assert from 'node:assert/strict';
const endpoint = process.argv[2] || 'http://localhost:8791/mcp';
let nextId = 0;
let session;
async function rpc(method, params) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json, text/event-stream', ...(session ? { 'mcp-session-id': session } : {}) },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++nextId, method, params }),
  });
  assert.equal(response.ok, true, `HTTP ${response.status}`);
  session = response.headers.get('mcp-session-id') || session;
  const body = await response.text();
  const packets = response.headers.get('content-type')?.includes('text/event-stream')
    ? body.split('\n').filter(line => line.startsWith('data: ')).map(line => JSON.parse(line.slice(6)))
    : [JSON.parse(body)];
  return packets.find(packet => packet.id === nextId);
}
const initialized = await rpc('initialize', { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'release-check', version: '1.0.0' } });
assert.equal(initialized.result.serverInfo.version, '0.1.11');
const listed = await rpc('tools/list', {});
const preview = listed.result.tools.find(tool => tool.name === 'show_completed_email');
assert.ok(preview);
assert.equal(preview.inputSchema.additionalProperties, false);
assert.equal('edits' in preview.inputSchema.properties, false);
const file = { file_id: 'file_release_check', download_url: 'https://files.oaiusercontent.com/release-check.html', mime_type: 'text/html' };
const shown = await rpc('tools/call', { name: 'show_completed_email', arguments: { file } });
assert.equal(shown.result.isError, undefined);
assert.equal(shown.result._meta.file.file_id, file.file_id);
// Empty legacy edits test contains no email content or customer data.
const rejected = await rpc('tools/call', { name: 'show_completed_email', arguments: { file, edits: [] } });
assert.ok(rejected.error || rejected.result?.isError);
const resource = await rpc('resources/read', { uri: preview._meta.ui.resourceUri });
assert.ok(resource.result.contents[0].text.includes('ui/download-file'));
assert.ok(!resource.result.contents[0].text.includes('<iframe'));
assert.equal(resource.result.contents[0]._meta.ui.domain, 'https://d365-email-studio.drbn8f85yx.workers.dev');
assert.ok(!resource.result.contents[0].text.includes('replaceAll'));
const imageOrigins = resource.result.contents[0]._meta.ui.csp.resourceDomains;
assert.ok(imageOrigins.includes('https://emailui-usa1.mkt.dynamics.com'));
for (const origin of imageOrigins) {
  assert.equal(new URL(origin).origin, origin);
  assert.ok(!origin.includes('*') && !origin.includes('%'));
}
console.log('PASS: initialize, strict tool schema, file-reference handoff, legacy rejection, preview resource');
