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
