# Email Studio — precise rebuild handover for Copilot Studio

Prepared 17 November 2026. Give this document and `SOURCE-REFERENCE.txt` to Copilot Studio together. The reference contains the actual application, styles, default email and regression fixtures. This document is the build instruction; the source resolves implementation details. `email-translator-source.zip` contains the same original files as a conventional project archive if useful outside the authoring conversation.

## Paste this instruction into Copilot Studio

Build a web app called **Email Studio** that faithfully reproduces the attached existing email translation application. Use the attached handover and source reference as the specification. Reproduce the current UI, interactions and source-preserving HTML editing. This is an HTML email wording translator for Dynamics 365 Customer Insights – Journeys, with an original/edited preview and editable translation cards.

Keep automatic translation on the user's device using the browser's `Translator` API. Keep manual editing fully usable when automatic translation is unavailable. Keep email content and all language drafts in memory for the current browser session only. Both choices have been explicitly confirmed by the owner.

Do not substitute a cloud translation service, store emails in a database, turn the app into a conversational agent, or redesign its interface. Platform-level Microsoft sign-in and hosting may surround the app; there is no additional app-specific account workflow. There is no requirement for a Dynamics connector, Dataverse table, Power Automate flow, external AI provider or API key.

First assess whether this Copilot Studio environment can support the required source-range parsing, browser translation API, isolated iframe preview, clipboard access and in-memory state using approved dependencies. Identify any unsupported requirement precisely. Do not silently substitute different behaviour or describe a simulated feature as implemented. Then build in stages: exact shell and default email; import/extraction/source-preserving export; manual edits and per-language drafts; safe preview and selection; real on-device translation; dialogs, responsive behaviour and acceptance checks. Complete all stages before calling the rebuild equivalent.

## 1. Baseline and boundaries

Reference app: https://email-studio-translator.mylokaye.chatgpt.site

Owning source: `sites/email-translator/` in the supplied repository. The source snapshot bundled with this handover is authoritative for this rebuild. Do not confuse it with the repository's standalone assistant skill, MCP plugin, Python validator or Cloudflare preview. Those are separate products with different capabilities.

The app edits wording in an existing HTML email. It preserves the source layout and protected markup, lets the user compare the original and edited versions, and returns the complete edited HTML through a copy dialog. It starts with a real sample email already loaded. It does not create email designs, edit subject metadata, edit destination URLs, edit image URLs, send emails, publish campaigns or write to a Dynamics tenant.

Verification for this handover: the local application source was inspected and its 28 Vitest tests passed on 17 November 2026. The live URL returned HTTP 403 to the available fetch tool and no controlled browser was available. Accordingly, this is a source-backed rebuild specification, not a fresh visual certification of the deployed website. Real browser language-pack translation, Dynamics acceptance and Outlook rendering have not been established by these tests.

## 2. Screen structure and initial state

Use one workspace, without a dashboard, onboarding screen, navigation sidebar, large visible title, extra footer, translation summary or chat UI.

Desktop layout:

| Left panel | Right panel |
| --- | --- |
| Heading: **Preview** | Heading: **Translations** |
| **Import**, **Export**, then **Original / Edited** segmented control | Target language picker, **Translate**, reset icon; a Source picker appears only when source detection has no result |
| Scaled, scrollable email display on a muted canvas | Conditional translation feedback, then a scrollable list of numbered editable cards |

Initial state:

- Load `src/default-email.html` exactly, through `src/sample.ts`. Preserve the supplied email artwork, structure and text, including “Form. Function. Fit. Fabulous.” Do not recreate it approximately or use a different template.
- Preview version is **Edited**; before edits it shows the original email.
- No target language is selected. Picker placeholder: **Select language**.
- Text areas already contain the original extracted wording. They are not empty translation boxes and there is no separate visible original-text paragraph above each input.
- No translations or saved drafts exist. Reset all is disabled.
- Bulk Translate and each card's Translate action are unavailable until prerequisites are met, while manual inputs remain usable.
- On a small viewport, show **Preview / Translations** at the top, with **Translations** selected initially. Show only the selected panel.

