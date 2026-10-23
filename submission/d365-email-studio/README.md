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
only guidance for using the read-only MCP tools. The source lives in the adjacent
`d365-email-studio/` directory; refresh the package when that skill changes.
