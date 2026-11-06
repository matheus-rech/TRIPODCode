from pathlib import Path
import pytest
from src.repo_utils import main_extractor as extractor

class CharacterEncoder:
    def decode(self, tokens): return ''.join(chr(x) for x in tokens)
@pytest.fixture(autouse=True)
def deterministic_budget(monkeypatch):
    # Unit-test the budget accounting independently of external tokenizer assets.
    monkeypatch.setattr(extractor,'tokenize_text',lambda text:(list(map(ord,text)),CharacterEncoder()))

def test_sorted_extraction_excludes_hidden_and_symlinks(tmp_path):
    (tmp_path/'z.py').write_text('z = 1')
    (tmp_path/'a.py').write_text('a = 1')
    (tmp_path/'.git').mkdir();(tmp_path/'.git'/'config').write_text('SECRET')
    (tmp_path/'link.py').symlink_to(tmp_path/'.git'/'config')
    output=extractor.read_all_files(tmp_path,False,10000)
    assert output.index('FILE: a.py')<output.index('FILE: z.py')
    assert 'SECRET' not in output and 'link.py' not in output
    assert [node.name for node in extractor.get_tree(tmp_path)]==['a.py','z.py']

def test_global_budget_includes_headers_and_truncation_notice(tmp_path):
    (tmp_path/'a.py').write_text('value = 1\n'*500)
    output=extractor.read_all_files(tmp_path,False,100)
    assert len(output)<=100 and 'TRUNCATED' in output

def test_nested_readme_is_not_subject_to_per_file_cutoff(tmp_path):
    (tmp_path/'docs').mkdir();text='documentation '*300
    (tmp_path/'docs'/'README.md').write_text(text)
    assert text in extractor.read_all_files(tmp_path,False,10000)

def test_empty_files_do_not_manufacture_content(tmp_path):
    (tmp_path/'empty.py').write_text('')
    assert extractor.read_all_files(tmp_path,False,100)==''

def test_context_budget_includes_repository_tree(tmp_path,monkeypatch):
    for i in range(20):(tmp_path/f'file{i}.py').write_text('x = 1')
    class Cloner:
        def clone(self,*args):return tmp_path
    monkeypatch.setattr(extractor,'get_repo_cloner',lambda *_:Cloner())
    result=extractor.clone_and_extract_tree('https://github.com/example/repo',100,str(tmp_path))
    assert result.status==extractor.RepoStatus.OK
    assert len(result.output)<=100
