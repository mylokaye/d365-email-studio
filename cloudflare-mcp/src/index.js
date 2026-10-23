import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';
import { skill, validator } from './content.js';

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
