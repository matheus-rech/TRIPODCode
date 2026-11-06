"""Resource limits and safe archive handling for untrusted research inputs."""
import hashlib
import ipaddress
from pathlib import Path, PurePosixPath
import socket
import stat
from urllib.parse import urlparse, urljoin
import zipfile
import requests

MAX_DOWNLOAD = 50 * 1024 * 1024
MAX_EXPANDED = 100 * 1024 * 1024
MAX_FILES = 5000
MAX_FILE = 2 * 1024 * 1024

def public_https(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Public HTTPS URLs without credentials are required')
    for record in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(record[4][0]).is_global:
            raise ValueError('Private network destinations are forbidden')
    return url

def request_public(url, method='GET', **kwargs):
    for _ in range(6):
        public_https(url)
        response = requests.request(method, url, timeout=(10, 30), allow_redirects=False, **kwargs)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location')
            response.close()
            if not location:
                raise ValueError('Redirect without destination')
            url = urljoin(url, location)
            continue
        response.raise_for_status()
        return response
    raise ValueError('Too many redirects')

def download(url, target, max_bytes=MAX_DOWNLOAD):
    total = 0
    target = Path(target)
    try:
        with request_public(url, stream=True) as response, target.open('wb') as stream:
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError('Download exceeds resource limit')
                stream.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return total

def safe_destination(root, name):
    parts = PurePosixPath(name).parts
    if not parts or name.startswith('/') or '\\' in name or ':' in name or '..' in parts or '\x00' in name:
        raise ValueError('Unsafe archive filename')
    target = Path(root).joinpath(*parts)
    if not target.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Archive path escapes destination')
    return target

def safe_extract_zip(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_EXPANDED:
            raise ValueError('Archive exceeds resource limit')
        paths = set()
        for item in members:
            target = safe_destination(destination, item.filename)
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Archive links and special files are forbidden')
            key = str(target).casefold()
            if key in paths:
                raise ValueError('Duplicate archive path')
            paths.add(key)
            if item.file_size > MAX_FILE or (item.compress_size and item.file_size/item.compress_size > 1000):
                raise ValueError('Archive member exceeds resource limit')
        for item in members:
            target = safe_destination(destination, item.filename)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, target.open('xb') as output:
                    remaining = item.file_size
                    while chunk := source.read(min(65536, remaining+1)):
                        remaining -= len(chunk)
                        if remaining < 0:
                            raise ValueError('Invalid archive size')
                        output.write(chunk)

def cache_name(url):
    return hashlib.sha256(url.rstrip('/').removesuffix('.git').encode()).hexdigest()
