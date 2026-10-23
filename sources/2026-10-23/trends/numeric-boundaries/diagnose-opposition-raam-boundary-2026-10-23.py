"""Diagnose only the actual23Oct opposition_raam floating-tail boundary.

Keep all original numeric outputs, frozen algorithms and1e-12 tolerance intact.
Reproduce direct sums at both observed values, then independently count the
primary subtraction predicate with the frozen two-pointer sweep in memory.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import sys
import time
import numpy as np

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-23/numeric-boundaries'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
import exact_scalar_marginals_2026_10_20 as backend
backend.verify_frozen_counters()


def main():
    inputs=['artifacts/strict-post-close/analysis.json','artifacts/strict-post-close/independent-strict-numeric-audit.json',
        'data/poll-history.json','data/current-polls.json','scripts/exact_scalar_marginals_2026_10_20.py',
        'artifacts/strict-post-close/compressed_searchsorted_exact.py','artifacts/strict-post-close/independent-compressed-counts.py']
    inputs+=['artifacts/strict-post-close/party-analysis.json','artifacts/strict-post-close/party-independent.json','data/strict-party-trends.json']
    inputs+=['artifacts/poll-checks/2026-10-23/source-plan.json',
        'artifacts/poll-checks/2026-10-23/ingestion-validation.json',
        'artifacts/poll-checks/2026-10-23/canonical-numeric-runlogs/run-receipt.json']
    hashes={p:sha(ROOT/p) for p in inputs}
    primary,independent,history=[read(ROOT/p) for p in inputs[:3]]
    assert primary['asOf']=='2026-10-23' and primary['historySha256']==hashes['data/poll-history.json']
    j=independent['groups'].index('opposition_raam');row=primary['primary']['overall'][j]
    assert row['group']=='opposition_raam'
    pobs,iobs=row['slopePerWeek'],independent['slopes'][j]
    pc,ic=int(primary['primary']['exactCounting']['extremeCountsExact'][j]),int(independent['countsExact'][j])
    total=int(independent['totalExact'])
    assert type(pobs) is type(iobs) is float and abs(pobs)-1e-12>0 and abs(iobs)-1e-12>0
    assert int(primary['primary']['exactCounting']['nPermutationsExact'])==total
    archive={p['id']:p for p in history['polls']}
    blocks=[];support=[]
    for series in primary['primary']['byPollster']:
        times,weight=series['timeDaysFromFirst'],series['weight']
        seats=next(v['seats'] for v in series['groups'] if v['group']=='opposition_raam')
        assert seats==[sum(archive[k]['seats'].get(p,0) for p in primary['groups']['opposition_raam']) for k in series['pollIds']]
        pb=backend.score_blocks(times,np.asarray(seats)[:,None],weight,method='unique')[0]
        ib=backend.independent_blocks(times,np.asarray(seats)[:,None],weight)[0]
        assert np.array_equal(pb.values,ib[0]) and np.array_equal(pb.multiplicities,ib[1])
        assert sum(int(v) for v in ib[1])==math.factorial(len(times))
        blocks.append([ib]);support.append({'pollsterId':series['pollsterId'],'pollIds':series['pollIds'],
            'timeDays':times,'seats':seats,'weight':weight,'uniqueScores':len(ib[0]),'rawMass':str(pb.raw_permutations),
            'valuesSha256':hashlib.sha256(pb.values.tobytes()).hexdigest(),
            'multiplicitiesSha256':hashlib.sha256(json.dumps([str(int(v)) for v in ib[1]],separators=(',',':')).encode()).hexdigest()})
    assert math.prod(int(row['rawMass']) for row in support)==total
    left,right,nl,nr=[],[],1,1
    for index in sorted(range(len(blocks)),key=lambda i:len(blocks[i][0][0]),reverse=True):
        if nl<=nr:left.append(index);nl*=len(blocks[index][0][0])
        else:right.append(index);nr*=len(blocks[index][0][0])
    half_masses=[math.prod(int(support[i]['rawMass']) for i in side) for side in [left,right]]
    assert math.prod(half_masses)==total
    frozen=ROOT/'artifacts/strict-post-close/independent-compressed-counts.py'
    assert sha(frozen)=='8a725d5bfca3a0f40a8f6e72f038e76877ec88e0d444b8fbf07686da3f1b924d'
    spec=importlib.util.spec_from_file_location('_original_independent_counter_21_boundary',frozen)
    counter=importlib.util.module_from_spec(spec);spec.loader.exec_module(counter)
    started=time.monotonic()
    direct_common,common_total,sizes=counter.direct_tail_counts(blocks,[pobs],tolerance=1e-12)
    dc=int(direct_common[0]);assert common_total==total
    print(json.dumps({'phase':'direct_at_primary','countExact':str(dc),'matchesPrimary':dc==pc,'seconds':time.monotonic()-started}),flush=True)
    direct_own,own_total,own_sizes=counter.direct_tail_counts(blocks,[iobs],tolerance=1e-12)
    own=int(direct_own[0]);assert own_total==total and own==ic
    print(json.dumps({'phase':'direct_at_own','countExact':str(own),'matchesIndependent':own==ic,'seconds':time.monotonic()-started}),flush=True)
    source=frozen.read_text(encoding='utf-8-sig')
    substitutions=[
        ('a_value + float(b[high_index - 1]) >= cutoff','float(b[high_index - 1]) >= cutoff - a_value'),
        ('a_value + float(b[low_index - 1]) > -cutoff','float(b[low_index - 1]) > -cutoff - a_value'),
    ]
    for before,after in substitutions:
        assert source.count(before)==1;source=source.replace(before,after,1)
    diagnostic={};exec(compile(source,str(frozen),'exec'),diagnostic)
    subtraction,sub_total,sub_sizes=diagnostic['direct_tail_counts'](blocks,[pobs],tolerance=1e-12)
    sub=int(subtraction[0]);assert sub_total==total
    print(json.dumps({'phase':'two_pointer_subtraction_at_primary','countExact':str(sub),'matchesPrimary':sub==pc,'seconds':time.monotonic()-started}),flush=True)
    subtraction_own,sub_own_total,sub_own_sizes=diagnostic['direct_tail_counts'](blocks,[iobs],tolerance=1e-12)
    sub_own=int(subtraction_own[0]);assert sub_own_total==total
    assert sizes==own_sizes==sub_sizes==sub_own_sizes==[[nl,nr]]
    assert (dc-sub)+(own-dc)==(sub_own-sub)+(own-sub_own)==ic-pc
    print(json.dumps({'phase':'two_pointer_subtraction_at_own','countExact':str(sub_own),'seconds':time.monotonic()-started}),flush=True)
    result={'status':'PASS' if sub==pc and own==ic else 'INVESTIGATE','asOf':'2026-10-23','outcome':'opposition_raam',
        'scope':'Focused diagnosis only; all original numeric results and counters preserved',
        'inputHashes':hashes,'primaryObservedHex':pobs.hex(),'independentObservedHex':iobs.hex(),
        'toleranceUnchanged':1e-12,'primaryCutoffHex':(abs(pobs)-1e-12).hex(),'independentCutoffHex':(abs(iobs)-1e-12).hex(),
        'primaryExtremeCountExact':str(pc),'independentExtremeCountExact':str(ic),'totalExact':str(total),
        'directAtPrimaryObservedCountExact':str(dc),'directAtOwnObservedCountExact':str(own),
        'twoPointerSubtractionAtPrimaryCountExact':str(sub),
        'twoPointerSubtractionAtOwnCountExact':str(sub_own),
        'commonSubtractionPredicateIntegerMatch':sub==pc,'originalDirectOwnThresholdIntegerMatch':own==ic,
        'directSumAndSubtractionPredicateDifferenceExact':str(dc-pc),'observedStatisticContributionExact':str(ic-dc),
        'signedCountDecomposition':{'predicateAtPrimary':str(dc-sub),'directObservedShift':str(own-dc),
            'subtractionObservedShift':str(sub_own-sub),'predicateAtIndependent':str(own-sub_own),'totalDifference':str(ic-pc)},
        'decompositionIsSignedNetCountDifferenceNotPairEnumeration':True,
        'unchangedReportedValues':{'primaryP':row['pValue'],'primaryQ':row['qValue'],'independentP':independent['p'][j]},
        'probabilityDifferenceExactFraction':str(Fraction(ic-pc,total)),'probabilityDifference':(ic-pc)/total,
        'allScalarSupportsAndLabeledMassesEqual':True,'support':support,'halfSizes':sizes,'subtractionHalfSizes':sub_sizes,
        'halfSeries':[[support[i]['pollsterId'] for i in side] for side in [left,right]],'rawHalfMasses':[str(v) for v in half_masses],
        'diagnosticOnlySubstitutions':substitutions,'diagnosticSourceSha256':hashlib.sha256(source.encode()).hexdigest(),
        'reproducerSha256':sha(Path(__file__)),'elapsedSeconds':round(time.monotonic()-started,3),
        'outputsOrFrozenHelpersModified':False,
        'explanation':'Counts are reproduced independently under each original binary floating comparison. The difference decomposes into cutoff changes from separately computed observed slopes plus sum-versus-subtraction rounding at the discrete boundary. No reported probability, tolerance, source data or primary/independent algorithm is changed.'}
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    ART.mkdir(parents=True,exist_ok=True);out=ART/'opposition-raam-predicate-diagnosis.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert result['status']=='PASS','Focused predicate diagnosis did not establish equivalence'


if __name__=='__main__':main()
