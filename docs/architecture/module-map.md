# Module map

Baseline e217630579a2521c92e04449756326331f740a43.

| Source / symbol | Responsibility | Dependencies / callers |
|---|---|---|
| src/llm_utils/llm_wrapper.py::LLM_wrapper | Structured API and DataFrame checkpoints | OpenAI, pandas, tqdm; notebooks 02b/02c/03b/03d |
| src/llm_utils/structs.py::PaperAssessment | Inclusion, reason, country, code statement/repo | Pydantic; required booleans/strings |
| src/llm_utils/structs.py::RepoAssessment | Repository criteria and nullable conditions | Pydantic; notebooks 03 |
| src/llm_utils/*_assessment_prompt.py | Scientific instructions | Preserved unchanged |
| src/repo_utils/repo_providers.py::get_repo_cloner | Git/Zenodo/Figshare/OSF/DOI acquisition | GitPython, requests, zenodo_get/osf |
| src/repo_utils/main_extractor.py::read_all_files | Exclusions, ordering, token budgets | tokenizer, clone_and_extract_tree |
| src/repo_utils/tokenizer.py::extract_text_from_file | PDF/DOCX/notebook/text parsing | PyPDF2, python-docx, pandas; no cell execution |
| src/repo_utils/tokenizer.py::tokenize_text | cl100k_base tokenization | tiktoken; first-use encoding download |
| notebooks/00–04 | Scientific orchestration and publication plots | datasets, sklearn, plotting libraries, stored corpus |

Original CI uses .github/workflows/tests.yml and Conda. Existing tests mock downloads/API calls; some explicitly expect buggy retry exhaustion and model-only checkpoint behavior. Intentional changes require regression coverage and documented migration.
