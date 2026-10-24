# Dynamics 365 Email Studio plugin

Private plugin containing the existing email editing skill and local Python validator,
connected to the read-only Cloudflare MCP at:
https://d365-email-studio.drbn8f85yx.workers.dev/mcp

Select this plugin in Codex, attach an existing email HTML file, and request specific
content edits or a translation. The local executor needs Python 3. Email HTML stays
local; Cloudflare only serves the instructions and validator source. No Dynamics
connection is required or included. The plugin does not send or publish emails.

The server is public and unauthenticated because it serves only the reusable guide
and validator source. Plugin account visibility is separate from endpoint visibility.

The skill's original constraints and validator are preserved. The packaged skill adds
guidance for using the MCP tools and showing a completed HTML file inline in chat.
The inline card shows a scrollable half-height preview with Copy HTML and Download HTML
buttons. ChatGPT passes a temporary file reference to the MCP tool; the Worker neither
fetches nor stores the email. The card reads the file through ChatGPT's file API.
After local validation, the agent passes the completed file's absolute path to the
`show_completed_email` file parameter. The host converts it to a temporary file
reference before the MCP request.
Remote images and scripts are blocked in
the preview, so final rendering still needs a Dynamics preview and test send.
The source lives in the adjacent
`d365-email-studio/` directory; refresh the package when that skill changes.