Application document title: **Email Studio — Text Translator**. Include a visually hidden `h1` reading **Email Studio**.

## 3. Visual specification

Use the supplied `src/style.css` as the exact styling reference. The following values explain the main dimensions; they are not a replacement for the full stylesheet.

| Property | Current value |
| --- | --- |
| Font | Inter Variable; Arial, Helvetica, sans-serif fallback |
| Desktop page padding | 30px; 24px at widths up to 1100px; 16px at widths up to 760px |
| Workspace columns | `minmax(0, 1.1fr) minmax(0, 1fr)` |
| Panel gap | 14px |
| Desktop workspace height | Fill available viewport height within a `100dvh` main element |
| Panel | 1px border, 12px radius, clipped outer overflow |
| Panel heading | 19px type, approximately 63px minimum row height |
| Panel horizontal inset | 20px, reducing to 16px at widths up to 1100px |
| Standard control | Minimum 40px high, 8px radius, 14px label |
| Compact card action | Minimum 32px high |
| Touch controls | Minimum 48px high for coarse pointers |
| Card | 1px border, 9px radius, 16px padding, 14px bottom spacing |
| Text input | At least 16px font, 1.5 line height, vertical resize, approximately 3–12 lines of height |
| Modal | Up to 720px wide, 26px padding, 12px radius |
| Confirmation modal | Up to 480px wide |
| Modal textarea | 280px initial height, 140px minimum, at most 50dvh; 16px monospace type |
| Modal action | Minimum 90px wide and 50px high |

Main colour tokens:

| Token | Light | Dark |
| --- | --- | --- |
| Page/panel background | `#ffffff` | `#121714` |
| Main text | `#171c19` | `#e7ece9` |
| Primary green | `#174f37` | `#5ec291` |
| Primary button text | `#ffffff` | `#092216` |
| Panel border | `#d4d9d6` | `#333e37` |
| Divider | `#dde1df` | `#2c3630` |
| Muted text | `#5c635e` | `#a3ada7` |
| Preview canvas | `#edf0ee` | `#0c100e` |
| Edited card background | `#e3f4e9` | `#203b2b` |
| Edited card border | `#2e6f4e` | `#4ca378` |
| Input background | `#ffffff` | `#151c18` |
| Input border | `#707872` | `#6f7a73` |
| Focus ring | `#438f68` | `#6fd4a3` |
| Validation error | `#a33e31` | `#ff897a` |

Follow the OS/browser light or dark preference; there is no app theme switch. Keep the displayed email's own colours rather than recolouring the email for dark mode. Use the existing Lucide icon equivalents: clipboard/paste for Import, upload arrow for Export, rotate-counterclockwise for reset, linked-chain for Outlook linked, X for close, and rotating loader for Cancel while translating.

At widths up to 760px, use a single panel with the sticky mobile workspace switch. The translations view uses page scrolling. The preview panel is approximately `100dvh - 6.5rem` high, with a 320px minimum. Preserve state when switching views. When an individual panel is narrower than 448px, stack language controls vertically, even on a larger viewport. Controls and card action rows can wrap without clipping labels.

## 4. Import and document replacement

The visible import workflow is **paste HTML**, not file upload. An unused file-reading helper exists in the source; it is not a visible app feature.

1. Clicking **Import** opens **Import HTML** as a modal, with an X close button at the top right.
2. Focus the HTML textarea immediately. Placeholder: `<!doctype html>…`. Disable spelling correction, autocapitalisation and autocomplete.
3. Show one primary **Import** button at the bottom right. Disable it until the source contains a case-insensitive opening `html`, `body`, `table`, `div`, `p` or `h1`–`h6` tag boundary. This is the existing permissive recognition rule, not a strict full-document validator. Empty/plain text input does not produce an empty-input warning.
4. At submission, enforce the existing size limit: reject UTF-8 content exceeding `5 * 1024 * 1024` bytes. Message: **Paste an HTML email smaller than 5 MB.**
5. Parse without changing the original string. If parsing fails, show an inline error, keep the dialog open and refocus the source input.
6. If there are changed fields in any language draft, or a target language is selected, open a second confirmation: **Replace email?** / **Current translations and language drafts will be discarded.** Actions: **Cancel**, **Replace**. Cancellation leaves the existing email and drafts intact.
7. On successful import, cancel stale translation work, replace the source/field inventory, clear every draft, target selection, field error and active card selection. Reset preview version to Edited. Close the import dialog and clear its pasted input.
8. Announce `pasted-email.html loaded (N fields).` using a polite status region.

