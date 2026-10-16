"""Party follow-up to the verified post-closure bloc analysis.

Exact time permutations, fixed historical weights, same fieldwork-midpoint axis.
The tested family is predeclared as all17 ballot parties in data/parties.json.
"""
from pathlib import Path
from itertools import permutations, product
from datetime import date
import csv, hashlib, json, math, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/strict-post-close'
sys.path.insert(0, str(OUT))
from compressed_searchsorted_exact import integer_score_blocks, exact_counts
BASE=OUT/'analysis.json'
base=json.loads(BASE.read_text(encoding='utf-8'))
hist_path=ROOT/'data/poll-history.json'
assert hashlib.sha256(hist_path.read_bytes()).hexdigest()==base['historySha256']
history={p['id']:p for p in json.loads(hist_path.read_text(encoding='utf-8'))['polls']}
parties=[p for p in json.loads((ROOT/'data/parties.json').read_text(encoding='utf-8')) if p['ballot']]
IDS=[p['id'] for p in parties]
NAMES={p['id']:p['name'] for p in parties}
assert len(IDS)==17
weights=base['normalizedHistoricalWeights']
audit={p['pollId']:p for p in base['cohort'] if p['eligibleStrict']}
assert len(audit)==base['primary']['nPolls'] and len(weights)==base['primary']['nPollsters']
assert set(IDS)==set().union(*(history[k]['seats'].keys() for k in audit))
assert abs(sum(weights.values())-1)<1e-12

def bh(rows,pkey='pValue',qkey='qValue'):
    q=1.
    for rank,row in reversed(list(enumerate(sorted(rows,key=lambda r:r[pkey]),1))):
        q=min(q,row[pkey]*len(rows)/rank,1.)
        row[qkey]=q

def exact_combined(blocks,observed):
    return exact_counts(blocks, observed, tolerance=1e-12)

def timing(pid,axis):
    a=audit[pid]
    if axis=='publication': return float(date.fromisoformat(a['publicationDate']).toordinal())
    return (date.fromisoformat(a['fieldworkStart']).toordinal()+date.fromisoformat(a['fieldworkEnd']).toordinal())/2

def analyze(axis):
    records=[];individual=[];distributions=[]
    for series in base['primary']['byPollster']:
        pid=series['pollsterId'];w=weights[pid]
        pp=sorted(series['pollIds'],key=lambda k:timing(k,axis))
        assert all(k in audit for k in pp)
        t=np.array([timing(k,axis) for k in pp]);t-=t[0]
        x=t-t.mean();coeff=7*x/(x@x)
        assert np.all(np.diff(t)>0)
        y=np.array([[history[k]['seats'].get(p,0) for p in IDS] for k in pp],dtype=float)
        assert np.all(y.sum(axis=1)==120)
        assert np.all(y>=0) and np.all(y==np.round(y))
        dy=np.diff(y,axis=0);D=np.diff(np.eye(len(pp)),axis=0);dt=D@t
        z=np.linalg.solve(D@D.T,dt);gls=7*z/(dt@z)
        slopes=coeff@y
        assert np.allclose(slopes,gls@dy,atol=1e-12)
        assert np.array_equal(dy.sum(axis=0),y[-1]-y[0])
        perm=np.array(list(permutations(range(len(pp)))))
        ps=np.einsum('i,pij->pj',coeff,y[perm])
        assert len(ps)==math.factorial(len(pp))
        assert np.allclose(ps.mean(axis=0),0,atol=1e-12)
        distributions.append(integer_score_blocks(t, y.astype(np.int64), perm, w))
        rows=[]
        for j,party in enumerate(IDS):
            slope=float(slopes[j]) if abs(slopes[j])>1e-12 else 0.
            row={'pollsterId':pid,'partyId':party,'partyName':NAMES[party],'nPolls':len(pp),'nDeltas':len(pp)-1,
                'weight':w,'firstPublication':history[pp[0]]['date'],'lastPublication':history[pp[-1]]['date'],
                'firstSeats':int(y[0,j]),'lastSeats':int(y[-1,j]),'netDelta':int(dy[:,j].sum()),
                'slopePerWeek':slope,'pValue':float(np.mean(np.abs(ps[:,j])>=abs(slope)-1e-12)),
                'constantSeatSeries':bool(np.all(y[:,j]==y[0,j])),
                'seats':y[:,j].astype(int).tolist(),'deltas':dy[:,j].astype(int).tolist()}
            rows.append(row);individual.append(row)
        records.append({'pollsterId':pid,'weight':w,'pollIds':pp,'publicationDates':[history[k]['date'] for k in pp],
            'timeDaysFromFirst':t.tolist(),'parties':rows})
    bh(individual)
    w=np.array([r['weight'] for r in records]);slopes=np.array([[g['slopePerWeek'] for g in r['parties']] for r in records])
    obs=w@slopes;exact=exact_combined(distributions,obs)
    signs=np.array(list(product([-1,1],repeat=len(records))))
    sf=(signs*w)@slopes
    overall=[]
    for j,party in enumerate(IDS):
        rows=[r['parties'][j] for r in records]
        overall.append({'partyId':party,'partyName':NAMES[party],
            'weightedFirstSeats':sum(r['weight']*r['firstSeats'] for r in rows),
            'weightedLastSeats':sum(r['weight']*r['lastSeats'] for r in rows),
            'weightedNetDelta':sum(r['weight']*r['netDelta'] for r in rows),
            'slopePerWeek':float(obs[j]),'pValue':exact['pValues'][j],
            'wholeSeriesSignFlipP':float(np.mean(np.abs(sf[:,j])>=abs(obs[j])-1e-12)),
            'upwardSeries':int(np.sum(slopes[:,j]>1e-12)),
            'downwardSeries':int(np.sum(slopes[:,j]<-1e-12)),
            'flatSeries':int(np.sum(np.abs(slopes[:,j])<=1e-12)),
            'zeroSeatsThroughout':all(max(row['seats'])==0 for row in rows)})
    bh(overall);bh(overall,'wholeSeriesSignFlipP','wholeSeriesSignFlipQ')
    assert abs(sum(r['weightedNetDelta'] for r in overall))<1e-12
    assert abs(sum(r['slopePerWeek'] for r in overall))<1e-12
    # These party estimates must aggregate back to the already audited bloc estimates.
    source=base['primary'] if axis=='fieldwork-midpoint' else base['publicationDateSensitivity']
    lookup={r['partyId']:r for r in overall}
    for g in source['overall']:
        ids=base['groups'][g['group']]
        for key in ['weightedNetDelta','slopePerWeek']:
            assert abs(sum(lookup[i][key] for i in ids)-g[key])<1e-12
    return {'timeAxis':axis,'nPolls':len(audit),'nSeries':len(records),'nDeltas':len(audit)-len(records),'overall':overall,'byPollster':records,
        'exactCounting':exact,'wholeSeriesSignPatterns':len(signs),
        'significantPartiesBH':[r for r in overall if r['qValue']<.05],
        'significantPartiesSensitivityBH':[r for r in overall if r['wholeSeriesSignFlipQ']<.05],
        'significantIndividualRaw':[r for r in individual if r['pValue']<.05],
        'significantIndividualBH':[r for r in individual if r['qValue']<.05]}

