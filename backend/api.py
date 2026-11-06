import base64
from contextlib import asynccontextmanager
import csv
import hmac
import io
import json
from typing import Literal
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from src.tripod.datasets import demo_records, normalize
from src.tripod.provenance import digest
from src.tripod.jobs import Jobs
from src.tripod.store import Store
from src.tripod.secrets import save_key

class ImportRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str = Field(max_length=36_000_000)

class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str
    stage: Literal['article', 'repository'] = 'article'
    mode: Literal['demo', 'live'] = 'demo'
    model: str = Field(default='recorded-demo-v1', min_length=1, max_length=200)
    allow_network: bool = False
    fetch_repositories: bool = False

class CredentialRequest(BaseModel):
    key: str = Field(min_length=1, max_length=1024, repr=False)

class BodyLimit:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        # Bounded pre-read also covers chunked/spoofed content-length requests.
        messages, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > 36_001_000:
                response = JSONResponse({'detail': 'Request too large'}, status_code=413)
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get('more_body', False): break
        async def buffered():
            return messages.pop(0) if messages else await receive()
        return await self.app(scope, buffered, send)

def create_app(root, token, provider=None):
    if len(token) < 32: raise ValueError('A strong session token is required')
    store = Store(root)
    engine = Jobs(store, provider)
    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.close()
    app = FastAPI(title='TRIPODCode Workspace', version='0.1.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store; app.state.jobs = engine
    origins = ['tauri://localhost', 'http://tauri.localhost', 'http://localhost:1420', 'http://127.0.0.1:1420']
    app.add_middleware(BodyLimit)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST'],
                       allow_headers=['Authorization', 'Content-Type'])
    @app.middleware('http')
    async def protect(request: Request, call_next):
        if request.url.hostname not in ('127.0.0.1','localhost','testserver'):
            return JSONResponse({'detail':'Invalid host'}, status_code=403)
        origin = request.headers.get('origin')
        if origin and origin not in origins:
            return JSONResponse({'detail':'Invalid origin'}, status_code=403)
        if request.method != 'OPTIONS' and not hmac.compare_digest(request.headers.get('authorization',''), 'Bearer '+token):
            return JSONResponse({'detail':'Unauthorized'}, status_code=401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({'detail':str(exc)}, status_code=400)
    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({'detail':'Not found'}, status_code=404)
    @app.get('/api/health')
    def health():
        return {'ready':True,'version':'0.1.0','offline_demo':True}
    @app.get('/api/datasets')
    def datasets():
        return store.list_datasets()
    @app.post('/api/datasets/import',status_code=201)
    def import_dataset(body: ImportRequest):
        try: payload = base64.b64decode(body.content_base64, validate=True)
        except Exception: raise ValueError('Invalid base64 payload') from None
        return store.import_data(payload, body.filename)
    @app.post('/api/datasets/demo',status_code=201)
    def demo():
        for dataset in store.list_datasets():
            if dataset['kind']=='demo' and dataset['sha256']==digest(normalize(demo_records())): return dataset
        return store.import_data(json.dumps(demo_records()).encode(), 'Synthetic-demonstration.json', kind='demo')
    @app.get('/api/datasets/{identifier}')
    def inspect(identifier: str, offset: int=0, limit: int=25):
        if offset<0 or not 1<=limit<=100: raise ValueError('Invalid pagination')
        records = store.records(identifier)
        return {'dataset':store.dataset(identifier),'records':records[offset:offset+limit],
                'offset':offset,'limit':limit,'total':len(records)}
    @app.get('/api/jobs')
    def jobs(): return store.jobs()
    @app.post('/api/jobs',status_code=202)
    def create_job(body: RunRequest): return engine.create(**body.model_dump())
    @app.get('/api/jobs/{identifier}')
    def job(identifier: str): return store.job(identifier)
    @app.get('/api/jobs/{identifier}/results')
    def results(identifier: str): return store.results(identifier)
    @app.get('/api/jobs/{identifier}/evaluation')
    def evaluate(identifier: str): return engine.comparison(identifier)
    @app.post('/api/jobs/{identifier}/cancel')
    def cancel(identifier: str): return engine.cancel(identifier)
    @app.post('/api/jobs/{identifier}/resume',status_code=202)
    def resume(identifier: str): return engine.resume(identifier)
    @app.post('/api/credentials')
    def credential(body: CredentialRequest):
        save_key(body.key)
        return {'stored':True}
    @app.get('/api/jobs/{identifier}/export')
    def export(identifier: str, format: Literal['json','csv']='json'):
        job = store.job(identifier); rows = store.results(identifier)
        if format=='json':
            payload={'job':job,'results':rows,'evaluation':engine.comparison(identifier)}
            return Response(json.dumps(payload,ensure_ascii=False,indent=2),media_type='application/json',
                headers={'Content-Disposition':f'attachment; filename="{identifier}.json"'})
        output=io.StringIO(); writer=csv.writer(output)
        writer.writerow(['record_id','status','assessment_json','error','run_identity'])
        def cell(value):
            text='' if value is None else str(value)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        for row in rows:
            writer.writerow([cell(row['record_id']),row['status'],cell(json.dumps(row['assessment'])),
                             cell(row['error']),job['identity']])
        return Response(output.getvalue(),media_type='text/csv',
            headers={'Content-Disposition':f'attachment; filename="{identifier}.csv"'})
    return app