Closing the import dialog without importing clears its error and pending replacement, but retains the pasted text for reopening. Dialogs close with X, Escape or an outside click. Confirmation dialogs initially focus **Cancel**; import/export dialogs initially focus their textareas. Preserve native modal keyboard containment and normal focus restoration.

## 5. Extract editable wording without rebuilding HTML

Port `src/email.ts` faithfully. Use a parser with source locations, currently `parse5`, to discover editable string ranges. **Never export by serializing the parsed DOM.** Parser repair, indentation, attribute order, quote normalization and entity normalization must not rewrite protected source.

The internal email record retains the complete immutable original string, fields, notices and an optional range for the existing quoted root `html` language value. Each field has a stable source-offset-based ID, original decoded wording, label, kind, one or more original ranges and raw substrings, an Outlook pairing flag, and optional ordered sections. A section maps one editable line back to its own source range(s).

Extraction rules:

- Extract readable text in the permitted email text contexts. Labels are **Heading**, **Link / button**, **List item**, **Body text**, **Text block**, or **Image description**, following the original code's context priority.
- Exclude the `head`, `style`, `script`, `title`, `textarea`, `noscript`, `template`, `svg`, `math`, `iframe`, `object` and `xmp` contexts. The HTML title/subject is protected. Ordinary comments are protected.
- Protect complete expressions in `{{…}}`, `{%…%}`, `${…}` and `[[…]]`; extract editable wording around them. Incomplete/unrecognised expression delimiters cause the affected text run to remain read-only.
- Preserve fixed whitespace entities, nonbreaking spaces and protected invisible formatting characters in the source. Decode display wording for inputs, but keep untouched raw entities unchanged in export.
- Extract suitable quoted, nonempty `img alt` values as Image description fields. Expressions or protected segmentation make them read-only. If conditional Outlook image copies exist, do not offer image description edits.
- Group compatible text runs into their containing Dynamics `data-editorblocktype="Text"` block, or nearest supported text block, using one textarea line per source section. Preserve inline emphasis, spans, breaks, paragraphs and tags in their existing positions. Do not merge unrelated paragraphs or group guarded expression-separated/Outlook-linked runs across their boundaries.
- Keep punctuation-only visible sections when present. Grouped section display text normalizes whitespace as the reference does; unchanged sections still export their original raw source.
- Sort fields by source order and reject overlapping ranges.
- `<!--[if…]>` Outlook handling must follow the exact conditional-comment pattern in the source, not a generic comment translation rule. Only safely paired hidden/normal labels are editable. Match shared `data-msdyn-tracking-id`, exactly two link owners, corresponding part/context and identical original wording. Store both ranges under one field and show **Outlook linked**.
- If counterpart mapping is missing, inconsistent or ambiguous, keep the guarded wording read-only, including the corresponding unsafe visible candidate; never guess a pairing by global text replacement.

Existing nonblocking notices, displayed above the cards when applicable:

- **Some complex markup is read-only.**
- **Unmatched Outlook text is read-only.**
- **Image descriptions with Outlook copies are read-only.**
- **No editable text found.**

The exact text-tag list, grouping guards, entity recognition and pairing algorithm are in the source reference and should be carried over rather than approximated from this description.

## 6. Manual editing, selection and language drafts

For each field, render a card with its 1-based number, context label, optional Outlook linked indicator, **Translate** action, and an input containing the current draft value or original text. For grouped fields, show **N lines — keep one section per line.**

A value counts as edited when it differs from its original. A nonempty edited value gives the card its green changed treatment and an accessible **Edited** status. Edited cards use **Re-translate** and gain a reset icon labelled **Reset block N**. Reset restores that field's original wording for the current target only. It does not affect other fields or language drafts.

