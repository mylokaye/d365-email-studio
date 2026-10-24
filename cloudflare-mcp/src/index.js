import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { skill, validator } from './content.js';
import { viewerHtml } from './viewer-content.js';

const INLINE_URI = 'ui://d365-email-studio/inline-preview-v2.html';

function createServer() {
  const server = new McpServer({ name: 'd365-email-studio', version: '0.1.0' });
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
  registerAppResource(server, 'inline-preview', INLINE_URI, {}, async () => ({
    contents: [{
      uri: INLINE_URI,
      mimeType: RESOURCE_MIME_TYPE,
      text: viewerHtml,
      _meta: {
        ui: {
          prefersBorder: true,
          csp: {
            connectDomains: ['https://chatgpt.com', 'https://files.oaiusercontent.com'],
            resourceDomains: [],
            frameDomains: ['https://web-sandbox.oaiusercontent.com'],
          },
        },
        'openai/ui': { availableDisplayModes: ['inline'], preferredDisplayMode: 'inline' },
      },
    }],
  }));
  registerAppTool(server, 'show_completed_email', {
    title: 'Show completed email',
    description: 'After editing and validating an email locally, pass the completed HTML file to show its preview, Copy HTML and Download HTML buttons inline in chat. The server does not fetch or store the file.',
    inputSchema: {
      file: z.object({
        download_url: z.string(),
        file_id: z.string(),
        mime_type: z.string().optional(),
        file_name: z.string().optional(),
      }).strict(),
    },
    _meta: {
      ui: { resourceUri: INLINE_URI },
      'openai/outputTemplate': INLINE_URI,
      'openai/fileParams': ['file'],
      'openai/toolInvocation/invoking': 'Preparing email preview',
      'openai/toolInvocation/invoked': 'Email preview ready',
    },
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  }, async () => ({ content: [{ type: 'text', text: 'Inline preview requested. The host may still fail to display it; keep the completed HTML file link available.' }] }));
  return server;
}

const handler = createMcpHandler(createServer);
export default {
  async fetch(request, env, ctx) {
    const path = new URL(request.url).pathname;
    if (path === '/health' && request.method === 'GET') {
      return Response.json({ name: 'd365-email-studio', version: '0.1.0', emailProcessing: 'local-only' });
    }
    if (path !== '/mcp') return new Response('Not found', { status: 404 });
    if (Number(request.headers.get('content-length') || 0) > 16384) {
      return new Response('Request too large', { status: 413 });
    }
    return handler(request, env, ctx);
  },
};
