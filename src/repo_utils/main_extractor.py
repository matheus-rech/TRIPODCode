from pathlib import Path
import re
from pydantic import BaseModel, HttpUrl
from enum import Enum
from typing import List, Union, Optional
from urllib.parse import urlparse
import os
from .safety import MAX_FILES, MAX_FILE
from .repo_providers import get_repo_cloner, RepoNotSupportedError
from .tokenizer import extract_text_from_file, tokenize_text

TOKEN_CUTOFF_PER_FILE = 3000


class RepoStatus(str, Enum):
    """
    Enumeration of possible repository extraction statuses.

    :cvar OK: Repository was successfully cloned and extracted.
    :cvar EMPTY: Repository exists but contains no meaningful content.
    :cvar INACCESSIBLE: Repository could not be accessed (network error, private, etc.).
    :cvar NOT_SUPPORTED: Repository URL is from an unsupported platform.
    """

    OK = "ok"
    EMPTY = "empty"
    INACCESSIBLE = "inaccessible"
    NOT_SUPPORTED = "not_supported"


class RepoExtractionResult(BaseModel):
    """
    Result of a repository extraction operation.

    :param repo_url: The original URL of the repository.
    :type repo_url: str
    :param status: The status of the extraction operation.
    :type status: RepoStatus
    :param repo_path: Local path to the cloned repository (if successful).
    :type repo_path: str, optional
    :param output: Extracted content including tree structure and file contents.
    :type output: str, optional
    :param error: Error message if extraction failed.
    :type error: str, optional
    """

    repo_url: str
    status: RepoStatus
    repo_path: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


class RepoTree(BaseModel):
    """
    Tree structure representing a file or directory in a repository.

    :param name: Name of the file or directory.
    :type name: str
    :param children: List of child nodes (for directories). None for files.
    :type children: list[RepoTree], optional
    """

    name: str
    children: Union[List["RepoTree"], None] = None


RepoTree.model_rebuild()


class RepoInfo(BaseModel):
    """
    Repository metadata including URL and file tree structure.

    :param url: URL of the repository.
    :type url: HttpUrl
    :param tree: List of top-level files and directories in the repository.
    :type tree: list[RepoTree]
    """

    url: HttpUrl
    tree: List[RepoTree]


def _paths(root):
    """Stable bounded traversal, shared by tree and content; never follow links."""
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in
                         {'node_modules', '__pycache__', '.venv'} and
                         not (Path(directory) / d).is_symlink())
        if len(Path(directory).relative_to(root).parts) > 30:
            dirs[:] = []
            continue
        for name in sorted(files):
            path = Path(directory) / name
            if name.startswith('.') or path.is_symlink() or not path.is_file():
                continue
            count += 1
            if count > MAX_FILES:
                raise ValueError('Repository exceeds file limit')
            yield path

def get_tree(path: Path) -> List[RepoTree]:
    roots = {}
    for file in sorted(_paths(path)):
        current = roots
        parts = file.relative_to(path).parts
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = None
    def nodes(mapping):
        return [RepoTree(name=name, children=nodes(child) if child is not None else None)
                for name, child in sorted(mapping.items())]
    return nodes(roots)


# file that will be excluded from the text string but are reported in the repo tree
block_list = {
    ".pdf", ".docx",  # opaque document parsers are outside bounded repository assessment
    ".pt",
    ".pth",
    ".pkl",
    ".h5",
    ".onnx",  # model checkpoints
    ".pack",  # compressed binary file for commits, blob, etc
    ".lock",  # lock files for dependency management
    ".log",
    ".bin",
    ".db",
    ".sqlite",  # large logs/databases
    ".zip",
    ".tar",
    ".gz",
    ".7z",  # compressed archives
    ".csv",
    ".tsv",
    ".parquet",
    ".feather",
    ".arrow",
    ".xls",
    ".xlsx",
    ".sav",
    ".dta",
    ".sas7bdat",
    ".jsonl",
    ".hdf5",
    ".mat",
    ".npy",
    ".npz",
    ".rds",
    ".rdata",
    ".avro",
    ".orc",
    ".mdb",
    ".accdb",
    ".dbf",
    ".pqt",
    ".rec",
    ".arff",
    ".psv",
    ".br",
}

# file included without any token cutoff
allow_list = {
    ".py",
    ".ipynb",
    ".r",
    ".java",
    ".jl",
    ".kt",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".swift",
    ".php",
    ".rb",
    ".cs",
    ".scala",
    ".hs",
    ".dart",
    ".lua",
    ".pl",
    ".fs",
    ".asm",
    ".toml",
}


