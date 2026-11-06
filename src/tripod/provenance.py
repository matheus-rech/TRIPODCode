"""Content-addressed provenance; timestamps never determine compatibility."""
import hashlib
import json
import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from src.llm_utils.structs import PaperAssessment, RepoAssessment
from src.llm_utils.paper_assessment_prompt import PAPER_ASSESSMENT_PROMPT as PAPER_PROMPT
from src.llm_utils.repo_assessment_prompt import REPO_ASSESSMENT_PROMPT as REPO_PROMPT

SCHEMAS = {'article': PaperAssessment, 'repository': RepoAssessment}
PROMPTS = {'article': PAPER_PROMPT, 'repository': REPO_PROMPT}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def code_version():
    root = Path(__file__).parent.parent
    manifest = root / 'tripod' / 'build-info.json'
    if manifest.exists():
        return json.loads(manifest.read_text())
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
             and (p.suffix == '.py' or ('fixtures' in p.parts and p.suffix == '.json'))}
    return {'source_sha256': digest(files), 'git_commit': None, 'build': 'source'}

def provenance(dataset, config):
    stage = config['stage']
    packages = {}
    for name in ('openai', 'pydantic', 'pandas', 'tiktoken', 'pyarrow'):
        try: packages[name] = version(name)
        except PackageNotFoundError: packages[name] = None
    return {'format_version': 1, 'methodology_version': 'workspace-v1',
            'input_sha256': dataset['sha256'], 'original_sha256': dataset['original_sha256'],
            'model': config['model'], 'mode': config['mode'],
            'python': sys.version.split()[0], 'packages': packages,
            'prompt_sha256': digest(PROMPTS[stage]),
            'schema_sha256': digest(SCHEMAS[stage].model_json_schema()),
            'code': code_version(), 'config': config,
            'extraction_version': 'bounded-snapshot-v1', 'truncation': 'disabled',
            'metric_version': 'binary-complete-pairs-v1'}
