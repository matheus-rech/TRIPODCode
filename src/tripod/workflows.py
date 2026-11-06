"""Pure extraction of notebook stages 00, 01 and 02a; no network or pickle loading.

Input order is explicit because the published stage-00 method retains the first
duplicate PMID. This module preserves that behavior rather than sorting silently.
"""
from pathlib import Path
import hashlib
import json
import pandas as pd

def load_reference_group(paths):
    group = {}
    for filename in paths:
        path = Path(filename)
        statement = int(path.name.split('_')[0])
        if statement in group:
            raise ValueError('Duplicate statement export; specify exactly one file per statement')
        frame = pd.read_csv(path)
        if 'PMID' not in frame:
            raise ValueError('Reference export requires PMID')
        group[statement] = frame.iloc[1:].reset_index(drop=True)
    if not group:
        raise ValueError('Reference group is empty')
    return group

def combine_reference_groups(*groups):
    combined = []
    counts = []
    for group in groups:
        frame = pd.concat(group.values(), ignore_index=True)
        before = len(frame)
        frame = frame.drop_duplicates(subset=['PMID'], keep='first')
        duplicates = before - len(frame)
        statements = frame['PMID'].isin(set(group))
        counts.append({'input_rows':before,'duplicate_pmids':duplicates,'statement_rows':int(statements.sum())})
        combined.append(frame[~statements].reset_index(drop=True))
    result = pd.concat(combined, ignore_index=True).drop_duplicates().reset_index(drop=True)
    if not result['PMID'].is_unique:
        raise ValueError('Conflicting records share a PMID across reference groups')
    return result, {'method':'notebook-00-equivalent-v1','groups':counts,'output_rows':len(result)}

def attach_full_text(references, mapping):
    if not references['PMID'].is_unique:
        raise ValueError('Reference PMIDs must be unique')
    result = references.copy()
    result['full_text'] = result['PMID'].astype(str).map(mapping)
    retained = result[result['full_text'].notnull()].reset_index(drop=True)
    return retained, {'method':'notebook-01-equivalent-v1','input_rows':len(result),
                      'missing_full_text':int(result['full_text'].isna().sum()),'output_rows':len(retained)}

def prepare_paper_annotations(annotations, full_text):
    if not full_text['PMID'].is_unique:
        raise ValueError('Full-text PMIDs must be unique; annotation joins must not expand rows')
    joined = annotations.merge(full_text[['PMID','full_text']],on='PMID',how='left',validate='many_to_one')
    joined = joined.rename(columns={c:'gt_'+c for c in ['in_scope','has_repo','repo_url']})
    return joined[['PMID','full_text','gt_in_scope','gt_has_repo','gt_repo_url']]

def write_prepared_references(tripod_paths, ai_paths, output_directory):
    target = Path(output_directory)
    target.mkdir(parents=True, exist_ok=True)
    output = target/'merged_references.parquet'
    manifest = target/'lineage.json'
    if output.exists() or manifest.exists():
        raise FileExistsError('Choose a new output directory; research artifacts are immutable')
    result, lineage = combine_reference_groups(load_reference_group(tripod_paths),load_reference_group(ai_paths))
    lineage['ordered_inputs'] = [{'name':Path(p).name,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                                 for p in [*tripod_paths,*ai_paths]]
    result.to_parquet(output,index=False)
    lineage['output_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(lineage,indent=2))
    return output, manifest
