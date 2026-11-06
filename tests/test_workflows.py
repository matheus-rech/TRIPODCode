import json
from pathlib import Path
import pandas as pd
import pytest
from src.tripod.workflows import combine_reference_groups, attach_full_text, prepare_paper_annotations
REFERENCE=json.loads((Path(__file__).parent/'fixtures/notebook_reference.json').read_text())

def test_recorded_notebook_stage_equivalence():
    a={100:pd.DataFrame({'PMID':[10,11,100,10],'Title':['Alpha','Beta','Statement','Duplicate ignored']})}
    b={200:pd.DataFrame({'PMID':[11,12],'Title':['Beta','Gamma']})}
    merged,lineage=combine_reference_groups(a,b)
    assert merged.to_dict('records')==REFERENCE['stage00']
    assert lineage['groups'][0]['duplicate_pmids']==1
    assert lineage['groups'][0]['statement_rows']==1
    full,counts=attach_full_text(merged,{'10':'Text alpha','12':'Text gamma'})
    assert full.to_dict('records')==REFERENCE['stage01']
    assert counts['missing_full_text']==1
    annotations=pd.DataFrame([{'PMID':10,'in_scope':True,'has_repo':False,'repo_url':None}])
    assert prepare_paper_annotations(annotations,full).to_dict('records')==REFERENCE['stage02a']

def test_conflicting_cross_group_pmids_are_not_arbitrarily_chosen():
    a={100:pd.DataFrame({'PMID':[10],'Title':['Alpha']})}
    b={200:pd.DataFrame({'PMID':[10],'Title':['Changed']})}
    with pytest.raises(ValueError,match='Conflicting'):combine_reference_groups(a,b)

def test_annotation_join_cannot_duplicate_human_rows():
    annotation=pd.DataFrame([{'PMID':1,'in_scope':True,'has_repo':False,'repo_url':None}])
    with pytest.raises(ValueError,match='unique'):
        prepare_paper_annotations(annotation,pd.DataFrame({'PMID':[1,1],'full_text':['a','b']}))
