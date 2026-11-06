"""Read public GitHub snapshots over HTTPS; no Git or downloaded execution needed."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse
from src.repo_utils.safety import request_public, download, safe_extract_zip
from src.repo_utils.main_extractor import read_all_files

def github_snapshot(url, cache_root):
    parsed = urlparse(url)
    match = re.fullmatch(r'/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?', parsed.path)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment or not match:
        raise ValueError('Automatic retrieval supports public https://github.com/owner/repository URLs only')
    owner, repo = match.groups()
    with request_public(f'https://api.github.com/repos/{owner}/{repo}/commits/HEAD') as response:
        commit = response.json()['sha']
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Invalid upstream commit identity')
    identity = hashlib.sha256(f'{owner}/{repo}@{commit}'.encode()).hexdigest()
    root = Path(cache_root) / identity
    manifest = root / 'snapshot.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        text = (root / 'content.txt').read_text()
        if hashlib.sha256(text.encode()).hexdigest() == saved['content_sha256']:
            return text, saved
        raise ValueError('Snapshot cache integrity check failed')
    Path(cache_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_root) as temporary:
        temp = Path(temporary)
        download(f'https://api.github.com/repos/{owner}/{repo}/zipball/{commit}', temp / 'snapshot.zip')
        unpacked = temp / 'files'; unpacked.mkdir()
        safe_extract_zip(temp / 'snapshot.zip', unpacked)
        children = list(unpacked.iterdir())
        base = children[0] if len(children) == 1 and children[0].is_dir() else unpacked
        text = read_all_files(base, False, 100000)
    saved = {'url': url, 'commit': commit, 'content_sha256': hashlib.sha256(text.encode()).hexdigest(),
             'extraction_version': 'bounded-snapshot-v1', 'token_limit': 100000,
             'truncated': 'TRUNCATED' in text, 'omitted_large_files': '[OMITTED:' in text}
    root.mkdir(parents=True, exist_ok=True)
    (root / 'content.txt').write_text(text)
    manifest.write_text(json.dumps(saved))
    return text, saved
