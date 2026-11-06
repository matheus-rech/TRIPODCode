"""Bounded dataset normalization. Inputs and human annotations remain immutable."""
import csv
import hashlib
import io
import json
from pathlib import Path
import pandas as pd
from .provenance import digest

MAX_BYTES = 25 * 1024 * 1024
MAX_ROWS = 5000
MAX_TEXT = 2_000_000

def normalize(records):
    if not isinstance(records, list) or not 0 < len(records) <= MAX_ROWS:
        raise ValueError(f'Dataset must contain 1–{MAX_ROWS} records')
    seen = set()
    normalized = []
    for row in records:
        if not isinstance(row, dict):
            raise ValueError('Each record must be an object')
        raw_id = row.get('id', row.get('PMID'))
        identifier = '' if raw_id is None else str(raw_id).strip()
        if not identifier or len(identifier) > 200 or identifier in seen:
            raise ValueError('Record IDs must be nonempty, unique, and at most 200 characters')
        seen.add(identifier)
        text = row.get('text', row.get('full_text'))
        content = row.get('repo_content', row.get('output'))
        for value in (text, content):
            if value is not None and (not isinstance(value, str) or len(value) > MAX_TEXT):
                raise ValueError('Text fields must be strings within the 2 million character limit')
        human = row.get('human', {})
        if human is None:
            human = {}
        if isinstance(human, str):
            try:
                human = json.loads(human)
            except ValueError:
                raise ValueError('human must contain a JSON object') from None
        if not isinstance(human, dict):
            raise ValueError('human must be an object separated from model output')
        if any(k not in ('article', 'repository') or not isinstance(v, dict) for k, v in human.items()):
            raise ValueError('Human annotations require article/repository objects')
        url = row.get('repo_url')
        if url is not None and (not isinstance(url, str) or len(url) > 2048):
            raise ValueError('Repository URL must be a string of at most 2048 characters')
        # Preserve the complete imported record; normalized fields never overwrite source data.
        normalized.append({'id': identifier, 'title': str(row.get('title', row.get('Title', identifier)))[:1000],
                           'text': text, 'repo_content': content, 'repo_url': row.get('repo_url'),
                           'human': human, 'source': row})
    return normalized

def parse_upload(payload, filename):
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError('Upload must be nonempty and at most 25 MiB')
    suffix = Path(filename).suffix.lower()
    if suffix == '.json':
        value = json.loads(payload)
        records = value.get('records') if isinstance(value, dict) else value
    elif suffix == '.csv':
        reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise ValueError('Duplicate CSV columns are forbidden')
        records = []
        for row in reader:
            records.append({k: v if v != '' else None for k, v in row.items()})
            if len(records) > MAX_ROWS:
                raise ValueError('Dataset exceeds row limit')
    elif suffix == '.parquet':
        import pyarrow.parquet as pq
        table = pq.ParquetFile(io.BytesIO(payload))
        if table.metadata.num_rows > MAX_ROWS:
            raise ValueError('Dataset exceeds row limit')
        # Cap decoded memory as well as compressed file size.
        if sum(table.metadata.row_group(i).total_byte_size for i in range(table.num_row_groups)) > MAX_BYTES * 4:
            raise ValueError('Parquet decoded size exceeds limit')
        frame = table.read().to_pandas()
        records = json.loads(frame.to_json(orient='records'))
    else:
        raise ValueError('Supported imports are CSV, JSON, and Parquet')
    return normalize(records), hashlib.sha256(payload).hexdigest()

def demo_records():
    return json.loads((Path(__file__).parent / 'fixtures' / 'demo.json').read_text())

def evaluation(records, results, stage):
    """Only observed boolean human/model pairs enter each metric denominator."""
    indexed = {r['record_id']: r for r in results}
    fields = sorted({field for record in records for field in record['human'].get(stage, {})})
    metrics = []
    for field in fields:
        tp = tn = fp = fn = excluded = 0
        for record in records:
            truth = record['human'].get(stage, {}).get(field)
            result = indexed.get(record['id'], {})
            predicted = (result.get('assessment') or {}).get(field)
            if result.get('status') != 'succeeded' or type(truth) is not bool or type(predicted) is not bool:
                excluded += 1
                continue
            tp += int(truth and predicted); tn += int(not truth and not predicted)
            fp += int(not truth and predicted); fn += int(truth and not predicted)
        n = tp + tn + fp + fn
        metrics.append({'field': field, 'n': n, 'excluded': excluded, 'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
                        'accuracy': (tp+tn)/n if n else None,
                        'precision': tp/(tp+fp) if tp+fp else None,
                        'recall': tp/(tp+fn) if tp+fn else None,
                        'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None})
    return {'version': 'binary-complete-pairs-v1', 'records': len(records), 'metrics': metrics,
            'note': 'Missing, failed, inapplicable, pending and nonboolean pairs are excluded, never scored as negative.'}