Clicking or focusing a card selects it, highlights its border, locates its wording/image in the current preview version, scrolls that element into the iframe viewport and outlines it. Repeated selections should work. Grouped text uses the shared containing element where possible. The preview has no click-to-edit feature; selection flows from card to preview. Scrolling must not drag the outer page away from a mobile editor. Respect reduced-motion preference and ignore stale scroll results.

Language list and codes: English `en`, French `fr`, German `de`, Spanish `es`, Italian `it`, Portuguese `pt`, Dutch `nl`, Danish `da`, Swedish `sv`, Polish `pl`, Czech `cs`, Finnish `fi`, Norwegian `no`, Japanese `ja`, Korean `ko`, Chinese `zh`.

Target picker order: German, French, Spanish, Polish, Italian, Chinese, followed by a **More** group containing the remaining languages in the source list's order. Exclude the current source language from target options. Source choices use the complete source list.

Keep drafts separately by target code, in memory:

- Switching French → German saves the French edits and displays the existing German draft or untouched originals. Returning to French restores its edits.
- Never relabel French wording as German just because the picker changed. Export/Edited preview use only the active language's values.
- Manual edits made before choosing any target belong to the first selected target; do not duplicate them across languages.
- A selected target alone counts as dirty, even without changed wording. Changed fields in inactive drafts also count as dirty.
- Changing target cancels current translation, clears displayed field errors/status and active selection, and changes the existing root `lang` value in the edited output when applicable.
- Register the browser's unload confirmation while dirty. Do not imply this saves work.

**Reset all** is a reset icon next to bulk Translate. Disable it only when no language is selected and no draft has changes. Its confirmation is **Reset all translations?** / **This will discard all translations and language drafts, and reset the target language.** Actions: **Cancel**, **Reset all**. On confirmation, cancel translation, clear every language draft and target selection, clear validation errors, retain the loaded original email, and announce **Reset to original.**

There is no autosave, localStorage, IndexedDB, sessionStorage, server persistence, document history or cross-device recovery. Refreshing/reopening starts from the bundled sample. Mobile view changes and language switching within the open app retain current in-memory state.

## 7. Automatic translation: device only

Port `src/on-device.ts` and `src/useOnDeviceTranslation.ts`. Use `globalThis.Translator` only when both `availability` and `create` exist. No cloud fallback or deprecated `window.ai.translator` fallback. Do not use Copilot's conversational response as the translation engine.

Source detection uses `franc-min` plus ISO-639 mapping over up to 10,000 characters of extracted text fields, excluding alt text. If fewer than 80 letters are present, detection is uncertain, the top two scores differ by less than 0.1, or the detected language is outside the picker list, fall back to the existing root HTML language's primary language via `Intl.Locale`. If no usable result exists, show the **Source** picker with **Select…**. When detection/fallback has a result, hide the Source picker. Do not add a new permanent source label or override control as part of this exact rebuild.

Check availability whenever document/source/target changes or Retry is selected. Ignore stale checks, cancel the previous job, and impose the existing 8-second availability timeout. Supported API states are `available`, `downloadable`, `downloading`, `unavailable`; checking/failure are separate UI states. Downloadable/downloading pairs can be started by a user gesture.

Bulk **Translate** translates only untouched fields: no draft entry or a value equal to the original. A card's Translate/Re-translate targets just that field and translates its original wording, not the user's current draft wording. Both run sections sequentially. Send only editable plain wording for each section to the translation API—no complete HTML, protected expressions, hrefs, tracking or image metadata.

Start translator creation directly inside the click gesture before awaiting. Display language-pack download progress when reported; clamp it to 0–1. Once running, bulk Translate becomes **Cancel** with a loader. Other translation actions are unavailable, but the user can still manually edit.

Trim each returned section and flatten internal newlines to spaces; rejoin grouped sections with exactly one newline. Validate using the same export function before applying. Reject a non-string result and invalid/empty/protected-token output.

Protect edits from asynchronous races: capture document, target and expected field value. Skip any result if the document/target changed, the job was cancelled or the user's value no longer matches the captured value. Check before and after awaiting translation, and guard the reducer application too. Never overwrite a newer manual edit. Cancel stops pending creation/translation even if the browser ignores its abort signal; destroy sessions, including sessions created late after cancellation. Retain completed translations on cancellation or failure.

