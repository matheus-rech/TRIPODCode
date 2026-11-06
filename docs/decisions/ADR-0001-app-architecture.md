# ADR-0001: Local research workspace

Accepted for implementation 2026-11-06. Baseline e217630579a2521c92e04449756326331f740a43.

Retain Python/Pydantic research schemas/prompts, add reusable Python services, thin FastAPI adapter, React/TypeScript UI and Tauri 2 desktop shell. SQLite transactions own job state/per-record checkpoints; content-addressed JSON preserves imports. One worker bounds concurrency/spending. Restart marks work interrupted and requires explicit compatible resume rather than automatically making cloud calls.

FastAPI retains scientific Python. React supplies typed interactive review. Tauri packages a PyInstaller Python sidecar without end-user Conda. The sidecar binds loopback, requires a random token, reports readiness and shuts down with its parent. Rust owns startup and a narrow API bridge; no arbitrary frontend shell. Credentials use macOS Keychain where available, backend environment for development. Offline imports/replay require no acquired executables. Downloaded code is never executed.

Alternatives: Electron is larger and still needs Python; browser-only deployment does not meet local installation; rewriting scientific logic in TypeScript increases equivalence risk; distributed queues are unnecessary for one researcher. Architecture-specific builds and Apple signing/notarization remain platform obligations.

Offline replay is explicitly synthetic, not local AI. Cloud assessment requires network and paid credentials. Original PMC indexing and full publication plotting remain reproducibility notebooks; arbitrary pickle/remote dataset code are not app upload capabilities.

Official formats checked 2026-11-06:
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions
- https://docs.github.com/en/copilot/concepts/prompting-and-context/prompt-files
- https://developers.openai.com/codex/guides/agents-md/
- https://v2.tauri.app/develop/sidecar/

AGENTS.md and copilot-instructions.md provide shared guidance. Scoped instructions use applyTo frontmatter; reusable workflows use .github/prompts/*.prompt.md (IDE support varies). Tauri externalBin expects target-triple suffixes.
