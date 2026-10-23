# Submission preparation

Version 0.1.2. This public-upload copy preserves the private plugin source.
Publisher: Mylo Kaye; all supported countries; free with no payments (confirmed).

## Review test coverage

Five positive cases cover constraints, Dynamics protections, validator download, local verification and Outlook fallbacks. Three negative cases cover sending, redesign and remote HTML processing. These are drafts for review: host-level automated case runs are NOT RUN. Live endpoint and source equality checks previously passed; they do not establish host case results.

## Remaining requirements

- Real demo recording URL: missing. No recording has been fabricated.
- Reviewer access instructions: enter through secure dashboard fields, not this ZIP. The MCP endpoint is public and needs no credentials. No Dynamics tenant is needed. Python 3/local execution is needed for the skill.
- Configure the saved draft's MCP connection and run all cases against that exact version.
- Developer verification, scans and legal/policy attestations must be completed in the portal.

## Demo walkthrough to record

In Codex with the plugin selected, show: (1) asking which email changes are supported and the actual guide tool response; (2) requesting the validator and showing its source; (3) requesting a small wording edit to a synthetic email and showing the separate output and real local guard result; (4) requesting Cloudflare HTML processing and showing the local-only explanation. Keep credentials and unrelated private content out of the recording. Host the recording at a public/reviewer-accessible link and add the actual URL as review.demo_recording_url.
