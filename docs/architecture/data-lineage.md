# Data lineage

Baseline e217630579a2521c92e04449756326331f740a43. Source trace, not a claim of full-corpus execution.

| Stage | Inputs / transformations | Outputs / external calls |
|---|---|---|
| 00 | TRIPOD/TRIPOD_AI *_11_Aug_25.csv; drop first row, per-group PMID dedup first, remove statement PMIDs, combine and exact-dedup, assert unique PMID | merged_references.parquet.br |
| 01 | PMID to full-text mapping; retain non-null full text | references_with_full_text.parquet.br; pickle+brotli cache or Hugging Face pmc/open_access trust_remote_code=True |
| 02a | human labels joined by PMID; in_scope/has_repo/repo_url renamed gt_* | gt_paper_assessment.csv |
| 02b/02c | PaperAssessment and PAPER_ASSESSMENT_PROMPT | evaluation CSV / paper predictions Parquet; OpenAI, checkpoints |
| 03a/03c | repository URLs and labels, clone_and_extract_tree, context budget 380000 | gt_repo_assessment.csv / references_with_repo.parquet.br; provider downloads |
| 03b/03d | repo_status == ok; RepoAssessment and REPO_ASSESSMENT_PROMPT | evaluation CSV / repository predictions Parquet; OpenAI |
| 04 | stored predictions, metadata and analysis filters | figures/ publication plots |

Small raw annotation CSV headers were inspected. Large data inventoried by Git hash and byte size, not loaded; full-text pickle is about 62.6 MB, full-text Parquet about 71.5 MB. The app must not accept pickle or overwrite published artifacts.

Review finding: 02b initially assigns has_repo_gt from predicted repo_url and has_repo_pred from gt_repo_url; later exact-URL code uses correct arrays. App evaluation must explicitly name human/model arrays and version its metrics; published notebook conclusions are not silently rewritten.

## Implemented service lineage (5e5e958)

`workflows.load_reference_group` preserves explicit file order and the original first-row drop; `combine_reference_groups` preserves first-PMID selection within groups and exact cross-group deduplication, while rejecting conflicting cross-group rows. `attach_full_text` takes a supplied mapping and removes missing full text. `prepare_paper_annotations` joins human labels with validated many-to-one cardinality. `write_prepared_references` writes a new Parquet and lineage JSON without overwriting. The historical PMC index acquisition remains in notebook 01.

Application import → preserved original bytes/SHA-256 → normalized records/SHA-256 → SQLite dataset metadata. Job creation records input, scientific source/build digest, dependency/Python versions, requested model, prompt/schema hashes, stage, extraction/metric versions and configuration. Each result is persisted transactionally with record hash and provider metadata (resolved model/response ID/usage when live). GitHub acquisition adds immutable commit and extracted-content digest. JSON export carries run provenance, results and evaluation; original uploads remain separate.

Legacy LLM checkpoints are now v2 JSON under checkpoints/{identity}.checkpoint.json; timestamp/model-only CSV files are ignored as resume sources. CSV is a derived compatibility output. New app checkpoints live in SQLite and never collide with notebook CSV outputs. Resume never merges scientific identities.
