"""SQLite metadata and immutable artifact storage with per-row transactions."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import uuid
from .datasets import parse_upload, normalize
from .provenance import digest

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.datasets = self.root / 'datasets'; self.datasets.mkdir(exist_ok=True, mode=0o700)
        self.db = self.root / 'workspace.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS datasets (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT NOT NULL,
                  original_sha256 TEXT NOT NULL, row_count INTEGER NOT NULL,
                  kind TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id),
                  identity TEXT NOT NULL, config TEXT NOT NULL, provenance TEXT NOT NULL,
                  state TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL,
                  cancel INTEGER NOT NULL DEFAULT 0, error TEXT, created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS results (
                  job_id TEXT NOT NULL REFERENCES jobs(id), record_id TEXT NOT NULL,
                  status TEXT NOT NULL, assessment TEXT, evidence TEXT NOT NULL, error TEXT,
                  PRIMARY KEY(job_id, record_id));
            ''')
        os.chmod(self.db, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_data(self, payload, filename, kind='imported'):
        records, original_sha = parse_upload(payload, filename)
        sha = digest(records); identifier = uuid.uuid4().hex
        path = self.datasets / identifier; path.mkdir(mode=0o700)
        # Preserve byte-for-byte input alongside the normalized representation.
        (path / 'original').write_bytes(payload)
        (path / 'records.json').write_text(json.dumps(records, ensure_ascii=False, allow_nan=False))
        with self.connect() as db:
            db.execute('INSERT INTO datasets VALUES(?,?,?,?,?,?,?)',
                       (identifier, Path(filename).name[:200], sha, original_sha, len(records), kind, now()))
        return self.dataset(identifier)

    def list_datasets(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM datasets ORDER BY created DESC')]

    def dataset(self, identifier):
        with self.connect() as db:
            row = db.execute('SELECT * FROM datasets WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise KeyError('Dataset not found')
        return dict(row)

    def records(self, identifier):
        dataset = self.dataset(identifier)
        records = json.loads((self.datasets / identifier / 'records.json').read_text())
        if digest(records) != dataset['sha256']:
            raise ValueError('Dataset integrity check failed')
        return records

    def job(self, identifier):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise KeyError('Job not found')
        result = dict(row)
        for field in ('config', 'provenance'):
            result[field] = json.loads(result[field])
        return result

    def jobs(self):
        with self.connect() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT 200')]
        return [self.job(identifier) for identifier in ids]

    def results(self, identifier):
        self.job(identifier)
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM results WHERE job_id=? ORDER BY record_id', (identifier,))]
        for row in rows:
            row['assessment'] = json.loads(row['assessment']) if row['assessment'] else None
            row['evidence'] = json.loads(row['evidence'])
        return rows

    def record_result(self, identifier, record_id, status, assessment=None, evidence=None, error=None):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?)',
                       (identifier, record_id, status, json.dumps(assessment) if assessment is not None else None,
                        json.dumps(evidence or {}), error))
            db.execute('UPDATE jobs SET progress=(SELECT COUNT(*) FROM results WHERE job_id=?), updated=? WHERE id=?',
                       (identifier, now(), identifier))

    def set_state(self, identifier, state, error=None):
        with self.connect() as db:
            db.execute('UPDATE jobs SET state=?, error=?, updated=? WHERE id=?', (state, error, now(), identifier))

    def recover(self):
        # Recovery never initiates a paid call; the user deliberately resumes.
        with self.connect() as db:
            db.execute("UPDATE jobs SET state='interrupted', updated=? WHERE state IN ('queued','running','cancelling')", (now(),))
