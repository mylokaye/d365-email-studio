# Working preview baseline

Read the “Confirmed working baseline — 25 October 2026” section of README.md
before changing the preview renderer, CSP, MCP Apps bridge, or download handling.
The user confirmed this setup works and explicitly requested extra care with
future changes. Preserve the baseline, make minimal scoped changes, run the
specified checks, and distinguish automated verification from actual host
confirmation. Do not reintroduce wildcard image origins: the desktop host
percent-encodes them into invalid CSP sources.
