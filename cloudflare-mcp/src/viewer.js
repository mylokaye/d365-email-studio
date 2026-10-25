import { App } from '@modelcontextprotocol/ext-apps';
import { extractFile, fileUrl, readBytes, base64, LOAD_TIMEOUT_MS, MAX_FILE_BYTES } from './preview-data.js';
import { renderEmail } from './preview-render.js';

const app = new App({ name: 'd365-email-studio', version: '0.1.11' }, { availableDisplayModes: ['inline', 'fullscreen'] });
const preview = document.querySelector('#preview').attachShadow({ mode: 'open' });
const copyButton = document.querySelector('#copy');
const downloadButton = document.querySelector('#download');
const retryButton = document.querySelector('#retry');
const status = document.querySelector('#status');
const sourceText = document.querySelector('#source');
let bytes;
let html = '';
let filename = 'completed-email.html';
let current;
let loadedKey = '';
let loadingKey = '';
let loadVersion = 0;
let activeController;
let connected = false;
let remoteDownload;
function message(text) { status.textContent = text; }
function reset() {
  bytes = undefined;
  remoteDownload = undefined;
  html = '';
  sourceText.value = '';
  preview.replaceChildren();
  copyButton.disabled = true;
  downloadButton.disabled = true;
}
function withDeadline(promise, signal) {
  return new Promise((resolve, reject) => {
    const aborted = () => reject(new Error('File loading timed out or was interrupted. Please retry.'));
    if (signal.aborted) return aborted();
    signal.addEventListener('abort', aborted, { once: true });
    Promise.resolve(promise).then(resolve, reject).finally(() => signal.removeEventListener('abort', aborted));
  });
}
function updateDownload() {
  const supportsDownload = connected && !!app.getHostCapabilities()?.downloadFile;
  const supportsLink = !!remoteDownload && (typeof window.openai?.openExternal === 'function' || (connected && !!app.getHostCapabilities()?.openLinks));
  downloadButton.disabled = !bytes || !(supportsDownload || supportsLink);
  const help = document.querySelector('#download-help');
  help.hidden = !bytes || supportsDownload;
  help.textContent = supportsLink
    ? 'This host opens the original file link for download. Your browser may ask where to save it.'
    : 'This host cannot download this file from the app. Use the completed HTML attachment in the conversation.';
  downloadButton.title = supportsDownload ? 'Download the original output bytes' : 'Open the original output file through the host';
}
function showBytes(value, name) {
  if (!value.byteLength) throw new Error('The HTML file is empty.');
  const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(value);
  renderEmail(preview, text);
  bytes = value;
  html = text;
  filename = /\.html?$/i.test(name || '') ? name.replace(/^.*[\\/]/, '') : 'completed-email.html';
  document.querySelector('#title').textContent = filename;
  sourceText.value = text;
  copyButton.disabled = false;
  updateDownload();
  message('Email loaded. Remote images, active content and link navigation are disabled in this display copy.');
}
async function showFile(input, force = false) {
  if (input.unsupportedEdits) { reset(); message('Replacement payloads are not supported. Use the completed output file.'); return; }
  const { file, fileName } = input;
  const key = JSON.stringify([file.file_id, file.download_url, fileName]);
  if (!force && (key === loadedKey || key === loadingKey)) return;
  current = input;
  const version = ++loadVersion;
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;
  const timeout = setTimeout(() => controller.abort(), LOAD_TIMEOUT_MS);
  loadedKey = '';
  loadingKey = key;
  reset();
  retryButton.hidden = true;
  message('Loading completed email…');
  try {
    let url = file.download_url;
    if (file.file_id && window.openai?.getFileDownloadUrl) {
      try {
        const fresh = await withDeadline(window.openai.getFileDownloadUrl({ fileId: file.file_id }), controller.signal);
        url = fresh?.downloadUrl || fresh?.download_url || url;
      } catch (error) { if (controller.signal.aborted) throw error; }
    }
    if (version !== loadVersion) return;
    const resolvedUrl = fileUrl(url);
    const response = await fetch(resolvedUrl, { signal: controller.signal, credentials: 'omit', referrerPolicy: 'no-referrer' });
    const value = await readBytes(response, controller.signal);
    if (version !== loadVersion) return;
    remoteDownload = { file, url: resolvedUrl };
    showBytes(value, fileName);
    loadedKey = key;
  } catch (error) {
    if (version !== loadVersion) return;
    reset();
    retryButton.hidden = false;
    message(controller.signal.aborted ? 'File loading timed out. Retry or open the completed HTML file below.' : `${error.message || 'Could not read this file.'} You can also open the completed HTML file below; it stays in this app.`);
  } finally {
    clearTimeout(timeout);
    if (version === loadVersion) loadingKey = '';
  }
}
function handleResult(raw) {
  const input = extractFile(raw);
  if (input) void showFile(input);
}
// Register callbacks before connect: the host may deliver results immediately
// after initialization. SDK requests, IDs, capability checks and teardown use
// the official MCP Apps transport, not a separate handwritten RPC protocol.
app.ontoolresult = handleResult;
app.ontoolcancelled = () => { activeController?.abort(); reset(); message('Preview cancelled.'); };
app.onteardown = async () => { activeController?.abort(); return {}; };
void app.connect(undefined, { timeout: 10000 }).then(() => {
  connected = true;
  updateDownload();
  if (current && !bytes && !loadingKey) void showFile(current, true);
}).catch(() => { message('The app bridge could not connect. Open the completed HTML file below to preview it locally.'); });

