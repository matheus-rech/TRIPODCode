"""Durable, bounded, cancellable assessment orchestration independent of FastAPI."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import uuid
from .datasets import demo_records, evaluation, normalize
from .provenance import SCHEMAS, PROMPTS, digest, provenance
from .store import now

class Jobs:
    def __init__(self, store, provider=None):
        self.store = store
        self.provider = provider or self.live_assessment
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='tripod-job')
        self.lock = threading.Lock()
        self.closing = threading.Event()
        self.store.recover()

    def create(self, dataset_id, stage='article', mode='demo', model='recorded-demo-v1', allow_network=False, fetch_repositories=False):
        if stage not in SCHEMAS or mode not in ('demo', 'live'):
            raise ValueError('Unknown assessment stage or mode')
        dataset = self.store.dataset(dataset_id)
        if mode == 'demo' and (dataset['kind'] != 'demo' or dataset['sha256'] != digest(normalize(demo_records()))):
            raise ValueError('Recorded demo runs require the packaged demo dataset')
        if mode == 'live' and (not allow_network or not model.strip() or dataset['row_count'] > 20):
            raise ValueError('Live runs require explicit network consent, a model ID, and at most 20 records')
        config = {'stage': stage, 'mode': mode, 'model': 'recorded-demo-v1' if mode == 'demo' else model,
                  'allow_network': allow_network, 'fetch_repositories': fetch_repositories, 'attempts': 1}
        prov = provenance(dataset, config); identifier = uuid.uuid4().hex
        with self.lock, self.store.connect() as db:
            if db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running','cancelling')").fetchone()[0] >= 10:
                raise ValueError('Job queue is full')
            db.execute('INSERT INTO jobs(id,dataset_id,identity,config,provenance,state,total,created,updated) VALUES(?,?,?,?,?,?,?,?,?)',
                       (identifier, dataset_id, digest(prov), json.dumps(config), json.dumps(prov), 'queued', dataset['row_count'], now(), now()))
        self.pool.submit(self.run, identifier)
        return self.store.job(identifier)

    def cancel(self, identifier):
        with self.lock:
            job = self.store.job(identifier)
            if job['state'] not in ('queued', 'running', 'cancelling'):
                return job
            with self.store.connect() as db:
                db.execute("UPDATE jobs SET cancel=1,state='cancelling',updated=? WHERE id=?", (now(), identifier))
        return self.store.job(identifier)

    def resume(self, identifier):
        with self.lock:
            job = self.store.job(identifier)
            if job['state'] not in ('interrupted', 'cancelled', 'incomplete', 'failed'):
                raise ValueError('Only interrupted, cancelled, incomplete or failed jobs can resume')
            current = provenance(self.store.dataset(job['dataset_id']), job['config'])
            if digest(current) != job['identity']:
                raise ValueError('Code, inputs, prompt, schema or configuration changed; create a new run')
            self.store.records(job['dataset_id'])
            with self.store.connect() as db:
                db.execute("UPDATE jobs SET state='queued',cancel=0,error=NULL,updated=? WHERE id=?", (now(), identifier))
            self.pool.submit(self.run, identifier)
        return self.store.job(identifier)

    def run(self, identifier):
        try:
            job = self.store.job(identifier)
            if self.closing.is_set():
                self.store.set_state(identifier, 'interrupted'); return
            if job['cancel']:
                self.store.set_state(identifier, 'cancelled'); return
            self.store.set_state(identifier, 'running')
            config = job['config']; stage = config['stage']
            records = self.store.records(job['dataset_id'])
            done = {r['record_id']: r for r in self.store.results(identifier)}
            fixtures = {r['id']: r for r in demo_records()} if config['mode'] == 'demo' else {}
            for record in records:
                if self.closing.is_set():
                    self.store.set_state(identifier, 'interrupted'); return
                if self.store.job(identifier)['cancel']:
                    self.store.set_state(identifier, 'cancelled'); return
                previous = done.get(record['id'], {})
                if previous.get('status') in ('succeeded', 'missing', 'inapplicable'):
                    if previous['status'] == 'succeeded':
                        SCHEMAS[stage].model_validate(previous['assessment'])
                    continue
                try:
                    evidence = {'input_record_sha256': digest(record), 'source': config['mode']}
                    if config['mode'] == 'demo':
                        fixture = fixtures[record['id']]
                        status = fixture['demo'][stage]['status']
                        assessment = fixture['demo'][stage].get('assessment')
                        evidence['note'] = 'Synthetic recorded demonstration; no model inference or scientific finding'
                        if status == 'succeeded':
                            assessment = SCHEMAS[stage].model_validate(assessment).model_dump(mode='json')
                        self.store.record_result(identifier, record['id'], status, assessment, evidence,
                                                 'Demonstration of a provider failure' if status == 'failed' else None)
                        continue
                    text = record['text'] if stage == 'article' else record['repo_content']
                    if stage == 'repository' and not text and record['repo_url'] and config['fetch_repositories']:
                        from .sources import github_snapshot
                        text, snapshot = github_snapshot(record['repo_url'], self.store.root / 'snapshots')
                        evidence['snapshot'] = snapshot
                    if not isinstance(text, str) or not text.strip():
                        self.store.record_result(identifier, record['id'], 'missing', evidence=evidence)
                        continue
                    result = self.provider(text, stage, config['model'])
                    if isinstance(result, dict) and 'assessment' in result and 'provider' in result:
                        evidence['provider'] = result['provider']
                        result = result['assessment']
                    assessment = SCHEMAS[stage].model_validate(result).model_dump(mode='json')
                    self.store.record_result(identifier, record['id'], 'succeeded', assessment, evidence)
                except Exception:
                    # Provider exceptions may include credentials, prompts or document content.
                    self.store.record_result(identifier, record['id'], 'failed', error='Assessment failed; check credentials, model access, input size and network, then resume')
            statuses = [r['status'] for r in self.store.results(identifier)]
            if self.store.job(identifier)['cancel']:
                state = 'cancelled'
            else:
                state = 'incomplete' if any(s in ('failed', 'missing') for s in statuses) else 'succeeded'
            self.store.set_state(identifier, state)
        except Exception:
            self.store.set_state(identifier, 'failed', 'Run failed; input or checkpoint integrity could not be verified')

    @staticmethod
    def live_assessment(text, stage, model):
        from openai import OpenAI
        from .secrets import get_key
        # One bounded call per row. No hidden retry or silent context truncation.
        with OpenAI(api_key=get_key(), timeout=60, max_retries=0) as client:
            response = client.responses.parse(model=model,
                input=[{'role': 'system', 'content': PROMPTS[stage]}, {'role': 'user', 'content': text}],
                text_format=SCHEMAS[stage], truncation='disabled')
            if response.output_parsed is None:
                raise ValueError('No structured assessment')
            return {'assessment': response.output_parsed, 'provider': {
                'resolved_model': response.model, 'response_id': response.id,
                'usage': response.usage.model_dump(mode='json') if response.usage else None}}

    def comparison(self, identifier):
        job = self.store.job(identifier)
        return evaluation(self.store.records(job['dataset_id']), self.store.results(identifier), job['config']['stage'])

    def close(self):
        self.closing.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.store.recover()
