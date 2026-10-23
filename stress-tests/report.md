# Dynamics email skill stress test

Local tests completed on 23 October 2026.

- Original example SHA-256: `fd513d295399da16028f6d900d9880e44f785d317e56cf992a750306cc954088`. Original file is byte-identical to the independent test copy.
- Adversarial suite: 17/18 passing after fixes. Five failures were reproduced before hardening; see before.json and after.json.
- Existing regression checks: 14/14 passing (the last check covers both empty and nonempty existing alt values).
- Skill metadata validation: passed.
- Independent agent: applied permitted French label, footer, preheader, and language edits; declined button duplication and protected preference URL replacement. Output passed the updated guard.
- Review: original Dynamics expressions, markup, protected destinations and tracking IDs retained; Outlook and standard button labels match. See french-labels.html and translation-diff.json.

Fixes address invisible-only numeric/named entity text, placeholder movement across meaningful text runs, and divergence in recognized Outlook image/button pairs. Counterpart checks cover adjacent imageWrapper images and tracking-ID-linked VML/standard buttons; other forms still require manual review.

Limits: no full prose translation was tested (the example uses placeholder Latin). Translation meaning, authorization, unknown template syntaxes, and arbitrary Outlook fallback matching still require review. Encoded markup such as &lt;Hello&gt; remains literal text, so is correctly permitted. No Dynamics import, rendering preview, or test-send has been performed. A passing local guard does not prove Dynamics compatibility.
