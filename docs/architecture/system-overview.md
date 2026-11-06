# System overview

Inspected baseline: `e217630579a2521c92e04449756326331f740a43` (main), 2026-11-06. Implementation: core `6a28882`, services/API `5e5e958`, frontend/desktop `fdf57fc`, toolchain fixes `cf6519a`. Isolated branch: `codex/research-workspace`, draft PR #1. Original corpus, annotations, publication figures, prompts and scientific schemas remain intact. CONTRIBUTING.md was read before editing; no repository AGENTS.md existed at baseline.

## Current architecture

Original notebooks 00–04 remain research entry points. The optional notebook 05 demonstrates extracted services offline. React/TypeScript calls an authenticated loopback FastAPI service; `src/tripod` performs computation independently of HTTP. One background worker runs assessments. SQLite WAL stores datasets, jobs and per-record checkpoints; originals and normalized JSON live outside the checkout.

Tauri owns the bundled PyInstaller Python process, random session token, readiness, narrow export IPC and shutdown. Normal installed use requires no separate Python, Node, Git, Conda or notebooks. See [ADR-0001](../decisions/ADR-0001-app-architecture.md), [module map](module-map.md), [lineage](data-lineage.md) and [API](api-contracts.md).

## Boundaries

Offline operations: imports, inspection, synthetic fixture replay, review, paired Boolean evaluation and exports. The demo is six explicitly synthetic records and makes no accuracy claim. Human labels stay separate from model results.

Network operations: live OpenAI assessment and optional public GitHub snapshot download. Live jobs require explicit consent, a model identifier and at most 20 records, with one request per record and no hidden SDK retries. Building dependencies also requires network.

Legacy notebooks retain PMC/Hugging Face indexing, trusted-local compressed pickle, plotting libraries and historical provider CLIs. These are not app upload or automatic launch behavior. The app does not execute downloaded repositories or accept pickle.

Native builds require macOS, Xcode command-line tools, Python 3.13, Node 22 and Rust. Signed/notarized distribution requires maintainer-owned Apple credentials. See [installation](../application.md), [validation evidence](../research/validation-plan.md) and [prioritized backlog](../backlog.md). The app has not reproduced the full published analysis.