// ChatGPT-only file helpers and result aliases supplement the standard bridge.
window.addEventListener('openai:set_globals', event => {
  handleResult(event.detail?.globals?.toolResponseMetadata);
  handleResult(event.detail?.globals?.toolOutput);
});
handleResult(window.openai?.toolResponseMetadata);
handleResult(window.openai?.toolOutput);
retryButton.addEventListener('click', () => { if (current) void showFile(current, true); });

document.querySelector('#local-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  const version = ++loadVersion;
  activeController?.abort();
  current = undefined;
  retryButton.hidden = true;
  loadedKey = '';
  loadingKey = '';
  reset();
  try {
    if (file.size > MAX_FILE_BYTES) throw new Error('This preview supports HTML files up to 5 MiB.');
    const value = new Uint8Array(await file.arrayBuffer());
    if (version !== loadVersion) return;
    showBytes(value, file.name);
  } catch (error) { message(error.message || 'Could not open that HTML file.'); }
});
copyButton.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(html); message('Complete HTML copied.'); }
  catch { sourceText.closest('details').open = true; sourceText.focus(); sourceText.select(); message('Automatic copy is unavailable here. The complete HTML is selected below; use your copy shortcut.'); }
});
downloadButton.addEventListener('click', async () => {
  if (!bytes) return;
  const value = bytes;
  const name = filename;
  const remote = remoteDownload;
  downloadButton.disabled = true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), LOAD_TIMEOUT_MS);
  try {
    if (connected && app.getHostCapabilities()?.downloadFile) {
      const result = await app.downloadFile({ contents: [{ type: 'resource', resource: {
        uri: `file:///${encodeURIComponent(name)}`, mimeType: 'text/html', blob: base64(value),
      } }] }, { timeout: 30000 });
      message(result.isError ? 'Download was cancelled or denied. Use the completed file attachment in the conversation.' : 'The host accepted the HTML download.');
    } else if (remote) {
      let url = remote.url;
      if (remote.file.file_id && window.openai?.getFileDownloadUrl) {
        const fresh = await withDeadline(window.openai.getFileDownloadUrl({ fileId: remote.file.file_id }), controller.signal);
        url = fresh?.downloadUrl || fresh?.download_url || url;
      }
      url = fileUrl(url);
      if (connected && app.getHostCapabilities()?.openLinks) {
        const result = await app.openLink({ url }, { timeout: 15000 });
        if (result.isError) throw new Error('File link was denied');
      } else if (typeof window.openai?.openExternal === 'function') {
        await window.openai.openExternal({ href: url, redirectUrl: false });
      } else throw new Error('No supported host file action');
      message('Opened the original HTML file through the host. Save it from your browser if prompted.');
    } else throw new Error('No output file reference');
  } catch { message('This host could not open the download. Use the completed HTML file attachment in the conversation.'); }
  finally { clearTimeout(timer); updateDownload(); }
});
