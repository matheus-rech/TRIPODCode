---
applyTo: "src/**/*.py,backend/**/*.py,tests/**/*.py,scripts/**/*.py"
---
Follow AGENTS.md. Trace callers before changing interfaces. Keep scientific operations independent of HTTP/UI. Use typed inputs, explicit errors, bounded I/O, deterministic processing and atomic compatible checkpoints. Validate structured outputs before marking success. Never log raw provider exceptions containing credentials or research content. Test failure, resume compatibility, cancellation and restart with mocked providers. Update API contracts and validation evidence.
