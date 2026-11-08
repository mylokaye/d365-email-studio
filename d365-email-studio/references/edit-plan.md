# Request-scoped edit plan

Read this when preparing `edits.json`. Keep the inventory and plan local: they contain email content. No additional user approval is required for clear edits already requested.

## Prepare before editing

```sh
python3 <skill-folder>/scripts/validate_email.py ORIGINAL.html --inventory > inventory.json
```

The inventory includes the SHA-256 of the untouched UTF-8 source, editable fields (IDs, exact `before` values, character ranges and enclosing node IDs), links with protection reasons, recognised counterpart groups, and conditional image/link nodes. Ranges are Python character offsets, not byte or UTF-16 offsets; use the supplied IDs and apply command instead of calculating offsets manually. Do not select every field merely because it is editable.

Inspect the source around each requested occurrence. A missing protection reason means a link needs classification, not that it is ordinary. Freeze functional destinations, unknown template syntax and uncertain links. For an affected pattern the inventory cannot pair, identify all copies in the original source. Use a `group` decision to map them; use `standalone` only when there is genuinely no corresponding copy. Detected groups cannot be overridden by manual decisions. If existing counterpart values differ, stop the affected edit rather than silently reconciling them.

## Format

The following is illustrative: obtain the hash, field IDs, node IDs and exact values from the actual inventory.

```json
{
  "version": 1,
  "source_sha256": "<inventory source_sha256>",
  "mode": "translation",
  "request": "Translate the greeting and link label into French.",
  "edits": [
    {
      "id": "text:8",
      "before": "Hello",
      "after": "Bonjour",
      "reason": "Greeting explicitly selected for translation."
    },
    {
      "id": "text:11",
      "before": "Read more",
      "after": "En savoir plus",
      "reason": "Link label explicitly selected for translation."
    }
  ],
  "counterpart_decisions": [
    {
      "type": "standalone",
      "members": ["node:10"],
      "reason": "Inspected this text link and surrounding conditional blocks; it has no Outlook counterpart."
    }
  ]
}
```

- `mode`: `translation` freezes every `href` and `src`, including attempts to list them in the plan. Use `edit` for an explicit destination/image update or a combined translation and destination/image request; it does not grant blanket permission.
- `request`: preserve the actual user request. Each edit's `reason` must explain its connection to that request; the guard cannot infer intent from this prose.
- `edits`: exact raw HTML value replacements, one per inventory field ID, with the exact `before` value. Include every requested Outlook copy. Preserve edge whitespace and protected entities/expressions. Escape text and attribute values appropriately, e.g. `&amp;` in URLs and `&quot;` in double-quoted attributes. Do not double-escape existing entities. Do not insert tags.
- Destination edits additionally need `"purpose": "ordinary"` and a reason documenting the requested replacement and why the original is not functional. Automatically protected destinations cannot be edited even with this classification. Tracking fragments remain byte-for-byte fixed.
- `counterpart_decisions` is optional when recognised groups cover every affected link/image. Otherwise provide `{"type":"group","members":["node:…","node:…"],"reason":"…"}` for matching copies or a single-member `standalone` decision. A manual group must contain comparable link nodes or image nodes. Review all copies, not just those carrying the changed attribute. All changed link/image values need coverage; unresolved occurrences fail validation.

## Apply and verify

```sh
python3 <skill-folder>/scripts/validate_email.py ORIGINAL.html --apply-plan edits.json --output UPDATED.html
python3 <skill-folder>/scripts/validate_email.py ORIGINAL.html UPDATED.html --plan edits.json
```

Application validates before writing and creates the output exclusively. Use a new output filename when one already exists. The original, UTF-8 BOM and untouched line endings remain intact. Any later change to the output must match the pre-edit plan and still pass all source guards. Revise a plan only to correct a mistaken interpretation or accommodate a new user instruction, then regenerate from the original.

The two-file command without `--plan` fails. `--structural-only` explicitly checks only structural preservation and known counterpart consistency; it does not complete the skill workflow. The Python `validate(original, updated)` API retains this structural-only behaviour for existing regression callers; pass a plan as its third argument for full checks.

After a pass, review translation meaning, completeness, factual accuracy and whether the plan matches the request. Neither a plan nor a structural guard proves those properties, Dynamics acceptance or actual Outlook rendering.
