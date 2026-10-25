# Dynamics 365 Email Studio

Edit and translate existing **Dynamics 365 Customer Insights – Journeys** email HTML while preserving its layout, tracking, dynamic expressions and Outlook markup.

[Website](https://mylokaye.me/d365-email-studio/) · [Support](https://mylokaye.me/d365-email-studio/support/) · [Privacy](https://mylokaye.me/d365-email-studio/privacy/) · [Terms](https://mylokaye.me/d365-email-studio/terms/)

## What it does

- Updates existing wording, headings, button labels and preheader copy.
- Translates content while preserving protected HTML and Dynamics expressions.
- Changes existing image sources and ordinary link destinations when requested.
- Checks the edited file against the original with a local Python validator.

It does not create or redesign emails, connect to your Dynamics tenant, send messages or publish campaigns.

## Use it

1. Select the [Email Studio plugin](https://chatgpt.com/plugins/plugin_asdk_app_6adcc939af148191967f4b5854d9a4e2) in Codex. Access depends on the plugin’s current availability.
2. Supply an existing email HTML file and describe the changes you want.
3. In a host that supports ChatGPT file inputs and inline plugin UI, the completed result appears inline in chat as an isolated preview with Copy HTML and a host-mediated Download HTML button. When the host lacks app-download support, the button opens the original output file through the host; the completed file attachment is also provided. Review the separate output file, diff and validation result as well. A file link remains available when inline UI is unsupported or the host cannot reference the completed output directly. The original email is never used to reconstruct the output in the preview.
4. Check the result in Dynamics preview and a test send before use.

Local execution with **Python 3** is required for structural validation.

Example request:

> Translate this email into French. Preserve names, factual details, links, Dynamics expressions and the existing layout.

## Validate locally

From the repository root:

```sh
python3 d365-email-studio/scripts/validate_email.py original.html updated.html
```

The validator checks permitted source changes. It does not prove translation quality, rendering or acceptance in Dynamics.

## Privacy

File editing and validation run locally. The Cloudflare MCP server serves the editing guide, validator source and preview UI; it never receives raw email HTML. For an inline preview, ChatGPT passes a temporary file reference to the server, which does not fetch or store it. Content supplied in ChatGPT or Codex is still processed by OpenAI according to your account settings and its policies.

## Repository

- [`d365-email-studio/`](d365-email-studio/) — skill instructions and validator.
- [`plugin/`](plugin/) — plugin package and icons.
- [`cloudflare-mcp/`](cloudflare-mcp/) — read-only MCP server and development instructions.
- [`example/`](example/) — sample email files.

## Licence

[GPL-3.0](LICENSE). An independent project by Mylo Kaye, not endorsed by Microsoft.

## Current releases

The linked private App-backed plugin is version **1.0.3**. Its App identity and
connection are preserved; it now includes the corrected local skill and validator.
The standalone package and Worker are version **0.1.11**. These use separate
version histories. Email HTML and replacement lists are never preview-tool inputs;
only the completed output file reference is passed to the Worker.

Verification: the three Python regression runners, 15 JavaScript checks, Worker
build, local and live MCP smoke checks passed. The UI uses the official MCP Apps SDK. The rendered preview and exact-byte host
download were verified in a browser with the SDK protocol; the user confirmed the actual email heading renders in the live card and the
Download HTML fallback opens or saves the original output file.
