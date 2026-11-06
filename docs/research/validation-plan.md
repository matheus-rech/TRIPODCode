# Validation evidence and plan

Inspected baseline: e217630579a2521c92e04449756326331f740a43, 2026-11-06. Validated application source: aab9fafd3314fda9aed7b1f0e784aac6cc33129e. No production corpus was regenerated; no paid model request was made.

## Baseline

Before behavioral edits, local macOS arm64 / Python 3.13.12 ran the original test_llm_utils.py and test_hello.py: **25 passed**. Full local collection was blocked by missing GitPython under restricted network/disk conditions.

Retrospective cloud verification checked out the exact untouched baseline and original environment.yaml: **74 passed, 1 warning** in [Actions 42269372311](https://github.com/matheus-rech/TRIPODCode/actions/runs/42269372311), job 128069628293. This is separate from the expanded implementation suite; neither reproduces the whole research corpus.

## Executed implementation checks

| Check | Evidence | Result |
|---|---|---|
| Full Python suite, Python 3.13 on Ubuntu | [Workspace CI](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272305002), aab9fafd | 111 passed |
| Python wheel and source distribution | Same run, python -m build | Passed |
| Original Conda environment plus application dependencies | [Conda CI](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272304913), aab9fafd | Passed on current code |
| TypeScript/Vite production build | Workspace CI | Passed |
| Vitest domain semantics | Workspace CI and both native jobs | 3 passed |
| Playwright browser + real FastAPI fixture workflow | Workspace CI | 1 passed: fixture import, inspect, assess, compare human labels |
| npm audit --audit-level=moderate | Workspace CI | 0 vulnerabilities reported |
| Frozen Python runtime, Apple Silicon and Intel | [Native CI](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272301370), aab9fafd | Startup, fixture run, export, persistence/restart and shutdown passed |
| Native .app and .dmg bundles, arm64 and x86_64 | Same run | Both built successfully |
| Rust forced-shutdown regression | Same run, cargo test --release --locked | 1 passed on each architecture; child process group terminated |
| Native app lifecycle | Same run, scripts/smoke_desktop.py | Both launch packaged backend, verify authenticated readiness and quit cleanly |
| Optional notebook 05 | Local offline execution | Passed |
| Rust formatting / source syntax | Local cargo fmt --check and Python compileall | Passed |

Apple Silicon job: 128079885942, macOS 26. Intel job: 128079886569, macOS 15. [arm64 artifact](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272301370/artifacts/13532446203); [Intel artifact](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272301370/artifacts/13532661633). Artifacts include installers, Cargo/npm lockfiles, Python environment, tool versions, source commit and sidecar SHA-256. They are development builds without Developer ID signing/notarization.

Earlier failures were corrected: Vitest initially collected Playwright tests; vulnerable frontend toolchain versions were upgraded; retired macOS 14 runner labels were replaced; native icons were supplied; the Tauri CLI now receives Cargo's lockfile flag after --. None of those earlier failed jobs is presented as a successful application build.

## Regression coverage

- test_checkpoint_regressions.py: retry exhaustion/refusal, required-schema failure handling, identity changes, preserved input fields, cancellation and compatible per-row checkpoints.
- test_repository_safety.py / test_extraction_regressions.py: owner-qualified cache identity, archive traversal/symlinks, deterministic bounded extraction, empty files and truncation.
- test_workflows.py + fixtures/notebook_reference.json: small recorded stage 00/01/02a outputs, conflicting PMID rejection and annotation-join cardinality. This is fixture equivalence, not corpus-wide equivalence.
- test_workspace.py: token/Host/Origin, immutable imports, demo eligibility, missing/failed/inapplicable results, complete-pair metrics, cancellation/resume without duplicate successes, startup interruption, incompatible versions, integrity checks, redacted failures, safe exports and request limits.
- frontend/src/domain.test.ts: negative/null/inapplicable and state semantics.
- frontend/e2e/workspace.spec.ts: real local service/browser offline demo; screenshot is retained in the frontend CI artifact.
- scripts/smoke_sidecar.py: frozen runtime independent of development Python.
- scripts/smoke_desktop.py and the Rust native regression: normal quit and forced descendant cleanup.

## Preservation and limits

GitHub's baseline-to-aab9fafd comparison shows no changed files under data/, figures/, notebooks/00–04, original prompt/schema files, LICENSE or CITATION.cff. There are 11 staged implementation commits before the final documentation update.

Not executed: full-corpus reproduction, real paid OpenAI inference, real network repository assessment, independent scientific accuracy evaluation, native screen-reader/usability review, or installation on older macOS versions. API/provider tests use mocks; demo outputs are explicitly synthetic.

Developer ID signing/notarization requires maintainer Apple credentials. Signed independent-machine installation remains a distribution gate. No automatic merge, public release or credential provisioning was performed. See the prioritized backlog for larger data, acquisition adapters and additional scientific validation.
