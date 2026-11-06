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
