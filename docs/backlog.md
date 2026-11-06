# Prioritized backlog

Updated 2026-11-06. The browser build and both native app/DMG builds, lifecycle smoke checks and forced-shutdown regression passed at aab9fafd; installer links are in docs/application.md. Delivered behavior is in system-overview; the following remains distinct from completed work.

| Priority | Work | Acceptance evidence |
|---|---|---|
| P0 distribution | Apple signing/notarization | Maintainer credentials and independent signed-install verification; no automatic release |
| P1 scientific validation | Authorized real dataset with human adjudication | Protocol, budget, field coverage, disagreements and versioned results; synthetic demo is insufficient |
| P1 usability | macOS WebView accessibility/user review | Keyboard, screen reader, zoom and interrupted-run review |
| P1 scale | Larger streaming datasets, workers if justified | Memory/crash/cost controls; current live cap 20 |
| P1 acquisition | Safe full-text and non-GitHub app adapters | Bounded parsing and immutable identities; app currently fetches public GitHub only |
| P2 reproducibility | Entire original corpus and figures | Exact original environment/data, authorized cost; not routine CI |
| P2 methods | Legacy gt_* mapping, URL comparisons, richer metrics | Explicit semantic mapping, scientific review and fixtures |
| P2 platforms | Windows/Linux and database migrations | Native lifecycle/install checks per platform |

Original prompts/schemas/inclusion criteria remain unchanged. New extraction and metrics are versioned; no retrospective published estimates were recalculated.
