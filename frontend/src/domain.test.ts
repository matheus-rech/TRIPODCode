import {describe,it,expect} from 'vitest';
import {assessmentValue,active,resumable,percent} from './domain';
describe('scientific value presentation',()=>{
 it('keeps negative, unreported and inapplicable distinct',()=>{
  expect(assessmentValue('contains_readme',false)).toBe('No');
  expect(assessmentValue('contains_readme',null)).toBe('Not reported');
  expect(assessmentValue('readme_purpose_and_outputs',null,{contains_readme:false})).toBe('Not applicable');
  expect(assessmentValue('fixes_seed_if_stochastic',null)).toBe('Not reported');
 });
 it('never formats undefined denominators as zero percent',()=>expect(percent(null)).toBe('—'));
 it('offers resume only for terminal recoverable states',()=>{
  expect(resumable('running')).toBe(false);expect(resumable('interrupted')).toBe(true);expect(active('cancelling')).toBe(true);
 });
});
