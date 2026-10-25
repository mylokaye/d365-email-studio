# Cloudflare MCP server

Live endpoint: https://d365-email-studio.drbn8f85yx.workers.dev/mcp

The public, unauthenticated endpoint exposes two guide tools with no arguments:
`get_email_studio_guide` and `get_email_validator_source`. These return the repository
skill and Python validator. It also serves an inline HTML preview.
For an inline preview, ChatGPT passes a temporary file URL and ID to
`show_completed_email`; the Worker returns only the file reference metadata without fetching the email. The UI retrieves the file through ChatGPT's file API. The Worker has no email processing, storage bindings, outbound
application requests, or application logging. Never submit raw email HTML or customer
data to it. Normal Cloudflare network handling still applies to file references in requests.

Email editing and structural validation run locally using the plugin bundle.
The private plugin package lives in `../plugin/` and requires local execution.

Run `npm ci`, then `node sync-content.mjs` after skill/validator changes.
The build also bundles the inline preview into `src/viewer-content.js`.
Use `npm run dev` for local development and `npm run build` for a dry run.
To deploy later, authenticate Wrangler with `npx wrangler login` and run
`npm run deploy`. Initial deployment used the authenticated Cloudflare MCP API
because the local Wrangler CLI had no login. No credentials are bundled.

For Cloudflare Workers Builds connected to GitHub, use `main` with root directory
`cloudflare-mcp`, build command `npm run build`, and production deploy command
`npm run deploy`. Preview builds use the same root and build command. The build
regenerates `src/content.js` from the skill before bundling; the generated file
does not need to be committed. Running from the repository root fails because
the Worker configuration and dependencies live in this subdirectory.

Verification: run `npm test` for preview lifecycle and MCP privacy checks, and
`npm run build` for a Worker dry run. With a local Worker running, use
`node tests/smoke-mcp.mjs`; pass the MCP endpoint URL to check a deployment. From the repository root run:

```sh
python3 d365-email-studio/scripts/test_validator.py
python3 stress-tests/test_adversarial.py
python3 stress-tests/test_designer.py
```

The preview accepts only a completed file reference. It does not accept HTML or
replacement lists. Unsupported hosts use the validated output download link.

The inline UI uses the official MCP Apps SDK, versioned resources and a dedicated
UI origin. It renders a sanitized display copy inside a shadow root (no nested
iframe), and downloads the preserved output bytes through `ui/download-file`. When that
capability is unavailable, it opens a fresh original-file link using the host
link API (`ui/open-link` or the OpenAI `openExternal` extension).
File fetching is client-only, limited to 5 MiB with a 15-second loading deadline.
The local HTML picker reads directly in the app and never calls the Worker.

The preview permits HTTPS image sources and CSS background images from the
explicit origins in `UI_META.ui.csp.resourceDomains` (currently the Dynamics
template image host). Additional image hosts must be added there; this desktop
host percent-encodes wildcard hosts into invalid CSP sources. Image requests
go directly from the host browser to the image server and may trigger tracking
pixels. Scripts, frames, forms, link navigation, and other remote CSS resources
remain disabled. Downloaded HTML bytes are unchanged.

## Confirmed working baseline — 25 October 2026

The user confirmed that the inline preview displays images correctly in the
Codex desktop host after deployment `04f947f0-5685-480c-9edc-82ae6c15fcb1`.
The active resource is `ui://d365-email-studio/inline-preview-v9.html`.
The confirmation covers the example3 email's inline images and background image.
Other image hosts and other host applications have not been confirmed.

Preserve this baseline carefully:

- Keep the explicit image origin `https://emailui-usa1.mkt.dynamics.com`.
  Do not replace it with `https://*`: the desktop host converts that value to
  `https://%2A`, which is invalid CSP and blocks images.
- Keep the sanitized display copy separate from the original download bytes.
  Preserve the file-reference handoff, host bridge, and local validation workflow.
- Keep scripts, frames, forms, and email link navigation disabled.
  Image requests can contact image hosts and trigger tracking pixels.
- Make small, scoped changes. For renderer, CSP, bridge, or download changes,
  run `npm test`, `npm run build`, and the live smoke check after deployment.
  Check image and background loading in the actual Codex host before calling
  a replacement baseline confirmed; a standalone browser check is insufficient.
- Keep a recoverable Git checkpoint and the previous deployment version before
  changing this working path. Bump the resource URI when cache invalidation is needed,
  retaining legacy resource aliases.

Live check: `node tests/smoke-mcp.mjs https://d365-email-studio.drbn8f85yx.workers.dev/mcp`.