primary=analyze('fieldwork-midpoint')
secondary=analyze('publication')
report={'asOf':base['asOf'],'baseAnalysisSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
    'historySha256':base['historySha256'],'partiesSha256':hashlib.sha256((ROOT/'data/parties.json').read_bytes()).hexdigest(),
    'cohort':base['cohort'],'closure':base['closure'],'normalizedHistoricalWeights':weights,'testedPartyIds':IDS,
    'method':{'primary':base['method']['primaryTest'],
        'statistic':'Historical-weighted mean of all-observation party seat slopes in mandates/week; equivalent to GLS of all adjacent deltas with covariance D D-transpose.',
        'timeAxis':base['method']['primaryTimeAxis'],
        'family':f'Predeclared{len(IDS)} modeled ballot parties; residualother excluded. BH across{len(IDS)} combined party tests; separately{len(IDS)*primary["nSeries"]} institute-party tests.',
        'sensitivity':f'Whole-institute slope sign-flips on the same fieldwork-midpoint axis: {primary["wholeSeriesSignPatterns"]} patterns, preserving each institute slope magnitude and historical weight, with BH across {len(IDS)} parties. A separate publication-date-axis sensitivity is also retained.',
        'zeros':'Complete published seat vectors sum120. Omitted seat keys imply0 assigned seats only. Constantzero parties get p=1 by convention; no inference about below-threshold vote shares.'},
    'limitations':base['limitations']+[
        'Seat thresholds create nonlinear jumps, especially0to4. This analysis cannot separate changing vote support from allocation and rounding effects.',
        'The four parties with zero reported seats throughout have no informative seat variation; their support percentages can still change.',
        'BH nominal guarantees require suitable dependence; party seats are compositional and cross-series errors may be dependent.'],
    'primary':primary,'publicationDateSensitivity':secondary}
reconciliation_path=OUT/'metadata-only-reconciliation.json'
if reconciliation_path.exists():
    report['metadataOnlyProvenanceReconciliation']=json.loads(reconciliation_path.read_text(encoding='utf-8'))
(OUT/'party-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for fname,rows in [('party-overall.csv',primary['overall']),('party-by-pollster.csv',[g for r in primary['byPollster'] for g in r['parties']])]:
    with (OUT/fname).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print(json.dumps({'overall':primary['overall'],'individualRaw':primary['significantIndividualRaw'],
    'individualBH':primary['significantIndividualBH'],'permutations':primary['exactCounting']['nPermutations']},ensure_ascii=False,indent=2))
