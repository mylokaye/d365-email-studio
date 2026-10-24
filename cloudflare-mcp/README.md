# Cloudflare MCP server

Live endpoint: https://d365-email-studio.drbn8f85yx.workers.dev/mcp

The public, unauthenticated endpoint exposes two guide tools with no arguments:
`get_email_studio_guide` and `get_email_validator_source`. These return the repository
skill and Python validator. It also serves an inline HTML preview.
For an inline preview, ChatGPT passes a temporary file URL and ID to
`show_completed_email`; the Worker discards those inputs without fetching or logging
them. The UI retrieves the file through ChatGPT's file API. The Worker has no email processing, storage bindings, outbound
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

Verification: local and live MCP initialization and tool listing passed; both live
tool responses matched their source files; unexpected tool arguments were rejected.
The packaged validator passed targeted allowed-translation and protected CSS,
expression and compliance URL checks. The legacy `test_validator.py` runner is
incompatible with the current example fixture: its CSS replacement matches no text.