def read_all_files(base_path: Path, verbose: bool, context_window: int) -> str:
    """
    Read and concatenate all files from a repository with token management.

    Files are processed with the following rules:

    - Files in :data:`block_list` (binary, data files) are excluded entirely.
    - Files in :data:`allow_list` (code files) are included in full.
    - Other files are truncated at :data:`TOKEN_CUTOFF_PER_FILE` tokens.
    - README files are always included in full regardless of extension.
    - Total output is limited to ``context_window`` tokens.

    :param base_path: Root path of the repository to read.
    :type base_path: Path
    :param verbose: If True, print warnings for files that cannot be read.
    :type verbose: bool
    :param context_window: Maximum total tokens to include in output.
    :type context_window: int
    :return: Concatenated file contents with headers indicating file paths.
    :rtype: str

    :Example:

    >>> content = read_all_files(Path("/repo"), verbose=False, context_window=50000)
    >>> "FILE: README.md" in content
    True
    """
    if context_window < 32:
        raise ValueError('context_window must be at least 32')
    content = ''
    notice = '\n(REST OF THE REPOSITORY IS TRUNCATED)'
    for file_path in sorted(_paths(base_path)):
        if file_path.suffix.lower() in block_list:
            continue
        if file_path.stat().st_size > MAX_FILE:
            segment = f'\n\nFILE: {file_path.relative_to(base_path)}\n[OMITTED: file exceeds byte limit]'
        else:
            text = extract_text_from_file(file_path)
            if not text.strip():
                continue
            is_readme = bool(re.match(r'^readme(?:\.|$)', file_path.name, re.IGNORECASE))
            tokens, enc = tokenize_text(text)
            if not is_readme and file_path.suffix.lower() not in allow_list and len(tokens) > TOKEN_CUTOFF_PER_FILE:
                text = enc.decode(tokens[:TOKEN_CUTOFF_PER_FILE]) + '\n[CONTENT TRUNCATED]'
            segment = f'\n\nFILE: {file_path.relative_to(base_path)}\n{text}'
        tokens, enc = tokenize_text(content + segment)
        if len(tokens) > context_window:
            marker, _ = tokenize_text(notice)
            content = enc.decode(tokens[:max(0, context_window-len(marker)-4)]) + notice
            while len(tokenize_text(content)[0]) > context_window:
                content = content[:-len(notice)-1] + notice
            break
        content += segment
    return content


def clone_and_extract_tree(
    repo_url: str,
    context_window: int,
    clone_dir: str,
    verbose: bool = False,
) -> RepoExtractionResult:
    """
    Clone a repository and extract its content for analysis.

    This is the main entry point for repository extraction. It:

    1. Determines the appropriate cloner based on the URL
    2. Clones the repository (or uses cached version if exists)
    3. Builds a tree structure of all files
    4. Extracts and concatenates file contents
    5. Returns structured results

    :param repo_url: URL of the repository to clone and extract.
    :type repo_url: str
    :param context_window: Maximum tokens to include in extracted content.
    :type context_window: int
    :param clone_dir: Local directory path for storing cloned repositories.
    :type clone_dir: str
    :param verbose: If True, print detailed progress and error messages.
    :type verbose: bool
    :return: Extraction result containing status, path, and content.
    :rtype: RepoExtractionResult

    :Example:

    >>> result = clone_and_extract_tree(
    ...     repo_url="https://github.com/user/repo",
    ...     context_window=100000,
    ...     clone_dir="./cloned_repos",
    ... )
    >>> result.status
    <RepoStatus.OK: 'ok'>
    >>> "Repository tree" in result.output
    True
    """

    try:
        cloner = get_repo_cloner(repo_url)
        base = Path(clone_dir)
        base.mkdir(parents=True, exist_ok=True)

        repo_path = cloner.clone(repo_url, base)

        text = read_all_files(repo_path, verbose, context_window)

        if not text.strip():
            return RepoExtractionResult(
                repo_url=repo_url,
                status=RepoStatus.EMPTY,
                repo_path=str(repo_path),
            )

        tree = get_tree(repo_path)
        repo_info = RepoInfo(url=repo_url, tree=tree)

        output = (
            f"Repository tree\n{repo_info.model_dump_json(indent=2)}"
            f"\nFiles content\n{text}"
        )

        tokens, enc = tokenize_text(output)
        if len(tokens) > context_window:
            marker = '\n[REPOSITORY TRUNCATED]'
            output = enc.decode(tokens[:max(0, context_window-len(tokenize_text(marker)[0])-4)]) + marker
        return RepoExtractionResult(
            repo_url=repo_url,
            status=RepoStatus.OK,
            repo_path=str(repo_path),
            output=output,
        )

    except RepoNotSupportedError as e:
        return RepoExtractionResult(
            repo_url=repo_url,
            status=RepoStatus.NOT_SUPPORTED,
            error=str(e),
        )

    except Exception as e:
        if verbose:
            print(f"ERROR processing {repo_url}: {e}")
        return RepoExtractionResult(
            repo_url=repo_url,
            status=RepoStatus.INACCESSIBLE,
            error=str(e),
        )
