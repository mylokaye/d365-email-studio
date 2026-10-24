const frame = document.querySelector('#preview');
const copyButton = document.querySelector('#copy');
const downloadButton = document.querySelector('#download');
const status = document.querySelector('#status');
let html = '';
let filename = 'completed-email.html';
let loadedKey = '';

function message(value) { status.textContent = value; }

let lastWidth = 0;
let lastHeight = 0;
function notifySize() {
  const doc = document.documentElement;
  const height = Math.ceil(Math.max(doc.scrollHeight, doc.getBoundingClientRect().height, document.body?.scrollHeight || 0));
  const width = Math.ceil(window.innerWidth || doc.getBoundingClientRect().width || 0);
  if (height > 0 && (height !== lastHeight || width !== lastWidth)) {
    lastWidth = width;
    lastHeight = height;
    window.parent?.postMessage({
      jsonrpc: '2.0',
      method: 'ui/notifications/size-changed',
      params: { width, height },
    }, '*');
    window.openai?.notifyIntrinsicHeight?.(height);
  }
}

if (typeof ResizeObserver !== 'undefined') {
  const observer = new ResizeObserver(() => requestAnimationFrame(notifySize));
  observer.observe(document.documentElement);
  if (document.body) observer.observe(document.body);
}

function normalizeInput(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const source = raw._meta || raw.mcp_tool_result?._meta || raw.call_tool_result?._meta || raw.structuredContent || raw.arguments || raw;
  let file = source.file || raw.file;
  if (typeof file === 'string' && file) {
    file = { file_id: file };
  } else if (!file && (typeof source.file_id === 'string' || typeof source.download_url === 'string')) {
    file = {
      file_id: source.file_id,
      download_url: source.download_url,
      file_name: source.file_name,
    };
  }
  if (!file || (typeof file.file_id !== 'string' && typeof file.download_url !== 'string')) {
    return null;
  }
  return {
    file,
    fileName: source.file_name || raw.file_name || file.file_name,
    edits: Array.isArray(source.edits) ? source.edits : (Array.isArray(raw.edits) ? raw.edits : []),
  };
}

async function showFile({ file, fileName, edits }) {
  const key = `${file.file_id || ''}:${file.download_url ? 'url' : 'nourl'}:${edits.length}`;
  if (key === loadedKey || (html && file.file_id && loadedKey.startsWith(`${file.file_id}:`))) return;
  loadedKey = key;
  try {
    let downloadUrl = '';
    if (file.file_id && window.openai?.getFileDownloadUrl) {
      try {
        const result = await window.openai.getFileDownloadUrl({ fileId: file.file_id });
        downloadUrl = result?.downloadUrl || result?.download_url || '';
      } catch {
        downloadUrl = '';
      }
    }
    if (!downloadUrl && typeof file.download_url === 'string') {
      downloadUrl = file.download_url;
    }
    if (!downloadUrl) throw new Error('No file URL');
    const response = await fetch(downloadUrl);
    if (!response.ok) throw new Error('File download failed');
    let content = await response.text();
    if (edits.length > 0 && edits.every((e) => typeof e?.old === 'string' && typeof e?.new === 'string' && content.includes(e.old))) {
      for (const edit of edits) {
        content = content.replaceAll(edit.old, edit.new);
      }
    }
    html = content;
    const candidateName = fileName || file.file_name || '';
    filename = /\.html?$/i.test(candidateName)
      ? candidateName.replace(/^.*[\\/]/, '')
      : 'completed-email.html';
    document.querySelector('#title').textContent = filename;
    const policy = "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'";
    frame.srcdoc = `<meta http-equiv="Content-Security-Policy" content="${policy}">` + html;
    copyButton.disabled = false;
    downloadButton.disabled = false;
    message('Preview ready. Scripts, external resources and form submissions are blocked.');
    notifySize();
  } catch {
    loadedKey = '';
    message('Could not read this HTML file. Use the file link in the conversation.');
    notifySize();
  }
}

function handleInput(raw) {
  const parsed = normalizeInput(raw);
  if (parsed) void showFile(parsed);
}

// Keep the MCP Apps bridge small: the full SDK client adds hundreds of KB to
// this otherwise self-contained resource. This view only needs initialize and
// the standard tool-input / tool-result notifications.
const INIT_REQUEST_ID = 1;

window.addEventListener('message', (event) => {
  if (event.source !== window.parent) return;
  const packet = event.data;
  if (packet?.jsonrpc !== '2.0') return;

  if (packet.id === INIT_REQUEST_ID && packet.result) {
    window.parent.postMessage({
      jsonrpc: '2.0',
      method: 'ui/notifications/initialized',
      params: {},
    }, '*');
    notifySize();
    return;
  }

  if (packet.method === 'ui/initialize' && packet.id !== undefined) {
    window.parent.postMessage({
      jsonrpc: '2.0',
      id: packet.id,
      result: {
        protocolVersion: packet.params?.protocolVersion || '2026-01-26',
        hostInfo: { name: 'MCP Apps host', version: '1.0.0' },
        hostCapabilities: {},
        hostContext: {},
      },
    }, '*');
    window.parent.postMessage({
      jsonrpc: '2.0',
      method: 'ui/notifications/initialized',
      params: {},
    }, '*');
    notifySize();
    return;
  }

  if (packet.method === 'ui/notifications/tool-input') {
    handleInput(packet.params);
  }
  if (packet.method === 'ui/notifications/tool-result') {
    handleInput(packet.params);
  }
});

window.parent?.postMessage({
  jsonrpc: '2.0',
  id: INIT_REQUEST_ID,
  method: 'ui/initialize',
  params: {
    protocolVersion: '2026-01-26',
    appInfo: { name: 'd365-email-studio', version: '0.1.0' },
    appCapabilities: { availableDisplayModes: ['inline'] },
  },
}, '*');

window.addEventListener('openai:set_globals', (event) => {
  const globals = event.detail?.globals;
  handleInput(globals?.toolResponseMetadata);
  handleInput(globals?.toolOutput);
  handleInput(globals?.toolInput);
});
handleInput(window.openai?.toolResponseMetadata);
handleInput(window.openai?.toolOutput);
handleInput(window.openai?.toolInput);
notifySize();

copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(html);
    message('Complete HTML copied.');
  } catch {
    message('Copy failed. Open the file and copy its contents instead.');
  }
});

downloadButton.addEventListener('click', () => {
  try {
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    message('HTML download started.');
  } catch {
    message('Download unavailable in this host. Use the file link in the conversation.');
  }
});
