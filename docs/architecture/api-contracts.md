# API contracts

Implemented at `5e5e958` in backend/api.py and src/tripod/{datasets,jobs,store}.py; UI at `fdf57fc`. API version 0.1.0. Prefix: /api. Bind: 127.0.0.1 only. All data/health requests require Authorization: Bearer <session token>. Origins are restricted to Tauri and localhost development port 1420. OpenAPI/docs endpoints are disabled.

| Method / route | Input | Output |
|---|---|---|
| GET /health | token | ready, version, offline_demo |
| GET /datasets | — | metadata list |
| POST /datasets/import | filename, content_base64 | 201 immutable dataset |
| POST /datasets/demo | — | 201 fixture dataset, idempotent by digest |
| GET /datasets/{id}?offset=0&limit=25 | limit 1–100, offset ≥0 | dataset, records, offset, limit, total |
| GET /jobs | — | durable history |
| POST /jobs | dataset_id, stage, mode, model, allow_network, fetch_repositories | 202 job |
| GET /jobs/{id} | — | state, progress, total, config, provenance, timestamps, redacted error |
| GET /jobs/{id}/results | — | per-record status, assessment, evidence, error |
| GET /jobs/{id}/evaluation | — | metric version, denominators, exclusions, Boolean metrics |
| POST /jobs/{id}/cancel | — | cooperative cancellation |
| POST /jobs/{id}/resume | — | 202 only for compatible identity |
| GET /jobs/{id}/export?format=json | json or csv | attachment |
| POST /credentials | key | stored:true after native credential storage; no read-back |

## Dataset contract

JSON accepts an array or {"records":[...]}. Each record requires unique nonempty id (or PMID). Aliases: title/Title, text/full_text, repo_content/output. Optional repo_url and human:{article:{...},repository:{...}}. CSV human values may be JSON strings. Historical gt_* labels are not guessed: map them explicitly to the intended schema. Full original rows are retained under source.

Limits: upload 25 MiB, 5,000 records, two million characters per text field; Parquet metadata decoded-size cap 100 MiB. HTTP base64 envelope capped at 36,001,000 bytes. Duplicate/empty IDs and duplicate CSV columns fail. Live jobs require explicit consent and ≤20 records. Demo only accepts the immutable packaged fixture. Creation queue cap: 10 active jobs.

## States and provenance

Job states: queued, running, cancelling, succeeded, incomplete, failed, cancelled, interrupted. Record states: succeeded, failed, missing, inapplicable; absent results are pending. Progress counts persisted outcomes, not positive assessments. Failed/missing records make a completed job incomplete.

Startup marks unfinished jobs interrupted and never automatically calls paid services. Resume recomputes input, prompt, schema, scientific source/build, packages/Python, model and configuration identity. Mismatch requires a new run. Valid successes, missing and inapplicable results remain; failed records can retry. Supplying missing text requires a new dataset/run.

False, unreported null, conditional inapplicability and failure stay distinct. Evaluation uses succeeded Boolean human/model pairs only; undefined metrics are null. Metric version: binary-complete-pairs-v1.

## Errors and access

401 token; 403 Host/Origin; 404 missing object; 400 service validation; 413 body size; 422 malformed schema/query. Provider errors are redacted. JSON export contains provenance/results/evaluation; CSV contains status and run identity with formula-safe cells. Exports omit provider credentials and source full text.

Native IPC only exposes backend_info and save_export. Exports use generated non-overwriting names in Downloads/TRIPODCode. No arbitrary shell, path serving, pickle upload or downloaded-code execution. This is a single-user local application, not a remotely deployable multi-user API.
