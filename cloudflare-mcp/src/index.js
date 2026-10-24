import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { skill, validator } from './content.js';
import { viewerHtml } from './viewer-content.js';

const INLINE_URI = 'ui://d365-email-studio/inline-preview-v4.html';
const LEGACY_INLINE_URIS = [
  'ui://d365-email-studio/inline-preview-v3.html',
  'ui://d365-email-studio/inline-preview-v2.html',
  'ui://d365-email-studio/inline-preview',
];
const UI_META = {
  ui: {
    prefersBorder: true,
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
  'openai/ui': {
    availableDisplayModes: ['inline'],
    preferredDisplayMode: 'inline',
  },
};

function createServer() {
  const server = new McpServer({ name: 'd365-email-studio', version: '0.1.8' });
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
    description: 'Required final step after every successful email edit or translation: call this tool to render the inline email preview with Copy HTML and Download HTML buttons in chat. Pass the completed HTML file in `file` (or in sandbox environments where only the user-uploaded email has a ChatGPT file ID, pass that uploaded file in `file` along with `file_name` and the exact `edits` applied). Do not claim the inline preview was requested unless this tool was called. The server does not fetch or store the file.',
    inputSchema: z.object({
      file: z.object({
        download_url: z.string(),
        file_id: z.string(),
        mime_type: z.string().optional(),
        file_name: z.string().optional(),
      }).passthrough(),
      file_name: z.string().optional().describe('Output HTML filename (for example, example3_french_buttons.html).'),
      edits: z.array(z.object({
        old: z.string().describe('Exact substring in the original HTML to replace.'),
        new: z.string().describe('Exact replacement substring in the updated HTML.'),
      })).optional().describe('Optional list of exact string replacements applied to produce the updated email when `file` references the original attached input file.'),
    }).passthrough(),
    _meta: {
      ui: { resourceUri: INLINE_URI },
      'openai/outputTemplate': INLINE_URI,
      'openai/fileParams': ['file'],
      'openai/toolInvocation/invoking': 'Preparing email preview',
      'openai/toolInvocation/invoked': 'Email preview ready',
    },
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  }, async ({ file, file_name, edits }) => {
    const resolvedName = file_name || file?.file_name || 'completed-email.html';
    const payload = {
      status: 'ready',
      file,
      file_name: resolvedName,
      ...(Array.isArray(edits) && edits.length > 0 ? { edits } : {}),
    };
    return {
      structuredContent: payload,
      content: [{
        type: 'text',
        text: `Inline preview ready for ${resolvedName}. Keep the completed HTML file link available in the response as well.`,
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
      return Response.json({ name: 'd365-email-studio', version: '0.1.8', emailProcessing: 'local-only' });
    }
    if (path !== '/mcp') return new Response('Not found', { status: 404 });
    if (Number(request.headers.get('content-length') || 0) > 65536) {
      return new Response('Request too large', { status: 413 });
    }
    return handler(request, env, ctx);
  },
};
