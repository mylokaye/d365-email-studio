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

1. Select the [Email Studio plugin](https://chatgpt.com/plugins/plugins_6adb0889a8488191b5270dc256904c1c) in Codex. Access depends on the plugin’s current availability.
2. Supply an existing email HTML file and describe the changes you want.
3. Review the separate output file, diff and validation result.
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

File editing and validation run locally. The Cloudflare MCP server serves only the editing guide and validator source; never send it email HTML or customer data. Content supplied in ChatGPT or Codex is still processed by OpenAI according to your account settings and its policies.

## Repository

- [`d365-email-studio/`](d365-email-studio/) — skill instructions and validator.
- [`plugin/`](plugin/) — plugin package and icons.
- [`cloudflare-mcp/`](cloudflare-mcp/) — read-only MCP server and development instructions.
- [`example/`](example/) — sample email files.

## Licence

[GPL-3.0](LICENSE). An independent project by Mylo Kaye, not endorsed by Microsoft.
