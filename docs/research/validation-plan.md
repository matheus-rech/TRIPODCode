# Validation evidence and plan

Inspected baseline: e217630579a2521c92e04449756326331f740a43, 2026-11-06. No production datasets were regenerated; no paid model requests were made.

## Baseline before behavioral edits

Local macOS arm64, Python 3.13.12: original test_llm_utils.py and test_hello.py gave **25 passed**. Full baseline collection was blocked by missing GitPython under restricted network/disk conditions. This was a partial baseline, not a successful full reproduction. A separate Actions baseline workflow checks out the exact original SHA for retrospective full-suite validation; its result must be recorded separately.

## Executed implementation checks

| Check | Evidence | Result |
|---|---|---|
| Full Python suite, Python 3.13 on Ubuntu | [Actions 42267468476](https://github.com/matheus-rech/TRIPODCode/actions/runs/42267468476), cf6519a | 111 passed |
| Python wheel and source distribution | Same run, python -m build | Passed |
| Original Conda CI plus app dependencies | [Actions 42266620206](https://github.com/matheus-rech/TRIPODCode/actions/runs/42266620206), 3522aaf | Passed; this is current code, not the untouched baseline |
| TypeScript/Vite production build | Actions 42267468476, cf6519a | Passed |
| Vitest domain semantics | Same run | 3 passed |
| Playwright browser + real FastAPI fixture workflow | Same run | 1 passed; import fixture, inspect, assess, compare labels |
| npm dependency audit | Same run, npm audit --audit-level=moderate | 0 vulnerabilities reported |
| Frozen Python sidecar on Intel macOS | [Actions 42266615788](https://github.com/matheus-rech/TRIPODCode/actions/runs/42266615788), 3522aaf | Startup, fixture run, export, persistence/restart and shutdown passed |
| Optional notebook 05 | Local offline execution | Passed |
| Rust formatting | Local cargo fmt --check | Passed |

The earlier frontend failure was Vitest collecting the Playwright file; explicit unit-test discovery fixed it. Earlier macOS 14 jobs never started because GitHub retired that image on November 2; fde5bad switches Apple Silicon to supported macOS 15. Full native shell/installer checks remain pending until their final linked result is recorded.

## Regression coverage

- test_checkpoint_regressions.py: actual retry exhaustion, required-schema failure, compatible per-row checkpoints, identity changes and colliding input fields.
- test_repository_safety.py / test_extraction_regressions.py: owner-qualified caches, archive traversal/symlinks, bounded deterministic extraction, missing/empty files and truncation.
- test_workflows.py + fixtures/notebook_reference.json: small recorded stage 00/01/02a outputs, conflicting duplicate PMID rejection and annotation-join cardinality. This establishes fixture equivalence, not corpus-wide equivalence.
- test_workspace.py: auth/Host/Origin, immutable imports, demo eligibility, missing/failed/inapplicable distinctions, complete-pair metrics, cancellation/resume without duplicate successes, startup interruption, incompatible versions, integrity tampering, redacted failures, safe export and request limits.
- frontend/src/domain.test.ts: negative/null/inapplicable and state semantics.
- frontend/e2e/workspace.spec.ts: real local service/browser offline demonstration; screenshot retained as a CI artifact.
- scripts/smoke_sidecar.py: frozen runtime independent of development Python; startup, API, persistence, export, shutdown.
- scripts/smoke_desktop.py: native bundle launches its packaged backend and shuts it down through the native quit callback.

## Remaining verification

No full-corpus run, new scientific accuracy evaluation, live paid OpenAI request or real network repository assessment was executed. The app uses mocked provider tests and recorded synthetic examples. Native screen-reader/usability checks, older macOS versions and signed/notarized installation on an independent Mac remain outstanding. Signing requires maintainer Apple credentials.

Before merging, inspect current workflow outcomes and review the methodological changes explicitly. Before distribution, complete native artifact checks and signing/notarization. No automatic merge or release is configured.
