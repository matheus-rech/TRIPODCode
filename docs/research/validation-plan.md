# Validation record

Baseline e217630579a2521c92e04449756326331f740a43. Inspection 2026-11-06.

Local host: macOS arm64, Python3.13.12. Git/PyPI shell DNS unavailable; exact source commit restored via connector. Initial pytest collection failed missing tqdm/GitPython. After cached dependency setup, python -m pytest tests/test_llm_utils.py tests/test_hello.py -q: **25 passed in 37.61s**. Full repository suite remained blocked by missing GitPython. No source behavior changed before these checks. Cached versions differed from original Conda pins; this is not full environment reproduction.

The Mac then reported about 256 MB free and ENOSPC on writes. User requested cloud continuation. Cloud Work handoff failed; implementation proceeds directly on GitHub with Actions verification. No paid job, full-corpus run, publication regeneration, frontend or desktop build has yet passed.

Required evidence: full baseline suite; regression tests for retries/schema/checkpoint identities/owner caches/extraction safety; small notebook reference-equivalence fixtures; API import/jobs/auth/cancel/restart/resume/export; UI states and build; end-to-end offline replay; desktop sidecar readiness/storage/auth/shutdown and macOS packaging. Routine tests use mocks/synthetic data. Add actual cloud results here as they execute, never label unexecuted checks passed.
