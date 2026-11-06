# Module map

Baseline `e2176305`; implementation stages `6a28882`, `5e5e958`, `fdf57fc`, `cf6519a` (2026-11-06). Refresh this source index after structural changes.

| Source / symbol | Responsibility | Callers / dependencies |
|---|---|---|
| `src/llm_utils/llm_wrapper.py::LLM_wrapper.assess_one_row` | Structured output, bounded retries, explicit AssessmentError | Original notebooks; OpenAI Responses |
| `LLM_wrapper.assess_dataframe` | Identity-checked atomic per-row JSON checkpoints; derived CSV | pandas, FileLock; notebooks 02b/02c/03b/03d |
| `src/llm_utils/structs.py::{PaperAssessment,RepoAssessment}` | Existing scientific output definitions, unchanged | Pydantic; both assessment paths |
| `src/llm_utils/*_assessment_prompt.py` | Original prompts, unchanged | Both assessment paths |
| `src/repo_utils/repo_providers.py::get_repo_cloner` | Legacy Git/Zenodo/Figshare/OSF/DOI adapters | subprocess Git, requests, optional zenodo_get/osf CLIs; GitPython removed |
| `src/repo_utils/safety.py` | Public HTTPS validation, download limits, safe ZIP extraction | Providers and app snapshots |
| `src/repo_utils/main_extractor.py::read_all_files` | Deterministic order, exclusions, symlink refusal, total token budget | tokenizer, clone_and_extract_tree, app snapshot |
| `src/repo_utils/tokenizer.py` | Text/notebook parsing and cl100k_base tokenization; no cell execution | tiktoken; PDF/DOCX helpers retained but excluded from bounded app extraction |
| `src/tripod/workflows.py` | Reference merge, full-text attachment, annotation join | Notebook 05; pandas; explicit input order and lineage |
| `src/tripod/datasets.py::{parse_upload,normalize,evaluation}` | Bounded imports and complete-pair Boolean metrics | Store, Jobs; pandas/pyarrow |
| `src/tripod/provenance.py::{provenance,code_version}` | Input/prompt/schema/scientific-code/config/environment hashes | Jobs; frozen build manifest or source digest |
| `src/tripod/store.py::Store` | SQLite transactions, artifacts, recovery | API and Jobs |
| `src/tripod/jobs.py::Jobs` | Single worker; create/cancel/resume; strict results | Store; mock provider or live OpenAI |
| `src/tripod/sources.py::github_snapshot` | Commit-pinned public GitHub archive and verified extraction cache | Jobs; no Git executable required |
| `src/tripod/secrets.py` | Backend environment/OS credential storage | Provider and credential endpoint |
| `backend/api.py::create_app` | Authenticated adapter, bounded upload, exports | FastAPI |
| `backend/main.py::main` | Loopback bind, workspace lock, session file, readiness/shutdown | uvicorn; CLI or Tauri |
| `frontend/src/{App.tsx,api.ts,domain.ts}` | Workspace, review, metrics, exports and typed client | React; Vitest and Playwright |
| `desktop/src-tauri/src/main.rs` | Sidecar lifecycle; backend_info/save_export IPC | Tauri 2 |
| `scripts/{build_sidecar,smoke_sidecar}.py`, `build_macos.sh` | Frozen runtime, black-box smoke, native packaging | PyInstaller, npm, Rust/Tauri |
| `notebooks/00–04`, `environment.yaml` | Original research and publication reproduction | Original environment and corpus |

CI: tests.yml retains Conda regression coverage; workspace.yml runs Python/package and browser checks; macos.yml builds each native architecture. See the validation record for actual outcomes.
