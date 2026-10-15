"""Reproducible analysis restricted to verified wholly post-closure fieldwork.

The primary axis is midpoint of the explicitly reported fieldwork dates.
Published dates are a prespecified sensitivity axis on the identical cohort.
No application or source data is mutated.
"""
from pathlib import Path
from itertools import permutations, product
from datetime import date
import json, csv, hashlib, math, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/strict-post-close'
sys.path.insert(0, str(OUT))
from compressed_searchsorted_exact import integer_score_blocks, exact_counts
history_path = ROOT / 'data/poll-history.json'
history = json.loads(history_path.read_text(encoding='utf-8'))
calibration = json.loads((ROOT/'data/calibration.json').read_text(encoding='utf-8'))
GROUPS = {
    'coalition': ['likud','shas','utj','otzma','rz_zehut','winter','noam'],
    'opposition': ['yashar','beyachad','democrats','yisrael_beiteinu'],
    'opposition_raam': ['yashar','beyachad','democrats','yisrael_beiteinu','raam'],
}
FILES = ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json',
         'new-unverified-fieldwork-2026-09-30.json']
audits = []
for name in FILES:
    obj = json.loads((OUT/name).read_text(encoding='utf-8-sig'))
    audits.extend(obj.get('polls', obj.get('rows', [])))
for r in audits:
    if 'eligibleStrict' not in r:
        r['eligibleStrict'] = r['includeInStrictPostClose']
audit_by_id = {r['pollId']: r for r in audits}
assert len(audit_by_id) == len(audits)
candidate_ids = {p['id'] for p in history['polls'] if p['date'] >= '2026-09-09'}
assert candidate_ids == set(audit_by_id)
eligible = [r for r in audits if r['eligibleStrict']]
assert len(eligible) >= 24
for r in eligible:
    assert '2026-09-09' <= r['fieldworkStart'] <= r['fieldworkEnd'] <= r['publicationDate']
eligible_ids = {r['pollId'] for r in eligible}
polls = [p for p in history['polls'] if p['id'] in eligible_ids]
for p in polls:
    assert p['date'] == audit_by_id[p['id']]['publicationDate']
    assert sum(p['seats'].values()) == 120
    assert all(isinstance(v,int) and v>=0 for v in p['seats'].values())
raw_weights = {pid:calibration['pollsterQuality'][pid]['weight'] for pid in sorted({p['pollsterId'] for p in polls})}
weights = {pid:w/sum(raw_weights.values()) for pid,w in raw_weights.items()}
assert abs(sum(weights.values())-1)<1e-12

def bh(rows, pk='pValue', qk='qValue'):
    running = 1.
    for rank,r in reversed(list(enumerate(sorted(rows,key=lambda r:r[pk]),1))):
        running = min(running, r[pk]*len(rows)/rank, 1.)
        r[qk] = running

def exact_combined(blocks,observed):
    return exact_counts(blocks, observed, tolerance=1e-12)

def timing(p,axis):
    a=audit_by_id[p['id']]
    if axis=='publication': return float(date.fromisoformat(p['date']).toordinal())
    return (date.fromisoformat(a['fieldworkStart']).toordinal()+date.fromisoformat(a['fieldworkEnd']).toordinal())/2

def analyze(axis):
    records=[];individual=[];distributions=[]
    for pid,weight in weights.items():
        pp=sorted([p for p in polls if p['pollsterId']==pid],key=lambda p:timing(p,axis))
        assert len(pp)>=2
        t=np.array([timing(p,axis) for p in pp]); t-=t[0]
        assert np.all(np.diff(t)>0)
        x=t-t.mean(); coeff=7*x/(x@x)
        y=np.array([[sum(p['seats'].get(k,0) for k in keys) for keys in GROUPS.values()] for p in pp],dtype=float)
        dy=np.diff(y,axis=0);D=np.diff(np.eye(len(pp)),axis=0);dt=D@t
        z=np.linalg.solve(D@D.T,dt); gls=7*z/(dt@z)
        slopes=coeff@y
        assert np.allclose(slopes,gls@dy,atol=1e-12)
        assert np.array_equal(dy.sum(axis=0),y[-1]-y[0])
        perm=np.array(list(permutations(range(len(pp)))))
        ps=np.einsum('i,pij->pj',coeff,y[perm])
        assert len(ps)==math.factorial(len(pp))
        assert np.allclose(ps.mean(axis=0),0,atol=1e-12)
        distributions.append(integer_score_blocks(t, y.astype(np.int64), perm, weight))
        rows=[]
        for j,g in enumerate(GROUPS):
            row={'pollsterId':pid,'group':g,'nPolls':len(pp),'nDeltas':len(pp)-1,'weight':weight,
                 'firstPublication':pp[0]['date'],'lastPublication':pp[-1]['date'],
                 'firstSeats':int(y[0,j]),'lastSeats':int(y[-1,j]),'netDelta':int(dy[:,j].sum()),
                 'slopePerWeek':float(slopes[j]),'pValue':float(np.mean(np.abs(ps[:,j])>=abs(slopes[j])-1e-12)),
                 'seats':y[:,j].astype(int).tolist(),'deltas':dy[:,j].astype(int).tolist()}
            rows.append(row);individual.append(row)
        records.append({'pollsterId':pid,'weight':weight,'dates':[p['date'] for p in pp],
            'fieldwork':[{'start':audit_by_id[p['id']]['fieldworkStart'],'end':audit_by_id[p['id']]['fieldworkEnd']} for p in pp],
            'pollIds':[p['id'] for p in pp],'timeDaysFromFirst':t.tolist(),
            'glsDeltaCoefficients':gls.tolist(),'groups':rows,
            'weightedEndpointPartyChanges':{k:weight*(pp[-1]['seats'].get(k,0)-pp[0]['seats'].get(k,0)) for k in set(pp[0]['seats'])|set(pp[-1]['seats'])}})
    bh(individual)
    w=np.array([r['weight'] for r in records]); slopes=np.array([[g['slopePerWeek'] for g in r['groups']] for r in records])
    obs=w@slopes; exact=exact_combined(distributions,obs)
    signs=np.array(list(product([-1,1],repeat=len(records))))
    sf=(signs*w)@slopes
    overall=[]
    for j,g in enumerate(GROUPS):
        overall.append({'group':g,'weightedNetDelta':sum(r['weight']*r['groups'][j]['netDelta'] for r in records),
            'slopePerWeek':float(obs[j]),'pValue':exact['pValues'][j],
            'wholeInstituteSignFlipP':float(np.mean(np.abs(sf[:,j])>=abs(obs[j])-1e-12))})
    bh(overall);bh(overall,'wholeInstituteSignFlipP','wholeInstituteSignFlipQ')
    party_deltas={}
    for r in records:
        for k,v in r['weightedEndpointPartyChanges'].items(): party_deltas[k]=party_deltas.get(k,0)+v
    assert abs(sum(party_deltas.values()))<1e-12
    return {'timeAxis':axis,'nPolls':len(polls),'nPollsters':len(records),'nDeltas':len(polls)-len(records),
        'overall':overall,'byPollster':records,'exactCounting':exact,'wholeInstituteSignPatterns':len(signs),
        'significantIndividualRaw':[r for r in individual if r['pValue']<.05],
        'significantIndividualBH':[r for r in individual if r['qValue']<.05],
        'weightedEndpointPartyChanges':party_deltas}

