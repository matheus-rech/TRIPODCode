# API contracts

Baseline e217630579a2521c92e04449756326331f740a43. ADR-0001 accepts FastAPI as a thin adapter over Python services. Implemented routes will be recorded with the backend commit.

Validated immutable imports, provenance, durable jobs, per-record outcomes, separate human/model review, paired evaluation and JSON/CSV export belong in the service layer. Data endpoints require a session token; loopback binding and browser-origin restrictions protect the local service. Health contains no research data; credentials are never returned.

Job states: queued, running, succeeded, incomplete, failed, cancelled, interrupted. Failed/missing rows prevent complete success. Resume verifies identity before scheduling and skips successful records. Progress separates completion from scientific success.