Feedback follows the current app: the general status paragraph is hidden while busy; Cancel and any download progress indicate activity. The hook tracks preparation/progress text internally, but do not invent a new visible progress dashboard. After completion, show a message only when there is a relevant result such as skipped manual edits, cancellation or failure.

Important messages and reasons:

| Situation | Copy |
| --- | --- |
| Unsupported browser status | On-device translation is unavailable in this browser. |
| Unsupported action hint | Automatic translation is unavailable in this browser. You can edit the wording manually. |
| Missing source | Choose the source language first. |
| Missing target | Choose a language to translate into. |
| Busy | A translation is already in progress. |
| Checking | Checking whether this language is available. |
| Check failed status | Language check failed. Try again. |
| Check failed hint | Language check failed. Use Retry to check this language again. |
| Unsupported pair status | This language pair is unavailable. |
| Unsupported pair hint | This language pair is unavailable. Choose another language. |
| Bulk has no untouched fields | All blocks have been edited. Use Re-translate on an individual block. |
| Cancelled | Translation cancelled. |
| Failure | Translation stopped (N completed). [reason] |
| Manual edit skipped | 1 manually edited block was kept. / N manually edited blocks were kept. |

Show **Retry** only for a failed availability check. Translation action hints must work on hover and keyboard focus. Keep unavailable translation buttons keyboard reachable with `aria-disabled` and guard their click handler. Native disabled controls are used where the current source uses them, including inactive Reset all and the empty import action.

## 8. Source-preserving export and validation

Export is a toolbar action opening **Export HTML**. It is not a download button. Validate all changed fields; stop at the first invalid field, focus it, show its inline error and the global alert **Fix highlighted errors before exporting.** If output generation fails, show the error and do not open the export dialog.

Patch only allowed source spans, in descending offset order:

1. For each changed field/section, verify the current original source substring still equals its captured raw range. Fail if it does not.
2. Escape replacement text: ampersand, less-than, greater-than, double quote and apostrophe become their HTML entity equivalents. Typed `<b>word</b>` must appear as literal text, not become markup.
3. Apply the same replacement to all ranges of a safely paired Outlook label.
4. Skip unchanged fields and unchanged sections so their original entity spelling and whitespace remain intact.
5. If a target is selected and an existing quoted root `html lang` value was captured, replace just that value. Validate the language code. Do not insert a missing `lang`, add `dir`, rewrite regional metadata elsewhere, or change head/title metadata. Selecting a language alone can therefore change the existing root lang value before any wording is translated.

Everything outside these ranges stays exactly as supplied: doctype, BOM, CRLF/LF, comments, CSS, layout, attributes, IDs, `data-*`, namespaces, VML, conditional wrappers, dynamic expressions, destinations, compliance/preference/unsubscribe URLs, image sources and tracking fragments. Repeated identical text elsewhere must not change. This is deterministic patching, not an AI rewrite of the document.

Validation/error copy:

- Empty/nonvisible replacement: **Translation cannot be empty. Use Reset to restore original.**
- Newly entered template delimiters or prohibited invisible formatting: **Enter plain text only (no template tags or invisible characters).**
- Wrong grouped line count: **Keep all N sections on separate lines.**
- Empty grouped section: **Each text section needs text. Use Reset to restore original.**
- Source range mismatch: **The original source no longer matches this text block. Reload the email.**
- Invalid language: **Choose a valid language.**

Validate a changed field on blur and clear its previous error when edited again. Invalid draft values stay in the editor for correction. The existing app attempts the complete Edited output in one operation; if any draft is invalid, the displayed edited source falls back to the original source rather than applying a partial set of edits. Reproduce this behaviour, and never allow invalid source into export.

The export dialog contains the entire output in a read-only textarea, initially focused and selected, an X close button and a **Copy** action at the bottom right. Clipboard success: **HTML copied.** Failure: select/focus the HTML and show **Copy failed. Select the HTML and copy it manually.** Never truncate output or add markdown fences, explanations or omission markers inside the HTML. Editing after closing and reopening must produce a fresh output snapshot.

