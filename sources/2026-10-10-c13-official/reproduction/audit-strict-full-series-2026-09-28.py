from pathlib import Path
import json,collections,datetime,itertools,importlib.util,numpy as np
R=Path(__file__).resolve().parents[1]; files=['n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json','lazar-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']; eligible=[]
helper_spec=importlib.util.spec_from_file_location('independent_compressed_counts',R/'artifacts/strict-post-close/independent-compressed-counts.py');helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper);compressed=[]
for f in files:
 d=json.loads((R/'artifacts/strict-post-close'/f).read_text(encoding='utf-8'))
 for row in d.get('rows',d.get('polls',[])):
  if row.get('eligibleStrict',row.get('includeInStrictPostClose',False)):eligible.append(row)
h={r['id']:r for r in json.loads((R/'data/poll-history.json').read_text(encoding='utf-8'))['polls']};q=json.loads((R/'data/calibration.json').read_text(encoding='utf-8'))['pollsterQuality'];g=collections.defaultdict(list)
verified=json.loads((R/'artifacts/strict-post-close/analysis.json').read_text(encoding='utf-8'))
assert len({row['pollId'] for row in eligible}) == len(eligible)
assert {row['pollId'] for row in eligible} == {row['pollId'] for row in verified['cohort'] if row['eligibleStrict']}
for row in eligible:g[row['pollsterId']].append(row)
assert all(len(rows) >= 2 for rows in g.values())
a={'likud','utj','shas','otzma','rz_zehut','winter','noam'};b={'yashar','beyachad','democrats','yisrael_beiteinu'};weights=np.array([q[k]['weight'] for k in sorted(g)]);weights/=weights.sum();blocks=[];obs=np.zeros(3);constant_factor=1;individual=[]
for weight,(pid,rs) in zip(weights,sorted(g.items())):
 rs.sort(key=lambda r:r['publicationDate']);origin=datetime.date.fromisoformat(rs[0]['fieldworkStart']).toordinal()
 x=np.array([((datetime.date.fromisoformat(r['fieldworkStart']).toordinal()-origin)+(datetime.date.fromisoformat(r['fieldworkEnd']).toordinal()-origin))/2 for r in rs]);times=x.copy();x-=x.mean();coef=x/(x@x)*7;y=np.array([[sum(h[r['pollId']]['seats'].get(i,0) for i in ids) for ids in [a,b,b|{'raam'}]] for r in rs]);sl=coef@y;obs+=weight*sl;dist=np.array([coef@y[list(ix)] for ix in itertools.permutations(range(len(rs)))]);individual.append({'pollsterId':pid,'slope':sl.tolist(),'p':(np.abs(dist)>=np.abs(sl)-1e-12).mean(axis=0).tolist()})
 compressed.append(helper.score_blocks(times,y,np.asarray(list(itertools.permutations(range(len(rs))))),weight))
 if np.max(np.abs(dist))<1e-12:constant_factor*=len(dist)
 else:blocks.append(weight*dist)
counts,total,compressed_sizes=helper.direct_tail_counts(compressed,obs,tolerance=1e-12)
p=counts/total
report={'cohortPolls':len(eligible),'cohortPollsters':len(g),'groups':['coalition','opposition','opposition_raam'],'slopes':obs.tolist(),'counts':counts.tolist(),'countsExact':[str(int(value)) for value in counts],'total':total,'totalExact':str(total),'p':p.tolist(),'method':'Independent direct scalar Cartesian enumeration in bounded chunks, preserving exact integer-score permutation multiplicities; no searchsorted counting. Relative fieldwork-day arithmetic avoids cancellation.','compressedHalfSizes':compressed_sizes,'individual':individual}
(R/'artifacts/strict-post-close/independent-strict-numeric-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
