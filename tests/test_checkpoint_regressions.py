import json
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from pydantic import BaseModel
from src.llm_utils.llm_wrapper import LLM_wrapper, AssessmentError

class Output(BaseModel):
    accepted: bool
    reason: str

def wrapper(prompt='original'):
    client=MagicMock()
    client.responses.parse.return_value.output_parsed=Output(accepted=False,reason='Negative reference fixture')
    return LLM_wrapper('model',prompt,Output,client=client)

def test_checkpoint_compatibility_and_original_annotation(tmp_path):
    path=tmp_path/'input.csv';pd.DataFrame({'text':['a','b'],'accepted':[True,True]}).to_csv(path,index=False)
    model=wrapper();result=model.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert list(result['accepted'])==[False,False]
    assert list(result['input__accepted'])==[True,True]
    model.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert model.client.responses.parse.call_count==2
    changed=wrapper('changed prompt');changed.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert changed.client.responses.parse.call_count==2
    pd.DataFrame({'text':['a','changed']}).to_csv(path,index=False)
    model.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert model.client.responses.parse.call_count==4

def test_missing_and_failure_never_become_negative(tmp_path):
    path=tmp_path/'input.csv';pd.DataFrame({'text':['','valid']}).to_csv(path,index=False)
    model=wrapper();model.client.responses.parse.side_effect=RuntimeError('secret')
    with patch('src.llm_utils.llm_wrapper.time.sleep'):
        result=model.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert list(result.assessment_status)==['missing','failed']
    assert result.accepted.isna().all()
    assert 'secret' not in result.to_json()

def test_refusal_has_explicit_exhaustion():
    model=wrapper();model.client.responses.parse.return_value.output_parsed=None
    with patch('src.llm_utils.llm_wrapper.time.sleep'),pytest.raises(AssessmentError):
        model.assess_one_row('text',max_retries=2)
    assert model.client.responses.parse.call_count==2

def test_cancel_checkpoint_resumes_only_pending_rows(tmp_path):
    path=tmp_path/'input.csv';pd.DataFrame({'text':['a','b']}).to_csv(path,index=False)
    model=wrapper()
    result=model.assess_dataframe(str(path),'text',str(tmp_path/'out'),stop_requested=lambda:model.client.responses.parse.call_count==1)
    assert list(result.assessment_status)==['succeeded','pending']
    result=model.assess_dataframe(str(path),'text',str(tmp_path/'out'))
    assert list(result.assessment_status)==['succeeded','succeeded']
    assert model.client.responses.parse.call_count==2
