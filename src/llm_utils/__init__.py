def __getattr__(name):
    if name == "LLM_wrapper":
        from .llm_wrapper import LLM_wrapper
        return LLM_wrapper
    raise AttributeError(name)
from .structs import PaperAssessment, RepoAssessment
from .repo_assessment_prompt import REPO_ASSESSMENT_PROMPT
from .paper_assessment_prompt import PAPER_ASSESSMENT_PROMPT
