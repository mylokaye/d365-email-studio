# Copilot email translation workbook

Version 0.1.0 implements this workflow: paste original email HTML, choose source
and target languages, download an Excel workbook, upload the completed workbook,
then download one source-preserving HTML file per language. It needs no MCP server.

The package is separate from the existing translator website and MCP plugin.
Python performs the file operations. The agent guides the conversation. Target
language cells start blank and the user supplies the translations.

## Build and run locally

Use Python 3.9+ with `openpyxl` 3.1.x. The Copilot host documents openpyxl as a
built-in package; check availability rather than installing packages at runtime.
Local development may use a virtual environment with `openpyxl>=3.1,<3.2`.

From the repository root:

```sh
python3 scripts/package_copilot_skill.py
python3 -m unittest discover -s copilot/tests -v
```

The builder creates `outputs/copilot-workbook/email-translation-workbook.zip`.
`SKILL.md` is at the ZIP root. It bundles the shared HTML guard unchanged from
`plugin/skills/d365-email-studio/scripts/validate_email.py`, with a checksum
manifest. Unzip the package to use it independently of this repository.

Example commands from the unpacked skill folder:

```sh
python3 scripts/translation_workbook.py prepare /path/to/original.html --source-language en-GB --targets de-DE fr-FR --output-dir job-001
python3 scripts/translation_workbook.py validate --job job-001 --workbook /path/to/completed.xlsx
python3 scripts/translation_workbook.py complete --job job-001 --workbook /path/to/completed.xlsx --output-dir completed-001
```

Every command returns JSON and a nonzero exit code on failure. `prepare` saves
the exact original bytes, job configuration and a blank workbook. `complete`
revalidates all languages and publishes individual HTML files, a ZIP when it fits
the host limit, and a validation report. Existing output directories are refused.
Use `--keep-html-lang` during preparation only when unchanged language metadata
is requested. By default, an existing editable root `lang` value changes per
target. A missing value is reported and never inserted.

## Install and verify in Copilot Studio

1. Create a test agent powered by the **Microsoft Copilot harness**. The classic
   topic-based runtime has different file and skill capabilities.
2. Open **Build → Skills → Add skill → Upload a skill** and select the ZIP.
3. Give the agent this instruction: “Use the email-translation-workbook skill
   for email translation workbook requests. Run its bundled scripts and report
   their actual results. Never rewrite the HTML or invent file links.”
4. Ask it to run `scripts/runtime_check.py`, then download the generated probe
   workbook and HTML. Upload the probe workbook again and ask it to run the check
   with `--uploaded` pointing to the actual uploaded file and a fresh output path.
5. Run the real workflow using a sample email and two target languages. Check
   the block/language counts, blank translation cells, file downloads and errors
   for a deliberately incomplete workbook.
6. Repeat in the intended published Microsoft 365 Copilot channel. Confirm the
   agent reads the uploaded workbook file itself, not just extracted text.
7. Review final files in Dynamics preview and test sends before wider use.

Uploading a ZIP is not evidence that all its scripts loaded or that attachments
and file links work. If the host cannot execute the scripts or provide actual
attachment bytes, stop at that capability failure. Do not substitute an AI-only
HTML rewrite. A documented serverless processing action could be added later,
but this package does not configure one.

## Workbook contract and boundaries

- One row is one editable text run, not necessarily an entire paragraph. Inline
  formatting and protected tokens can produce several rows. Context accompanies
  each row. Recognised Outlook copies share a translation row.
- Each requested target language has a yellow input column. Every required
  cell must contain literal text. Formulas, missing/duplicate IDs, changed source
  cells, altered metadata and changed language columns stop generation.
- The workbook is bound to the exact original source hash and inventory. Rows
  may be reordered as complete rows. Remove sheet protection using password
  `email-studio` if needed for sorting. Do not sort a language column alone.
  Sheet protection is only an accidental-edit aid; the importer checks the data.
- Template expressions in `{{…}}`, `{%…%}`, `${…}` and `[[…]]`, fixed whitespace,
  tracking, URLs, image sources, CSS and protected markup remain in the original.
  Unknown template formats need separate review. There is no universal template
  syntax detector.
- The first version refuses ambiguous/unpaired Outlook link and image copies,
  mismatched counterpart wording or inline segmentation, incomplete source and
  unsupported expression boundaries. It does not guess counterpart mappings.
- Translated runs must stay on one line without edge whitespace or new invisible
  formatting characters. Literal `<b>` is escaped text, not inserted markup.
- Inputs must be complete UTF-8 HTML under 5 MB. Limits are 10,000 blocks, 25
  targets, 30,000 characters per text cell, and 10 MB per host-download file.
  Very long cell text can require the Excel formula bar. Right-to-left workflows
  need a separate direction/layout design and are unsupported here.
- Structural checks do not establish language accuracy, meaning, Dynamics
  acceptance or Outlook rendering. Users can intentionally retain source wording
  for a name or brand by entering that wording in its target cells.

Keep the job's original HTML and configuration available during the conversation.
If working files disappear, recover the exact original and language choices and
recreate the job before importing the old workbook. The source fingerprint must
match. Do not reconstruct source from the agent's memory.

## Privacy and platform status

The code makes no network requests. Files supplied to Copilot are nevertheless
processed and retained within Microsoft's host and conversation environment.
This differs from the website's on-device translation and session-only drafts.
Microsoft currently documents attachment/generated-file retention of 28 days
after the last conversation activity. Tenant policies and feature availability
must be verified for the intended account.

Relevant official documentation, checked 18 November 2026:

- [Upload a skill package](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/skills-add-existing)
- [File attachments](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/attachments-overview)
- [Generated files and built-in Python packages](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/created-files-overview)
- [openpyxl styles](https://openpyxl.readthedocs.io/en/stable/styles.html)

Local tests cover unchanged-byte preservation (including BOM, CRLF and entities),
source-bound workbook identity, multiple languages, row reorder, duplicate IDs,
missing translations, protected tokens, text escaping, Outlook pairing, packaged
runtime checks and the repository's sample emails. Microsoft tenant execution,
real Excel application interaction and Dynamics rendering require live checks.
