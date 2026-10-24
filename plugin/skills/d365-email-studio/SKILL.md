---
name: d365-email-studio
description: Edit or translate existing Dynamics 365 Customer Insights – Journeys real-time email HTML while preserving its structure, Dynamics expressions, tracking, compliance links, and Outlook markup. Use for constrained content edits, not email creation or redesign.
---

# Dynamics 365 Email Studio

Treat the supplied HTML as protected source. Return a complete updated HTML file containing only requested changes within the following allowlist. Never recreate, prettify, minify, sanitize, repair, or serialize the document through a DOM library. Make exact source edits and retain an untouched original for comparison.

## Allowed changes

- Wording inside existing body text elements, including headings, paragraphs, lists, link/button labels, footer wording, and hidden preheader copy. Translate text across existing inline elements without adding, deleting, reordering, or emptying elements or meaningful text runs. Preserve names and factual details unless the user requests changes.
- Existing ordinary link destinations (`href` on links and their Outlook VML counterparts), only when requested. Translation alone does not authorize changing destinations.
- Existing image `src` values, only when requested.
- Existing image `alt` values, including filling an empty `alt=""`. Never add an alt attribute where it is absent. Translate existing nonempty alt text with the email.
- Existing root HTML `lang` value to match a requested translation. Do not add a missing attribute. Right-to-left conversion is unsupported because it can require forbidden direction and layout changes; explain this limit before undertaking that conversion.

This allowlist is a capability boundary, not permission to change every allowed value. Refuse out-of-list edits and complete independent permitted edits if useful. Do not silently expand the list even when asked to redesign or fix layout.

## Protected source

Preserve every other byte, including doctype, namespaces, metadata/title, tags and their order, attributes and quoting, CSS, whitespace outside editable text, IDs, classes, dimensions, direction, tracking IDs, Dynamics data attributes, comments, conditional markers, Outlook tables/VML, and preheader padding/spacer entities and invisible characters.

Never add, duplicate, remove, or reorder content or elements. Do not erase text as a substitute for removing a section. A translation may change words and sentence structure while retaining the original meaning and the existing markup. If inline segmentation prevents a faithful translation, explain the conflict instead of restructuring it.

Preserve all dynamic expressions and template/control syntax exactly, in their original locations. Examples include `{{URL1}}`, `{{CompanyAddress}}`, `{{PreferenceCenter}}`, and `{{event_registration_1}}`; this is not an exhaustive list. Treat unknown template syntax conservatively.

Protect complete destinations containing dynamic expressions, and complete Dynamics functional URLs, including preference, unsubscribe, event-registration, and calendar links. Translate their visible labels but never replace their destinations. Preserve company/address tokens and compliance functionality; do not introduce new legal claims.

Source may be designer HTML or exported/rendered HTML. Preserve the form supplied; never convert between them or invent missing designer metadata, preheaders, namespaces, or Outlook fallbacks. In designer HTML, protect `meta type="xrm/designer/setting"`, CSS setting markers such as `/* @layout-max-width */`, `data-layout`, `data-layout-version`, `data-section`, `data-container*`, `data-editorblocktype`, generated IDs, lookup metadata and `data-image-file-id`. These are editor configuration, not translatable copy. Keep `<title>` unchanged; a subject change is outside this HTML allowlist.

Ordinary links may include `#_msdynmkt_donottrack=…,_msdynmkt_linkid=…`. Change only the requested destination before `#`, retaining the entire tracking fragment exactly. Do not decode, rebuild, remove, or regenerate tracking fields. Protect complete dynamic/functional URLs as before. When changing an image source, retain its asset metadata and flag that the existing `data-image-file-id` may still refer to the prior asset; do not alter it to reconcile the editor.

Outlook conditional comments can contain separate copies of visible buttons, links, and images. Update the matching copy of a requested label, ordinary destination, source, or existing alt value consistently. Do not replace an entire comment to edit its contents. Do not assume all occurrences of the same image URL represent one image. Identify the requested block and its corresponding Outlook fallback.

Longer translations may overflow fixed Outlook button dimensions. Preserve dimensions and report the potential rendering limitation; do not shorten meaning or change layout without explanation.

## Work and verification

1. Read the source and user request. Identify each requested editable occurrence, its Outlook counterpart, protected expressions, and functional links. Ask only about ambiguities that affect the actual edit.
2. Save a separate output file, preserving the original encoding and line endings. Escape replacement content for its HTML context; do not inject markup through text or attribute values. Keep HTML editing and validation local. You may fetch an existing image URL when needed for the requested edit, such as inspecting an image to describe it in an existing alt attribute. Do not upload the email HTML, its contents, or downloaded images to external services. Use clear surrounding context or a locally supplied image when sufficient; ask for the intended alt text if the image cannot be inspected or its meaning remains uncertain. This does not authorize adding a missing alt attribute.
3. Run the bundled local structural guard:

   `python3 <skill-folder>/scripts/validate_email.py ORIGINAL.html UPDATED.html`

   Fix rejected edits by returning to the source; never weaken the guard to make an output pass. Unsupported or ambiguous markup requires stopping the affected edit, not bypassing validation.
4. Review the actual diff against the request: translation completeness and meaning, no omitted content, intact tokens and functional URLs, and consistent Outlook counterparts. The guard checks the allowlist, meaningful text around protected tokens, adjacent image-wrapper fallbacks, and tracking-linked Outlook/standard buttons. Other fallback patterns require manual review. It cannot prove meaning, authorization, or full template recognition. Inspect those manually. Do not open the email in Chrome, Chrome DevTools, another browser, or a browser automation tool for this workflow. Do not request browser-tool approval. The inline plugin preview is the only preview step here; recommend a separate Dynamics preview/test-send to the user when rendering needs confirmation.
5. After validation, call `show_completed_email` with the absolute path of the completed output file in its `file` parameter. The ChatGPT file adapter uploads that file and passes a temporary file reference to the MCP tool; the Cloudflare Worker does not receive the local path or raw HTML. This tool call requests the preview and Copy HTML / Download HTML buttons inline in chat. A successful tool result does not prove that the host displayed the card; do not claim the inline preview is available unless its rendering is confirmed. If the tool or card fails, say that the inline preview could not be shown and provide the linked output file instead. Return a brief change summary and honest verification result. Never return an abbreviated document or claim Dynamics acceptance/rendering from a structural pass. Recommend Dynamics preview/test-send when rendering needs confirmation. Never publish or send email as part of this skill.

## Plugin MCP connection

The Cloudflare MCP guide and validator tools take no arguments. The local `show_completed_email` tool adapter takes the absolute output-file path, uploads the file to ChatGPT, and passes a temporary file reference to Cloudflare. The Worker does not fetch or store it. Never put raw email HTML, edited copy, or a local file path into a generic MCP tool argument or chat message. Use the bundled `scripts/validate_email.py` locally. If local execution is unavailable, explain that structural verification is blocked; do not claim a validation pass.