## 9. Safe preview is separate from export

Port `src/preview.ts` and `src/EmailPreview.tsx`. The Original view renders a disposable sanitized copy of original source; Edited renders a disposable sanitized copy of the current active language output. Neither sanitized document is ever used for export.

Use the native `Document.parseHTML` sanitizer when available, otherwise DOMPurify with equivalent restrictions. Remove active and navigational elements/attributes according to the supplied lists. Block scripts, nested frames, forms, links as navigation, unsafe sources and external connectivity beyond permitted images. Iframe sandbox is `allow-same-origin` without scripts; referrer policy is `no-referrer`. Keep the exact restrictive preview CSP from the reference. The app must inspect its own sanitized iframe to locate a selected field.

Allow preview `img src` only for HTTPS and data PNG/JPEG/GIF/WebP. Other sources are removed. HTTPS image requests and CSS image loads permitted by the preview CSP can contact image hosts, including tracking endpoints; do not promise that previewing makes no network requests. Email wording is not submitted to an app server or cloud translator. Model/language-pack downloads may also need network access.

Keep the iframe's rendered email width at least 620px (or the larger document width), then scale down to the available canvas width with a maximum scale of 1. Preserve readable email layout proportions rather than forcing a responsive rewrite of the email. Retain preview scroll position across edits, reapply selected-element outlining, prevent stale preview results replacing current content, and respect reduced motion. Preview annotations and injected CSS never enter export.

Loading copy: **Loading preview…** Failure copy: **Preview unavailable. Original HTML is intact.** A preview failure must not destroy the source or block otherwise valid export.

Browser preview is not an Outlook renderer and does not prove Dynamics validation or actual send rendering.

## 10. Accessibility and interaction parity

- Use semantic headings, labelled inputs, native selects and modal dialogs, and independent named workspace sections.
- Preserve the mobile workspace group's accessible name **Workspace view** and preview switch's **Preview version**; expose selection with `aria-pressed`.
- Give each textarea a label **Translation block N**, the appropriate source/target `lang`, linked help/error descriptions and `aria-invalid` when needed.
- Show errors with text as well as colour. Keep a clear visible focus ring. Do not make icon meaning depend on visual recognition.
- Tooltips open on hover/focus, remain reachable under the pointer and can be dismissed with Escape.
- Use polite live status messages for import, reset, clipboard and translation feedback; alerts for blocking errors. Mark the translation list busy while running.
- Keep translated-card state available to screen readers. Honour reduced motion, forced-colours select behaviour and touch target sizing.
- Check at 320, 390, 820, 1219 and 1440px, plus keyboard-only use and dark mode. No horizontal control/label clipping.

## 11. Acceptance checks before calling this equivalent

Use the supplied regression tests and fixtures as executable examples. Preserve their guarantees even if Copilot Studio needs a different test framework. Record actual outcomes, distinguishing simulated translation from a real browser translator.