primary=analyze('fieldwork-midpoint')
sensitivity=analyze('publication')
report={
    'asOf':history['asOf'],'historySha256':hashlib.sha256(history_path.read_bytes()).hexdigest(),
    'closure':{'date':'2026-09-08','firstEligibleFieldworkDate':'2026-09-09',
        'sources':['https://www.gov.il/en/pages/time--table-26','https://www.idi.org.il/articles/65737'],
        'rule':'Entire fieldwork interval must be explicitly verified as starting on or after9Sep. Publication date is insufficient.'},
    'auditSources':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in FILES},
    'cohort':audits,'groups':GROUPS,'rawHistoricalWeights':raw_weights,'normalizedHistoricalWeights':weights,
    'method':{'statistic':'Historical-weighted mean of within-institute slopes in published mandates/week; OLS on all observations is exactly GLS on adjacent deltas with covariance D D-transpose.',
        'primaryTest':'Exact two-sided absolute-slope permutation of complete bloc vectors over fixed dates, separately within each institute. Assumes time exchangeability within institutes and independent permutation blocks.',
        'multiplicity':f'Benjamini-Hochberg separately across{len(GROUPS)} overall tests and{len(GROUPS)*len(weights)} institute-by-bloc tests. Dependence caveats apply.',
        'weighting':f'Existing historical accuracy weights, renormalized once over{len(weights)} verified institutes; no extra weight per published poll.',
        'primaryTimeAxis':'Midpoint of explicitly verified calendar-day fieldwork range; actual daily response weights are unavailable.',
        'sensitivity':f'Same cohort by publication date, plus sign-flips of whole institute slope vectors ({primary["wholeInstituteSignPatterns"]} combinations). Sign-flips preserve within-institute series but assume sign symmetry and independent institutes.'},
    'limitations':[f'Only{min(len(row["pollIds"]) for row in primary["byPollster"])}–{max(len(row["pollIds"]) for row in primary["byPollster"])} observations per institute; low power for individual series.',
        'Serially correlated errors, changing methods or shared calendar shocks can invalidate nominal permutation p-values. The whole-institute sensitivity is not a cure for cross-institute dependence.',
        'This tests trends in rounded, thresholded published seat projections, not raw respondents, actual voter switching, causality or election outcomes.',
        'Weighted net endpoint changes cover institute-specific observation ranges; their p-values are not endpoint tests. Inference tests the all-observation trend slope.',
        'Publication-only and unknown fieldwork polls remain in the underlying database but are excluded here.'],
    'primary':primary,'publicationDateSensitivity':sensitivity}
reconciliation_path=OUT/'metadata-only-reconciliation.json'
if reconciliation_path.exists():
    report['metadataOnlyProvenanceReconciliation']=json.loads(reconciliation_path.read_text(encoding='utf-8'))
(OUT/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'by-pollster.csv').open('w',encoding='utf-8-sig',newline='') as f:
    rr=[{**{k:v for k,v in g.items() if k not in ['seats','deltas']},'dates':' | '.join(r['dates']),
         'seats':' | '.join(map(str,g['seats'])),'deltas':' | '.join(map(str,g['deltas']))} for r in primary['byPollster'] for g in r['groups']]
    writer=csv.DictWriter(f,fieldnames=list(rr[0]));writer.writeheader();writer.writerows(rr)
print(json.dumps({'counts':[primary['nPolls'],primary['nPollsters'],primary['nDeltas']],
    'overall':primary['overall'],'publicationSensitivity':sensitivity['overall'],
    'individual':[{k:g[k] for k in ['pollsterId','group','netDelta','slopePerWeek','pValue','qValue']} for r in primary['byPollster'] for g in r['groups']],
    'partyDeltas':primary['weightedEndpointPartyChanges'],'exact':primary['exactCounting']},ensure_ascii=False,indent=2))
