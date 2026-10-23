# Updated designer HTML review

The current example/example.html contains designer source rather than the previous rendered/exported form. Skill guidance now explicitly preserves designer settings, CSS setting comments, block/container metadata, lookup metadata, asset IDs and the supplied source form. Existing title remains protected.

Fixed a validator gap: an ordinary href change could previously strip or alter its Dynamics tracking fragment. The entire fragment containing _msdynmkt_ fields is now protected, while the ordinary destination can change.

Validation: 17/17 current-designer checks, 18/18 adversarial checks against the archived original exported fixture, and 14/14 existing regression checks pass. Tests of current designer markup assert their mutation target exists, avoiding false success from replacements that changed nothing. Original and updated examples are never compared as if one were a permitted edit of the other.

The older french-labels.html is a historical test output from the previous example, not a translation of the updated designer source. No email was edited or sent during this review. Dynamics rendering/editor behavior remains unverified. Source-only image changes may leave data-image-file-id referring to the old asset; the skill preserves it and requires reporting this limitation.
