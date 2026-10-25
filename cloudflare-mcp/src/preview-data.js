export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const LOAD_TIMEOUT_MS = 15000;

// Host result envelopes can contain unrelated _meta fields alongside the data.
// Inspect only the documented envelopes, rather than choosing the first truthy one.
export function extractFile(raw) {
  const queue = [raw];
  const seen = new Set();
  while (queue.length) {
    const value = queue.shift();
    if (!value || typeof value !== 'object' || seen.has(value)) continue;
    seen.add(value);
    if ('edits' in value) return { unsupportedEdits: true };
    const file = value.file;
    if (file && typeof file === 'object' && (file.file_id || file.download_url)) {
      return { file, fileName: value.file_name || file.file_name || 'completed-email.html' };
    }
    for (const key of ['_meta', 'structuredContent', 'mcp_tool_result', 'call_tool_result', 'toolResponseMetadata']) {
      if (value[key]) queue.push(value[key]);
    }
  }
  return null;
}

export function fileUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.port ||
      !(url.hostname === 'chatgpt.com' || url.hostname.endsWith('.oaiusercontent.com'))) {
    throw new Error('The host did not provide a supported file URL.');
  }
  return url.href;
}

export async function readBytes(response, signal, maximum = MAX_FILE_BYTES) {
  if (!response.ok) throw new Error('The file link has expired or could not be read. Retry to request a fresh link.');
  if (Number(response.headers.get('content-length') || 0) > maximum) throw new Error('This preview supports HTML files up to 5 MiB.');
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      if (signal.aborted) throw new Error('File loading was interrupted. Please retry.');
      const { value, done } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maximum) throw new Error('This preview supports HTML files up to 5 MiB.');
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

export function base64(bytes) {
  let result = '';
  for (let start = 0; start < bytes.length; start += 8192) {
    result += String.fromCharCode(...bytes.subarray(start, start + 8192));
  }
  return btoa(result);
}
