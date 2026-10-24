import { App } from '@modelcontextprotocol/ext-apps';

const app = new App({ name: 'D365 Email Studio preview', version: '0.1.0' });
const frame = document.querySelector('#preview');
const copyButton = document.querySelector('#copy');
const downloadButton = document.querySelector('#download');
const status = document.querySelector('#status');
let html = '';
let fileBlob = null;
let filename = 'completed-email.html';

function message(value) { status.textContent = value; }

function showFile(text, blob, name) {
  html = text;
  fileBlob = blob;
  filename = /\.html?$/i.test(name) ? name.replace(/^.*[\\/]/, '') : 'completed-email.html';
  document.querySelector('#title').textContent = filename;
  const policy = "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'";
  frame.srcdoc = `<meta http-equiv="Content-Security-Policy" content="${policy}">` + html;
  copyButton.disabled = false;
  downloadButton.disabled = false;
  message('Preview ready. Scripts, external resources and form submissions are blocked.');
}

async function readChatFile(file) {
  if (!window.openai?.getFileDownloadUrl) throw new Error('ChatGPT file access unavailable');
  const { downloadUrl } = await window.openai.getFileDownloadUrl({ fileId: file.file_id });
  const response = await fetch(downloadUrl);
  if (!response.ok) throw new Error('File download failed');
  const data = await response.blob();
  const bytes = new Uint8Array(await data.arrayBuffer());
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 8192) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  }
  showFile(await data.text(), btoa(binary), file.file_name || 'completed-email.html');
}

app.addEventListener('toolinput', async ({ arguments: args }) => {
  try {
    if (typeof args?.file?.file_id === 'string') await readChatFile(args.file);
    else throw new Error('Missing file');
  } catch {
    message('Could not read this HTML file. Use the file link in the conversation.');
  }
});

copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(html);
    message('Complete HTML copied.');
  } catch {
    message('Copy failed. Open the file and copy its contents instead.');
  }
});

downloadButton.addEventListener('click', async () => {
  try {
    const result = await app.downloadFile({ contents: [{
      type: 'resource',
      resource: fileBlob
        ? { uri: `file:///${encodeURIComponent(filename)}`, mimeType: 'text/html', blob: fileBlob }
        : { uri: `file:///${encodeURIComponent(filename)}`, mimeType: 'text/html', text: html },
    }] });
    message(result.isError ? 'Download was cancelled.' : 'HTML download started.');
  } catch {
    message('Download unavailable in this host. Use the file link in the conversation.');
  }
});

app.connect().catch(() => message('Preview unavailable in this host. Use the file link in the conversation.'));
