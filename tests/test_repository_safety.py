import io
from pathlib import Path
import stat
import zipfile
import pytest
from src.repo_utils.safety import safe_extract_zip, safe_destination, cache_name

@pytest.mark.parametrize('name',['../escape','/absolute','a/../../escape','C:\\escape','a\\..\\escape'])
def test_rejects_archive_traversal(tmp_path,name):
    with pytest.raises(ValueError):safe_destination(tmp_path,name)

def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for name,body in entries:z.writestr(name,body)
    stream.seek(0);return stream

def test_validates_whole_archive_before_writing(tmp_path):
    with pytest.raises(ValueError):safe_extract_zip(archive([('good.txt','ok'),('../escape','no')]),tmp_path)
    assert list(tmp_path.iterdir())==[]

def test_rejects_symlink(tmp_path):
    item=zipfile.ZipInfo('link');item.create_system=3;item.external_attr=(stat.S_IFLNK|0o777)<<16
    with pytest.raises(ValueError):safe_extract_zip(archive([(item,'/etc/passwd')]),tmp_path)

def test_rejects_duplicate_casefold_paths(tmp_path):
    with pytest.raises(ValueError):safe_extract_zip(archive([('A.py','a'),('a.py','b')]),tmp_path)

def test_normal_archive_preserves_content(tmp_path):
    safe_extract_zip(archive([('source/a.py','print(1)')]),tmp_path)
    assert (tmp_path/'source/a.py').read_text()=='print(1)'

def test_cache_owner_identity():
    assert cache_name('https://github.com/a/repo')!=cache_name('https://github.com/b/repo')
    assert cache_name('https://github.com/a/repo.git')==cache_name('https://github.com/a/repo/')
