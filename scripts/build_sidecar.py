"""Build a native, self-contained Python sidecar. Run on the target architecture."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.tripod.provenance import code_version

def main():
    if sys.platform!='darwin':
        raise SystemExit('Build the macOS sidecar on macOS; cross-building Python is not supported.')
    target='aarch64-apple-darwin' if platform.machine()=='arm64' else 'x86_64-apple-darwin'
    scratch=ROOT/'build'/'sidecar';scratch.mkdir(parents=True,exist_ok=True)
    cache=scratch/'tiktoken_cache';cache.mkdir(exist_ok=True)
    os.environ['TIKTOKEN_CACHE_DIR']=str(cache)
    import tiktoken
    tiktoken.get_encoding('cl100k_base')  # Fetch once at build time; runtime is offline.
    info=code_version()
    try:info['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except subprocess.CalledProcessError:info['git_commit']=None
    info.update(build='pyinstaller',target=target,python=sys.version.split()[0],
                packages={n:version(n) for n in ['openai','pydantic','pandas','tiktoken','pyarrow','fastapi','pyinstaller']})
    manifest=ROOT/'src/tripod/build-info.json'
    if manifest.exists():raise SystemExit('Remove stale generated build-info.json before building')
    manifest.write_text(json.dumps(info,indent=2))
    try:
        command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile',
            '--name','tripod-backend','--distpath',str(scratch/'dist'),'--workpath',str(scratch/'work'),
            '--specpath',str(scratch),'--paths',str(ROOT),'--collect-all','tiktoken_ext',
            '--collect-all','keyring','--hidden-import','keyring.backends.macOS',
            '--hidden-import','pyarrow','--hidden-import','pyarrow.parquet',
            '--add-data',f'{ROOT / "src/tripod/fixtures"}:src/tripod/fixtures',
            '--add-data',f'{manifest}:src/tripod',
            '--add-data',f'{cache}:tiktoken_cache',str(ROOT/'scripts/sidecar_entry.py')]
        subprocess.run(command,cwd=ROOT,check=True)
        destination=ROOT/'desktop/src-tauri/binaries'/f'tripod-backend-{target}'
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(scratch/'dist/tripod-backend',destination);destination.chmod(0o755)
        info['binary_sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
        (scratch/'build-manifest.json').write_text(json.dumps(info,indent=2))
        print(destination)
    finally:manifest.unlink(missing_ok=True)
if __name__=='__main__':main()
