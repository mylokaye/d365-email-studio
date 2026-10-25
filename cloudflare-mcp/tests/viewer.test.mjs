import test from 'node:test';
import assert from 'node:assert/strict';
import { extractFile, fileUrl, readBytes, base64 } from '../src/preview-data.js';
const file = { file_id: 'file_output', download_url: 'https://files.oaiusercontent.com/output.html' };

test('finds hidden file metadata despite unrelated top-level host metadata', () => {
  const parsed = extractFile({ _meta: { widgetSessionId: 'host' }, mcp_tool_result: { _meta: { file, file_name: 'completed-email.html' } } });
  assert.deepEqual(parsed, { file, fileName: 'completed-email.html' });
});
test('accepts the standard MCP tool-result envelope', () => {
  assert.equal(extractFile({ structuredContent: { status: 'ready' }, _meta: { file } }).file, file);
});
test('does not treat an executor path as a downloadable file', () => {
  assert.equal(extractFile({ file: '/tmp/output.html' }), null);
});
test('rejects legacy replacement instructions', () => {
  assert.equal(extractFile({ file, edits: [] }).unsupportedEdits, true);
});
test('only accepts trusted HTTPS file hosts without credentials or custom ports', () => {
  assert.equal(fileUrl(file.download_url), file.download_url);
  assert.equal(fileUrl('https://sdmntprnortheu.oaiusercontent.com/output'), 'https://sdmntprnortheu.oaiusercontent.com/output');
  for (const url of ['http://files.oaiusercontent.com/a', 'https://example.com/a', 'data:text/html,test', 'https://files.oaiusercontent.com.evil.test/a', 'https://user:secret@files.oaiusercontent.com/a', 'https://files.oaiusercontent.com:8443/a']) {
    assert.throws(() => fileUrl(url));
  }
});
test('preserves the original BOM and CRLF bytes for host downloads', async () => {
  const original = new Uint8Array([0xef, 0xbb, 0xbf, ...new TextEncoder().encode('<p>Bonjour</p>\r\n')]);
  const bytes = await readBytes(new Response(original), new AbortController().signal);
  assert.deepEqual(bytes, original);
  assert.deepEqual(Buffer.from(base64(bytes), 'base64'), Buffer.from(original));
});
test('rejects oversized files using headers and streaming byte counts', async () => {
  const signal = new AbortController().signal;
  await assert.rejects(readBytes(new Response('1234', { headers: { 'content-length': '4' } }), signal, 3), /5 MiB/);
  await assert.rejects(readBytes(new Response('1234'), signal, 3), /5 MiB/);
});
test('expired file links fail with a recoverable error', async () => {
  await assert.rejects(readBytes(new Response('', { status: 403 }), new AbortController().signal), /expired/);
});
test('aborted file reads fail instead of offering partial output', async () => {
  const controller = new AbortController(); controller.abort();
  await assert.rejects(readBytes(new Response('test'), controller.signal), /interrupted/);
});
