# TRIPODCode research workspace

The workspace adds a local application to the original research repository. It does not regenerate published data or replace the original 00–04 notebooks.

## Install a macOS build

Open the **macOS application build** workflow under [Actions](https://github.com/matheus-rech/TRIPODCode/actions/workflows/macos.yml), select a run with a successful job for your architecture and download its artifact: aarch64-apple-darwin for Apple Silicon, x86_64-apple-darwin for Intel. Extract the artifact, open the DMG under the bundle directory and copy TRIPODCode.app to Applications.

These development artifacts are not Developer ID signed/notarized. macOS may require its explicit Open Anyway approval for a trusted downloaded build. Do not disable Gatekeeper globally. Signed public distribution is a separate maintainer step. Current native verification targets macOS 26 (Apple Silicon) and macOS 15 (Intel); the declared minimum 12.0 has not been independently tested on older systems.

The application bundles Python, its libraries and tokenizer vocabulary. No separate Conda, Node, Git, notebook or terminal server is needed for installed use. Launch TRIPODCode; it starts its local backend and connects automatically.

Verified builds from commit `aab9fafd3314fda9aed7b1f0e784aac6cc33129e`:

| Mac | Download | Native checks |
|---|---|---|
| Apple Silicon | [Unsigned arm64 installer artifact](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272301370/artifacts/13532446203) | macOS 26: bundle, forced-shutdown regression, native launch/readiness/quit passed |
| Intel | [Unsigned x86_64 installer artifact](https://github.com/matheus-rech/TRIPODCode/actions/runs/42272301370/artifacts/13532661633) | macOS 15: bundle, forced-shutdown regression, native launch/readiness/quit passed |

Use the DMG inside the artifact; it preserves application executable permissions. GitHub may require sign-in to download Actions artifacts. Artifacts have GitHub retention limits; source and build instructions remain in this branch.

## Try it offline

1. Select **Load offline demo** in Workspace.
2. Inspect the six synthetic records. Human annotations are separate from recorded model output.
3. Start the article assessment. Six records are processed; missing/failed examples deliberately make the run **Incomplete**.
4. Review results and compare with human annotations. The is_match example has four complete pairs and two exclusions.
5. Select the repository stage and run it to see negative, null and inapplicable results.
6. Export JSON (provenance/results/metrics) or CSV. Desktop exports go to Downloads/TRIPODCode.
7. Close and reopen the app to see persisted history.

Synthetic results demonstrate software behavior, not measured model performance. Offline imports, review, evaluation and exports need no API key.

## Import research data

CSV, JSON and Parquet are supported (25 MiB / 5,000-record maximum). Required: unique id or PMID. Optional: title, text/full_text, repo_content/output, repo_url and human labels.

```json
[
  {
    "id": "example-1",
    "title": "Example research article",
    "text": "Full article text here",
    "repo_content": "# Previously extracted repository text",
    "human": {
      "article": {"is_match": true},
      "repository": {"contains_readme": true, "implements_tests": false}
    }
  }
]
```

Use real JSON booleans for human labels. In CSV, human is a quoted JSON object. Historical gt_* columns must be mapped explicitly to the intended assessment fields; they are preserved but not silently interpreted. Original uploads are retained. The API never overwrites the repository corpus.

Live article/repository assessment requires internet, an accessible OpenAI model ID, credentials and explicit network consent in the run form. Live jobs are limited to 20 records. One provider request is made per eligible record; no automatic retry or hidden context truncation. Optional repository fetching currently supports public GitHub owner/repository URLs and records resolved commits. Other providers and PMC retrieval remain legacy notebook workflows.

Set the key through Settings (native OS credential storage), or OPENAI_API_KEY in the backend environment for development. Keys never enter the frontend bundle, browser storage or exports. The session token is a separate local access credential.

## Recovery and storage

Desktop data defaults to ~/Library/Application Support/org.tripodcode.workspace. The standalone CLI defaults to ~/Library/Application Support/TRIPODCode. TRIPOD_DATA_DIR overrides either; --data-dir overrides the CLI. Set separate directories for simultaneous development and installed applications.

The directory contains workspace.sqlite3, immutable datasets, snapshot artifacts and a transient session.json. Back up the whole directory while the app is closed. Do not edit SQLite/results files to force a resume. No destructive reset button is provided.

Cancel stops after the current bounded operation. Closing the native application requests shutdown, then terminates a still-busy backend; completed record transactions survive. On restart, unfinished work is marked Interrupted and requires explicit Resume. Changed scientific code, runtime packages, prompt, schema, input or configuration requires a new run. Missing text needs a corrected new dataset. Incomplete means failure/missing coverage, not a negative research finding.

## Development setup

Use Python 3.13 and Node 22.12+. The original Conda environment remains available for publication notebooks.

```bash
git clone https://github.com/matheus-rech/TRIPODCode.git
cd TRIPODCode
git switch codex/research-workspace
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
python -m pytest -q
python -m build
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
```

For browser development, run the backend and frontend in separate terminals:

```bash
python -m backend.main --data-dir /tmp/tripod-dev
npm --prefix frontend run dev
```

Open http://127.0.0.1:1420 and enter the port/session token from /tmp/tripod-dev/session.json. That file is local mode 0600; do not share or commit it. The server does not print credentials. Ctrl-C stops the standalone backend.

Browser integration tests use scripts/wait_for_backend.py and the environment/token setup in .github/workflows/workspace.yml. They run a real local backend with synthetic fixtures and no provider calls.

## Build a macOS application

Install Xcode command-line tools, Python 3.13, Node 22.12+ and Rust on the target architecture, then run:

```bash
bash scripts/build_macos.sh
```

The script builds a frozen Python sidecar, tests its independent startup/demo/export/persistence/shutdown, installs frontend dependencies from package-lock.json, tests/builds React, and builds Tauri using the pinned official @tauri-apps/cli 2.12.4 binary and Cargo.lock. Outputs are under desktop/src-tauri/target/release/bundle (macos/*.app and dmg/*.dmg). Build on Apple Silicon for arm64 and Intel for x86_64; Python cross-compilation is not supported. Dependencies require network during building.

The Actions matrix additionally records the Python environment, Rust/Node versions, binary SHA-256 and source commit in its artifacts. Dependency lockfiles fix npm/Rust resolution; Python version ranges are resolved at build time and recorded by pip freeze/build-manifest. Reproducing a specific binary requires its recorded Python environment and matching native toolchain; the workflow is not a bit-for-bit reproducible-build guarantee.

Apple Developer ID signing, notarization, credential provisioning and public release are intentionally separate. The workflow uploads review artifacts only and never merges or publishes a release.

See [actual checks](research/validation-plan.md), [API contracts](architecture/api-contracts.md) and [remaining work](backlog.md).
