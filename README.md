# Dynamics 365 Email Studio

Edit and translate existing **Dynamics 365 Customer Insights – Journeys** email HTML while preserving its layout, tracking, dynamic expressions, compliance links and Outlook markup.

[Website](https://mylokaye.me/d365-email-studio/) · [Support](https://mylokaye.me/d365-email-studio/support/) · [Privacy](https://mylokaye.me/d365-email-studio/privacy/) · [Terms](https://mylokaye.me/d365-email-studio/terms/)

## Choose a version

| Version | Requirements | Output and verification |
| --- | --- | --- |
| [Standalone skill](standalone/d365-email-studio-local/SKILL.md) | An AI assistant and the complete source HTML | Complete edited HTML in a code block, with assistant source comparison |
| [MCP-backed plugin](plugin/) | A compatible host, connector and local Python 3.9+ execution | Complete edited HTML file, automated source checks and an inline preview where supported |

The standalone skill is instruction-only. It requires no Python, scripts, packages, MCP server, connector, browser or local filesystem access.

## What it does

- Updates existing wording, headings, button labels and preheader copy.
- Translates content while preserving protected HTML and Dynamics expressions.
- Changes existing ordinary link destinations and image sources only when requested.
- Preserves functional destinations, tracking fragments and corresponding Outlook copies.

It does not create or redesign emails, connect to your Dynamics tenant, send messages or publish campaigns.

## Use the standalone skill

1. Open [SKILL.md](standalone/d365-email-studio-local/SKILL.md) and give its instructions to your AI assistant.
2. Supply the complete original email HTML and describe your requested edits.
3. Receive the complete updated HTML in a single code block, a brief change summary and an explanation of the source comparison performed.
4. Review the result in Dynamics preview and a test send before use.

An attachment can be provided if the host supports it, but is not required. The assistant must return the whole document without omitted sections or abbreviated examples. If the source is incomplete or too large to compare reliably, it should explain that limitation before editing.

For Codex skill discovery, place the `d365-email-studio-local` folder from [`standalone/`](standalone/) in your skills directory, then invoke `$d365-email-studio-local` in a new chat. In other hosts, supply the instructions directly. There is no build or installation script to run.

Example request:

> Use these skill instructions to translate this email into French. Preserve names, factual details, links, Dynamics expressions and the existing layout. Return the complete updated HTML.

### Verification limits

The standalone assistant compares the edited source with the original and reviews meaning, completeness and Outlook counterparts. This is an assistant review; it does not establish automated structural validation, byte-for-byte preservation, correct rendering or Dynamics acceptance. It must describe what it actually checked without claiming an automated pass.

## Use the MCP-backed plugin

1. Select the [Email Studio plugin](https://chatgpt.com/plugins/plugin_asdk_app_6adcc939af148191967f4b5854d9a4e2) in a compatible host. Access depends on the plugin's availability.
2. Supply an existing email HTML file and describe the changes you want.
3. Review the complete output file, diff and local validation result. In supported hosts, the completed file also appears in an isolated inline preview with copy and download controls.
4. Check the result in Dynamics preview and a test send before use.

This version requires local execution with **Python 3.9+** for its bundled validator. The preview is optional: when the host cannot reference the completed output or display the inline app, use the completed file link. Preview display content never replaces the original output bytes offered for download.

### Optional local validator workflow

These commands belong to the MCP-backed version and developer tooling. They are not prerequisites for the standalone instruction-only skill.

From the repository root:

```sh
python3 d365-email-studio/scripts/validate_email.py original.html --inventory > inventory.json
# Prepare edits.json from the request and inventory before editing.
python3 d365-email-studio/scripts/validate_email.py original.html --apply-plan edits.json --output updated.html
python3 d365-email-studio/scripts/validate_email.py original.html updated.html --plan edits.json
```

See the [edit-plan format](d365-email-studio/references/edit-plan.md). The validator binds exact edited occurrences to the original source hash, freezes destinations and image sources during translation, and checks protected source and Outlook counterparts. Inputs must be UTF-8; the original BOM and untouched line endings are preserved.

`--structural-only` is a diagnostic mode and does not complete the plugin's validation workflow. Automated checks do not prove translation quality, correct interpretation of the request, rendering or acceptance in Dynamics.

## Privacy

The standalone skill does not call external tools or services. The HTML supplied to your AI assistant is still processed according to that host's account settings and policies; using this skill does not mean the AI model runs offline.

For the MCP-backed version, editing and validation run locally. The Cloudflare server serves the guide, validator source and preview app without receiving raw email HTML. For an inline preview, the host passes a temporary file reference; the Worker does not fetch or store the email. Preview image requests can contact supported image hosts and trigger tracking pixels. See the [Worker documentation](cloudflare-mcp/README.md) for details.

## Repository

- [`standalone/d365-email-studio-local/`](standalone/d365-email-studio-local/) — instruction-only skill, optional Codex display metadata and licence.
- [`d365-email-studio/`](d365-email-studio/) — MCP-backed skill instructions, edit-plan reference and Python validator.
- [`plugin/`](plugin/) — connector-backed plugin configuration and bundled skill.
- [`cloudflare-mcp/`](cloudflare-mcp/) — Worker, inline preview and development instructions.
- [`example/`](example/) — sample email files.
- [`stress-tests/`](stress-tests/) — validator fixtures and regression checks.

## Development and verification

The Worker and plugin package version is **0.1.12**. The private App-backed plugin has its own version history; repository changes do not automatically update an installed plugin or deploy the Worker. The standalone skill is used directly from its instruction file.

Run the validator regression checks from the repository root:

```sh
python3 d365-email-studio/scripts/test_validator.py
python3 stress-tests/test_adversarial.py
python3 stress-tests/test_designer.py
python3 d365-email-studio/scripts/test_reliability.py
```

For Worker and preview development, run `npm ci`, `npx playwright install chromium`, `npm test` and `npm run build` in `cloudflare-mcp/`. Browser tests exercise the real preview and sanitizer with a test double for the host bridge, including cancellation, stale loads, local selection, image warnings and preservation of downloaded bytes. Actual host rendering and download behavior require host confirmation; see the preserved baseline in the [Worker README](cloudflare-mcp/README.md).

## Licence

[GPL-3.0](LICENSE). An independent project by Mylo Kaye, not endorsed by Microsoft.
