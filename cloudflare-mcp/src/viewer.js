const frame = document.querySelector('#preview');
const copyButton = document.querySelector('#copy');
const downloadButton = document.querySelector('#download');
const status = document.querySelector('#status');
let html = '';
let filename = 'completed-email.html';
let loadedFileId = '';

function message(value) { status.textContent = value; }

async function showFile(file) {
  if (typeof file?.file_id !== 'string' || file.file_id === loadedFileId) return;
  loadedFileId = file.file_id;
  try {
    const { downloadUrl } = window.openai?.getFileDownloadUrl
      ? await window.openai.getFileDownloadUrl({ fileId: file.file_id })
      : { downloadUrl: file.download_url };
    if (!downloadUrl) throw new Error('No file URL');
    const response = await fetch(downloadUrl);
    if (!response.ok) throw new Error('File download failed');
    html = await response.text();
    filename = /\.html?$/i.test(file.file_name || '')
      ? file.file_name.replace(/^.*[\\/]/, '')
      : 'completed-email.html';
    document.querySelector('#title').textContent = filename;
    const policy = "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'";
    frame.srcdoc = `<meta http-equiv="Content-Security-Policy" content="${policy}">` + html;
    copyButton.disabled = false;
    downloadButton.disabled = false;
    message('Preview ready. Scripts, external resources and form submissions are blocked.');
  } catch {
    loadedFileId = '';
    message('Could not read this HTML file. Use the file link in the conversation.');
  }
}

function handleInput(input) {
  if (input?.file) void showFile(input.file);
}

// Keep the MCP Apps bridge small: the full SDK client adds hundreds of KB to
// this otherwise self-contained resource. This view only needs initialize and
// the standard tool-input notification.
window.addEventListener('message', (event) => {
  if (event.source !== window.parent) return;
  const packet = event.data;
  if (packet?.jsonrpc !== '2.0') return;

  if (packet.method === 'ui/initialize' && packet.id !== undefined) {
    window.parent.postMessage({
      jsonrpc: '2.0',
      id: packet.id,
      result: {
        protocolVersion: packet.params?.protocolVersion || '2025-11-21',
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
    return;
  }

  if (packet.method === 'ui/notifications/tool-input') {
    handleInput(packet.params?.arguments);
  }
});

window.addEventListener('openai:set_globals', (event) => {
  handleInput(event.detail?.globals?.toolInput);
});
handleInput(window.openai?.toolInput);

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