| Check | Required outcome |
| --- | --- |
| Initial page | Exact default email; two panels on desktop; Edited selected; originals prefilled; no target |
| Mobile | Translations initially; switching to Preview and back preserves all edits |
| Import empty/plain text | Import disabled, no empty-input warning |
| Import >5 MiB | Size error; current email intact |
| Replace dirty document | Explicit Replace confirmation; Cancel retains all drafts |
| No-op export | Original string unchanged, including BOM, CRLF, entities and metadata |
| Repeated wording | Only selected source occurrence changes |
| HTML-like wording | Escaped as literal text; no element injection |
| Dynamic content | Expressions and spacing entities unchanged; surrounding wording editable |
| Protected contexts | No title/head/script/style/template/ordinary-comment editing |
| Grouped source | Original inline tags/sections intact; wrong line count and blank sections rejected |
| Unchanged grouped section | Retains raw original entity spelling |
| Outlook pairing | One card updates both safe counterparts; unsafe mapping stays read-only with notice |
| Language isolation | French and German drafts restore independently; export uses active draft only |
| Pre-language manual edit | Moves into the first selected target without duplication |
| Root language | Only existing quoted root lang value changes; absent lang remains absent |
| Reset one/all | One affects current field; all confirms and clears all language drafts and target |
| Refresh | No recovery from persistent storage; default email loads again |
| Unsupported browser | Manual editing/export work; accurate unavailable feedback; no cloud call |
| Translation pair check | Loading/unavailable/error/retry behave accurately; timeout does not leave an indefinite check |
| Translation input | Only plain editable sections; HTML, URLs and expressions excluded |
| Bulk translation | Only untouched fields; original wording is translation source |
| Edit during translation | New manual value survives both pending and late results |
| Cancel/change language/import | Stale results never apply; completed current draft edits retained as appropriate |
| Translation errors | Invalid output rejected; completed blocks retained; usable retry/manual workflow |
| Export dialog | Complete read-only output, selected; Copy success and manual fallback work |
| Preview isolation | Sanitized copy, blocked active content/navigation; exported original unaffected |
| Selection | Card focus/click scrolls and outlines correct preview content without scrolling outer editor away |
| Production host | Actual Translator permission policy/user gesture, iframe access and clipboard verified on the published host |
| Rendering | Keyboard, narrow layouts, dark mode and reduced motion checked; Dynamics/Outlook verification reported separately |

All four supplied HTML regression fixtures must parse with at least one editable field and round-trip exactly when untouched. All 28 current unit tests should pass after any supported source port. Tests that stub translation do not establish that a real language pack works in the published app.

## 12. Implementation reference and Copilot Studio constraints

Existing implementation: React 19, TypeScript, Vite, `parse5`, DOMPurify, `franc-min`, `iso-639-3`, Lucide React and Inter Variable. Exact package manifests and configuration are included. Use equivalent approved platform components only when they preserve the observable behaviour and source invariants. Do not add backend storage merely because the app builder offers a data model.

| Source | Responsibility |
| --- | --- |
| `App.tsx` | Workspace, document lifecycle, preview output, import/export/reset orchestration |
| `email.ts` | Source locations, extraction, guarded Outlook pairing, grouping, validation, escaped range patching |
| `translation-drafts.ts` | Target-isolated in-memory drafts and stale-result reducer guard |
| `TranslationPanel.tsx` | Language UI, editable cards, block selection, reset confirmation |
| `on-device.ts`, `useOnDeviceTranslation.ts` | Detection, native API, availability, download, cancellation and race protection |
| `OnDeviceControls.tsx` | Conditional status, Retry and download progress |
| `EmailPreview.tsx`, `preview.ts` | Scaled isolated preview, sanitization, selection and scroll state |
| `PasteHtmlDialog.tsx`, `HtmlExportDialog.tsx` | Paste import and full-source copy export |
| `Dialog.tsx`, `Hint.tsx` | Shared modal and accessible hint interactions |
| `style.css` | Full visual, responsive, dark-mode and reduced-motion reference |
| `languages.ts`, `sample.ts`, `default-email.html` | Exact picker list and initial content |
| `*.test.ts`, `tests/fixtures/` | 28 current regression tests and real email examples |

Copilot Studio Apps is currently a preview experience. Microsoft documents natural-language app creation, file/screenshot context, interactive preview, conversation-based changes, Microsoft hosting and governed connections. Its code view is read-only and available capabilities depend on the environment. These docs do not establish that the specific native Translator API, parser packages or inspectable iframe setup required here are supported. Treat those as a feasibility check in the actual tenant, including embedded preview and published-host permissions. If a required feature cannot work, report the precise gap and request a decision before changing the agreed behaviour.

Microsoft references, checked 17 November 2026:

- [Apps overview](https://learn.microsoft.com/en-us/microsoft-copilot-studio/apps-experience/apps-overview)
- [Create an app](https://learn.microsoft.com/en-us/microsoft-copilot-studio/apps-experience/create-app)
- [Apps FAQ and limitations](https://learn.microsoft.com/en-us/microsoft-copilot-studio/faq-apps)

At completion, provide the working app, acceptance results, any known platform differences and a clear separation between implemented, simulated and unverified features. Keep the attached reference and the owner's confirmed device-only/session-only choices as the baseline throughout refinement.
