# Dynamics 365 Email Studio

Edit and translate existing **Dynamics 365 Customer Insights – Journeys** email HTML while preserving its layout, tracking, dynamic expressions and Outlook markup.

[Website](https://mylokaye.me/d365-email-studio/) · [Support](https://mylokaye.me/d365-email-studio/support/) · [Privacy](https://mylokaye.me/d365-email-studio/privacy/) · [Terms](https://mylokaye.me/d365-email-studio/terms/)

## What it does

- Updates existing wording, headings, button labels and preheader copy.
- Translates content while preserving protected HTML and Dynamics expressions.
- Changes existing image sources and ordinary link destinations when requested.
- Checks the edited file against the original with a local Python validator.

It does not create or redesign emails, connect to your Dynamics tenant, send messages or publish campaigns.

## Use the standalone skill

The [standalone SKILL.md](standalone/d365-email-studio-local/SKILL.md) is instruction-only.
Give it to your AI assistant with the complete email HTML and your requested edits.
It returns the complete updated HTML in a code block, plus a brief change summary.
No Python, scripts, packages, MCP, connector, browser or local filesystem is required.

The assistant compares the original and edited source directly. This is model-based
review rather than automated structural or byte-for-byte validation. Rendering still
needs a Dynamics preview and test send.

For Codex, place this skill folder in your skills directory and invoke
`$d365-email-studio-local`. In other hosts, supply the instructions directly.
No ZIP build or installation script is needed.

## Use the MCP-backed plugin

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
python3 d365-email-studio/scripts/validate_email.py original.html --inventory > inventory.json
# Prepare edits.json from the request and inventory before editing (format linked below).
python3 d365-email-studio/scripts/validate_email.py original.html --apply-plan edits.json --output updated.html
python3 d365-email-studio/scripts/validate_email.py original.html updated.html --plan edits.json
```

The validator binds exact requested occurrences to the original source hash, freezes
links/images during translation, and checks protected source and Outlook counterparts.
See the [edit-plan format](d365-email-studio/references/edit-plan.md). Inputs must be
UTF-8; the original BOM and untouched line endings are preserved. For diagnostics
only, use `original.html updated.html --structural-only`. A structural-only pass does
not complete the workflow. Neither mode proves translation quality, correct request
interpretation, rendering or acceptance in Dynamics.

Run the local skill regression checks with:

```sh
python3 d365-email-studio/scripts/test_validator.py
python3 stress-tests/test_adversarial.py
python3 stress-tests/test_designer.py
python3 d365-email-studio/scripts/test_reliability.py
```

## Privacy

File editing and validation run locally. The Cloudflare MCP server serves the editing guide, validator source and preview UI; it never receives raw email HTML. For an inline preview, ChatGPT passes a temporary file reference to the server, which does not fetch or store it. Content supplied in ChatGPT or Codex is still processed by OpenAI according to your account settings and its policies.

## Repository

- [`d365-email-studio/`](d365-email-studio/) — skill instructions and validator.
- [`standalone/d365-email-studio-local/`](standalone/d365-email-studio-local/) — self-contained local skill.
- [`plugin/`](plugin/) — plugin package and icons.
- [`cloudflare-mcp/`](cloudflare-mcp/) — read-only MCP server and development instructions.
- [`example/`](example/) — sample email files.

## Licence

[GPL-3.0](LICENSE). An independent project by Mylo Kaye, not endorsed by Microsoft.

## Releases and verification

The local plugin package and Worker are version **0.1.12**. The linked private
App-backed plugin has its separate **1.0.3** history; rebuilding this repository
neither updates that installation nor deploys the Worker. The older `0.1.11` ZIP
is retained as a historical release.

Build and verify the MCP-backed plugin package from canonical skill sources:

```sh
python3 scripts/package_plugin.py
python3 scripts/package_plugin.py --check
python3 scripts/test_package.py
```

The builder synchronizes the bundled skill, checks manifest versions, includes all
skill references, and produces `d365-email-studio-plugin-0.1.12.zip` with a SHA-256
manifest. Archive paths, timestamps and ordering are deterministic. Verification
fails if the bundle or ZIP differs from the current canonical sources.

For the Worker and preview, run `npm ci`, `npx playwright install chromium`,
`npm test` and `npm run build` in `cloudflare-mcp/`. The browser tests execute the
real preview and sanitizer with a test double for the host bridge. They cover
cancellation, stale loads, local selection, image warnings and exact downloaded
bytes. Actual Codex-host image loading and download behavior still need host
confirmation after deployment; see the preserved baseline in the Worker README.
