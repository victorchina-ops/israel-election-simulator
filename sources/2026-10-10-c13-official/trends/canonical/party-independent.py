"""Independent exhaustive party-trend audit; no production data modifications.

Uses lstsq regressions and direct Cartesian tail enumeration instead of the
main analysis's coefficient formula / meet-in-the-middle searchsorted count.
"""
from pathlib import Path
from datetime import date
from itertools import permutations, product
import hashlib
import importlib.util
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
helper_spec = importlib.util.spec_from_file_location('independent_compressed_counts', OUT/'independent-compressed-counts.py')
helper = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(helper)
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

verified = read(OUT/'analysis.json')
history = read(ROOT/'data/poll-history.json')
parties = [p for p in read(ROOT/'data/parties.json') if p['ballot']]
ids = [p['id'] for p in parties]
assert len(ids) == 17
byid = {p['id']:p for p in history['polls']}
eligible = [p for p in verified['cohort'] if p['eligibleStrict']]
assert len(eligible) == verified['primary']['nPolls']
assert len({p['pollId'] for p in eligible}) == len(eligible)
weights = verified['normalizedHistoricalWeights']
assert len(weights) == verified['primary']['nPollsters']
assert math.isclose(sum(weights.values()),1.,abs_tol=1e-12)
raw = read(ROOT/'data/calibration.json')['pollsterQuality']
denom = sum(raw[k]['weight'] for k in weights)
assert all(math.isclose(w,raw[k]['weight']/denom,abs_tol=1e-12) for k,w in weights.items())

def adj_bh(pvalues):
    arr = np.asarray(pvalues,dtype=float)
    order = np.argsort(arr)
    ordered = arr[order]*len(arr)/np.arange(1,len(arr)+1)
    ordered = np.minimum.accumulate(ordered[::-1])[::-1]
    result = np.empty_like(arr)
    result[order] = np.minimum(ordered,1)
    return result

def midpoint(row):
    assert row['fieldworkStart'] >= '2026-09-09'
    return (date.fromisoformat(row['fieldworkStart']).toordinal()+date.fromisoformat(row['fieldworkEnd']).toordinal())/2

records=[]
perms=[]
compressed=[]
observed=[]
net_changes=[]
indiv=[]
for pid,w in weights.items():
    polls=sorted([r for r in eligible if r['pollsterId']==pid],key=midpoint)
    xx=np.array([midpoint(r) for r in polls]);xx-=xx[0]
    design=np.stack([np.ones(len(xx)),xx/7],axis=1)
    yy=[]
    for r in polls:
        seats=byid[r['pollId']]['seats']
        assert sum(seats.values()) == 120
        assert set(seats).issubset(ids)
        yy.append([seats.get(p,0) for p in ids])
    yy=np.asarray(yy,dtype=float)
    assert np.all(yy.sum(axis=1)==120)
    slope=np.linalg.lstsq(design,yy,rcond=None)[0][1]
    assert abs(slope.sum())<1e-10
    orders=np.asarray(list(permutations(range(len(polls)))))
    cases=np.asarray([np.linalg.lstsq(design,yy[order],rcond=None)[0][1]
                      for order in orders])
    assert len(cases)==math.factorial(len(polls))
    assert np.max(abs(cases.mean(axis=0)))<1e-10
    pvals=np.mean(abs(cases)>=abs(slope)-1e-10,axis=0)
    for j,p in enumerate(parties):
        indiv.append({'pollsterId':pid,'partyId':p['id'],'slopePerWeek':float(slope[j]),
                      'delta':int(yy[-1,j]-yy[0,j]),'p':float(pvals[j]),'series':yy[:,j].astype(int).tolist()})
    observed.append(w*slope)
    net_changes.append(w*(yy[-1]-yy[0]))
    perms.append(w*cases)
    compressed.append(helper.score_blocks(xx, yy, orders, w))
    records.append({'pollsterId':pid,'weight':w,'pollIds':[r['pollId'] for r in polls],
                    'days':xx.tolist(),'n':len(polls)})

obs=np.sum(observed,axis=0)
net=np.sum(net_changes,axis=0)
counts,total,compressed_sizes=helper.direct_tail_counts(compressed,obs,tolerance=1e-12)
assert total==math.prod(math.factorial(row['n']) for row in records)
pv=counts/total
qv=adj_bh(pv)
signed=np.asarray([sum(s*x for s,x in zip(signs,observed))
                   for signs in product([-1,1],repeat=len(records))])
assert len(signed)==2**len(records)
sp=np.mean(abs(signed)>=abs(obs)-1e-10,axis=0)
sq=adj_bh(sp)
iq=adj_bh([r['p'] for r in indiv])
for r,q in zip(indiv,iq):r['q']=float(q)
overall=[{'partyId':p['id'],'name':p['name'],'slopePerWeek':float(obs[j]),'netDelta':float(net[j]),
          'p':float(pv[j]),'q':float(qv[j]),'signFlipP':float(sp[j]),'signFlipQ':float(sq[j]),
          'extremeCount':int(counts[j]),'extremeCountExact':str(int(counts[j]))} for j,p in enumerate(parties)]
result={'cohortSha256':hashlib.sha256((OUT/'analysis.json').read_bytes()).hexdigest(),
        'historySha256':hashlib.sha256((ROOT/'data/poll-history.json').read_bytes()).hexdigest(),
        'nPolls':len(eligible),'nSeries':len(records),'nParties':len(ids),'nIndividualTests':len(indiv),
        'independentCounting':'Independent lstsq slopes and direct bounded scalar Cartesian tails with integer-score multiplicities; absolute tail tolerance 1e-12 matches the primary counter.',
        'compressedHalfSizes':compressed_sizes,
        'nPermutations':total,'nPermutationsExact':str(total),'nSignPatterns':len(signed),'overall':overall,'byPollster':indiv,'series':records,
        'interpretation':'These are published mandate trends; zero seats do not mean zero support. Four always-zero-seat parties are retained at p=1 in the testing family.'}
(OUT/'party-independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'overall':overall,'individualRawSignificant':[r for r in indiv if r['p']<.05],
                  'individualBHSignificant':[r for r in indiv if r['q']<.05]},ensure_ascii=False,indent=2))
