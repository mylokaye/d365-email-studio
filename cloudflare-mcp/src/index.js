import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { skill, validator } from './content.js';
import { viewerHtml } from './viewer-content.js';

const INLINE_URI = 'ui://d365-email-studio/inline-preview-v7.html';
const LEGACY_INLINE_URIS = [
  'ui://d365-email-studio/inline-preview-v6.html',
  'ui://d365-email-studio/inline-preview-v5.html',
  'ui://d365-email-studio/inline-preview-v4.html',
  'ui://d365-email-studio/inline-preview-v3.html',
  'ui://d365-email-studio/inline-preview-v2.html',
  'ui://d365-email-studio/inline-preview',
];
const UI_META = {
  ui: {
    prefersBorder: true,
    domain: 'https://d365-email-studio.drbn8f85yx.workers.dev',
    permissions: {
      clipboardWrite: {},
    },
    csp: {
      connectDomains: [
        'https://chatgpt.com',
        'https://files.oaiusercontent.com',
        'https://*.oaiusercontent.com',
      ],
      resourceDomains: [],
      frameDomains: [],
    },
  },
  'openai/widgetCSP': { redirect_domains: ['https://*.oaiusercontent.com'] },
  'openai/ui': {
    availableDisplayModes: ['inline', 'fullscreen'],
    preferredDisplayMode: 'inline',
  },
};

function createServer() {
  const server = new McpServer({ name: 'd365-email-studio', version: '0.1.11' });
  server.registerTool('get_email_studio_guide', {
    description: 'Get the D365 email editing rules. No email HTML is accepted. Edit and validate emails locally using the bundled skill.',
    inputSchema: z.object({}).strict(),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  }, async () => ({ content: [{ type: 'text', text: skill }] }));
  server.registerTool('get_email_validator_source', {
    description: 'Download the Python structural validator source for local execution. Takes no email content or file paths. Save locally and run with Python 3 against the original and edited email files.',
    inputSchema: z.object({}).strict(),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  }, async () => ({ content: [{ type: 'text', text: validator }] }));
  for (const [index, uri] of [INLINE_URI, ...LEGACY_INLINE_URIS].entries()) {
    registerAppResource(
      server,
      index === 0 ? 'inline-preview' : `inline-preview-legacy-${index}`,
      uri,
      {
        description: 'Inline read-only preview for completed Dynamics 365 emails.',
        mimeType: RESOURCE_MIME_TYPE,
        _meta: UI_META,
      },
      async () => ({
        contents: [{
          uri,
          mimeType: RESOURCE_MIME_TYPE,
          text: viewerHtml,
          _meta: UI_META,
        }],
      }),
    );
  }
  registerAppTool(server, 'show_completed_email', {
    title: 'Show completed email',
    description: 'Preview the completed, locally validated HTML output file. Pass only that output file reference; never pass the original input, email HTML, replacement text, or customer data. If the host cannot reference the completed file, provide its download link without calling this tool. The server never fetches the file.',
    inputSchema: z.object({
      file: z.object({
        download_url: z.url().max(4096).refine(value => {
          const url = new URL(value);
          return url.protocol === 'https:' && !url.username && !url.password &&
            (url.hostname === 'chatgpt.com' || url.hostname === 'files.oaiusercontent.com' || url.hostname.endsWith('.oaiusercontent.com'));
        }, 'Expected a ChatGPT output file URL'),
        file_id: z.string().min(1).max(256).regex(/^[A-Za-z0-9_-]+$/),
        mime_type: z.literal('text/html').optional(),
        file_name: z.string().max(256).optional(),
      }).strict(),
    }).strict(),
    outputSchema: z.object({ status: z.literal('ready'), file_name: z.string() }).strict(),
    _meta: {
      ui: { resourceUri: INLINE_URI },
      'openai/outputTemplate': INLINE_URI,
      'openai/fileParams': ['file'],
      'openai/toolInvocation/invoking': 'Preparing email preview',
      'openai/toolInvocation/invoked': 'Email preview ready',
    },
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  }, async ({ file }) => {
    const resolvedName = 'completed-email.html';
    const payload = {
      status: 'ready',
      file,
      file_name: resolvedName,
    };
    return {
      structuredContent: { status: 'ready', file_name: resolvedName },
      content: [{
        type: 'text',
        text: `Opening the inline preview for ${resolvedName}. Keep the completed HTML file link available in the response as well.`,
      }],
      _meta: payload,
    };
  });
  return server;
}

const handler = createMcpHandler(createServer, { allowedOriginHostnames: '*' });
export default {
  async fetch(request, env, ctx) {
    const path = new URL(request.url).pathname;
    if (path === '/health' && request.method === 'GET') {
      return Response.json({ name: 'd365-email-studio', version: '0.1.11', emailProcessing: 'local-only' });
    }
    if (path !== '/mcp') return new Response('Not found', { status: 404 });
    if (Number(request.headers.get('content-length') || 0) > 65536) {
      return new Response('Request too large', { status: 413 });
    }
    // Enforce the limit even when Content-Length is absent or inaccurate.
    if (request.body) {
      const reader = request.body.getReader();
      const chunks = [];
      let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 65536) {
          void reader.cancel();
          return new Response('Request too large', { status: 413 });
        }
        chunks.push(value);
      }
      const body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.byteLength;
      }
      request = new Request(request, { body });
    }
    return handler(request, env, ctx);
  },
};
