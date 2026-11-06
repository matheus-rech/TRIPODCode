export type Stage='article'|'repository';
export type Dataset={id:string;name:string;row_count:number;kind:string;sha256:string;created:string};
export type RecordRow={id:string;title:string;text:string|null;repo_content:string|null;repo_url:string|null;human:Partial<Record<Stage,Record<string,unknown>>>};
export type Job={id:string;dataset_id:string;state:string;progress:number;total:number;created:string;error:string|null;identity:string;config:{stage:Stage;mode:string;model:string};provenance:Record<string,unknown>};
export type Result={record_id:string;status:string;assessment:Record<string,unknown>|null;error:string|null;evidence:Record<string,unknown>};
export type Metric={field:string;n:number;excluded:number;tp:number;tn:number;fp:number;fn:number;accuracy:number|null;precision:number|null;recall:number|null;f1:number|null};
export type Evaluation={metrics:Metric[];note:string;version:string};
export const active=(state:string)=>['queued','running','cancelling'].includes(state);
export const resumable=(state:string)=>['cancelled','interrupted','incomplete','failed'].includes(state);
export function assessmentValue(field:string,value:unknown,assessment:Record<string,unknown>={}):string {
  if(value===true)return 'Yes';
  if(value===false)return 'No';
  if(value===null||value===undefined){
    if((field==='readme_purpose_and_outputs'&&assessment.contains_readme===false)||
       (field==='requirements_dependency_versions'&&assessment.contains_requirements===false))return 'Not applicable';
    return 'Not reported';
  }
  return Array.isArray(value)?value.join(', '):String(value);
}
export const label=(value:string)=>value.replaceAll('_',' ').replace(/^./,s=>s.toUpperCase());
export const percent=(value:number|null)=>value===null?'—':(value*100).toFixed(1)+'%';
