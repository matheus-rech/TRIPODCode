# Methodological invariants

Baseline e217630579a2521c92e04449756326331f740a43. This fork adds engineering, not revised scientific conclusions.

- Preserve published prompt strings and Pydantic scientific schemas. Operational errors use a separate envelope, not weakened required fields.
- False is negative. Null is missing unless an explicit condition establishes inapplicability. Transport failure/refusal is failure, never False. Missing-text and unassessed rows remain in coverage.
- Original labels/corpus/predictions/figures/citations are immutable. Human and model outputs occupy distinct objects.
- Record input/prompt/schema/model/code/config identities and filtering. Resume only exact-compatible runs.
- Cloud generation remains nondeterministic; provenance does not promise identical outputs. Record returned model/request identifiers where available.
- Evaluation reports paired denominators, exclusions and class counts. Do not impute missing labels or replace undefined metrics by zero. Correcting legacy variable assignment is an explicit metric-version change.
- Ordering, exclusions, symlink refusal and stricter truncation change repository measurement. Version extraction and avoid claims of bitwise equivalence to historic output.
- Synthetic demos are labeled and not pooled with research evidence.

## Explicit operational/methodological changes

`workspace-v1` preserves the original prompts and scientific Pydantic schemas. Confirmed legacy defects were unreachable retry exhaustion, all-None output incompatible with required fields, model-only checkpoint reuse and basename-only repository caches. Failure now uses an envelope, success requires schema validation, identities include input/prompt/schema/code/config, and caches include the full normalized repository URL.

`bounded-snapshot-v1` sorts paths, rejects symlinks/unsafe archives, excludes hidden/generated directories and PDF/DOCX from bounded repository extraction, caps file count/depth/download/expanded size and accounts for headings/tree/truncation within the total context budget. These are deliberate measurement changes, not a claim of bitwise equivalence to historic extraction. App GitHub snapshots use a 100,000-token limit and record omissions/truncation.

The legacy notebook wrapper retains API truncation=auto for interface compatibility and records it. New app calls set truncation=disabled and fail oversized requests explicitly. The app has a 20-record live cap and no implicit retry. These settings belong to the run identity.

`binary-complete-pairs-v1` uses explicit human/model Boolean pairs and reports class counts, denominator and exclusions. It does not silently reproduce the legacy swapped has_repo arrays, interpret string labels as Booleans, or provide repository URL matching/uncertainty estimates. Published metrics and conclusions are unchanged.
