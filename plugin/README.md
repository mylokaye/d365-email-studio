# Dynamics 365 Email Studio plugin

Private plugin containing the existing email editing skill and local Python validator,
connected to the read-only Cloudflare MCP at:
https://d365-email-studio.drbn8f85yx.workers.dev/mcp

This private package also maps the registered D365 Email Studio ChatGPT connection
through `.app.json`, so its MCP tools are available alongside the skill.

Select this plugin in Codex, attach an existing email HTML file, and request specific
content edits or a translation. The local executor needs Python 3. Email HTML stays
local; Cloudflare only serves the instructions and validator source. No Dynamics
connection is required or included. The plugin does not send or publish emails.

The server is public and unauthenticated because it serves only the reusable guide
and validator source. Plugin account visibility is separate from endpoint visibility.

The skill's original constraints and validator are preserved. The packaged skill adds
guidance for using the MCP tools and showing a completed HTML file inline in chat.
The inline card uses the official MCP Apps SDK and an isolated, sanitized
display copy. It offers Copy HTML and host-mediated Download HTML where supported;
the downloaded bytes are the original validated output, never the display copy.
When binary app downloads are unsupported, the button opens the original output
file through the host link API. The completed output attachment is also provided. Expired file links have
a retry action and a local HTML-file picker that does not upload to Cloudflare. After successful local validation, the agent may call
`show_completed_email` only with a reference to the completed output file.
Email HTML, replacement text and customer data must never be sent to Cloudflare.
The Worker returns file reference metadata without fetching the email; the card
reads the completed output through ChatGPT's file API. If the host cannot
reference the output, the agent provides the validated download link without
an inline preview. The original input must never stand in for the output.
The editing workflow does not open the generated email in Chrome or another browser.
HTTPS images are enabled, while scripts are blocked in
the preview, so final rendering still needs a Dynamics preview and test send.
The source lives in the adjacent
`d365-email-studio/` directory; refresh the package when that skill changes.
