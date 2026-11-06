# System overview

Baseline: e217630579a2521c92e04449756326331f740a43, main, inspected 2026-11-06. No prior AGENTS.md/scoped instructions existed; CONTRIBUTING.md governs original contributions. Isolated branch: codex/research-workspace. Local exact-commit reconnaissance preserved data/figure tree entries without downloading 41 large blobs. Local disk exhaustion and restricted network prevented continued local development; implementation continues through GitHub and cloud CI.

## Original behavior
Notebooks 00–04 orchestrate references, PMC full text, paper classification, repository retrieval/assessment, evaluation and figures. LLM_wrapper uses OpenAI Responses structured parsing. structs.py defines PaperAssessment and RepoAssessment. clone_and_extract_tree delegates acquisition and text/token extraction. Original data, annotations, figures and attribution remain preserved.

Notebook 01 loads trusted-local pickle or remote Hugging Face dataset code; neither is exposed as an upload feature. Published-output inspection can be offline; new AI calls and downloads require network.

## Application
ADR-0001 records the accepted architecture. Module map and API contracts are updated with implementation; validation-plan records actual checks. The Python core is callable outside the API. Application state lives outside the checkout by default. Human labels and model output stay separate. Synthetic fixture replay demonstrates software, not scientific accuracy.

## Priorities
P0: provenance-safe processing, bounded imports, durable workers/auth, compatible resume, evaluation and demo. P1: accessible review UI and desktop lifecycle/package workflow. P2: signed/notarized distribution, larger data scaling and independent platform validation. P3: explicit safe adapters for legacy full-text indexing/every repository provider and reproduction of published figures. Treat unfinished priorities as backlog, not delivered features.
