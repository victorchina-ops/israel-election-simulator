"""Independent arithmetic and provenance review of both20Oct comparison reports.

Does not import the simulation or change any input. Recomputes historical-policy
normalization, active-submatrix density discounts, information inflation,
histogram means and threshold marginals from the frozen replay evidence. Six
retained illustrative worlds per replay are independently checked; the complete
10000-world invariant is also bound to the unchanged reviewed trial-loop flag.
"""
from pathlib import Path
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-20'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def close(a,b,label):
    assert math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12),(label,a,b)


def snapshot_input(doc):
    return {r['key']:r['value'] for r in doc['queries']['model_input']['rows']}


def summary(result):
    return {'meanSeats':{g['id']:g['stats']['mean'] for g in result['reportingGroups']},
        'thresholdPassPct':{p['id']:100*p['passProbability'] for p in result['parties'] if p['id'] in {'winter','hendel'}},
        'probabilities':result['probabilities'],'nEffective':result['nEffective']}


def main():
    plan=read(ART/'source-plan.json')
    validation=read(ART/'model-comparison-validation.json')
    checkpoint=read(ART/'before/manifest.json')
    assert plan['status']=='reviewed' and plan['asOf']=='2026-10-20' and validation['status']=='PASS'
    assert validation['sourcePlanSha256']==sha(ART/'source-plan.json')
    assert validation['snapshotSha256']==sha(ROOT/'dashboard/src/data.json')
    assert validation['comparisonSha256']==sha(ART/'model-comparison.json')
    before_input=snapshot_input(read(ART/'before/dashboard/src/data.json'))
    after_input=snapshot_input(read(ROOT/'dashboard/src/data.json'))
    inputs={'before':before_input,'after':after_input}
    raw_calibration=read(ROOT/'data/calibration.json')
    assert sha(ROOT/'data/calibration.json')==checkpoint['files']['data/calibration.json']
    candidates={spec['pollsterId']:read(ROOT/spec['candidatePath']) for spec in plan['polls']}
    assert set(candidates)=={'midgam_geva','hamadad_consortium','next_data','lazar'}
    for spec in plan['polls']:
        assert sha(ROOT/spec['candidatePath'])==spec['candidateSha256']
    reports={}
    artifacts={}
    result_checks=[]
    for stem,enabled in [('model-comparison',False),('model-comparison-similarity',True)]:
        report=read(ART/(stem+'.json'))
        assert report['status']=='passed' and report['onlyControlDateDiffers'] is True
        assert {p['pollsterId'] for p in report['pollChanges'] if p['changed']}==set(candidates)
        assert report['oppositionMode']=='none'
        assert {d['key'] for d in report['controlDifferences']}=={'asOf'}
        for file,digest in report['authoredModelHashes'].items():
            assert sha(ROOT/file)==checkpoint['authorContentHashes'][file]==digest,file
        reports[stem]=report
        artifacts[stem]={'sha256':sha(ART/(stem+'.json')),'phases':{}}
        for phase in ['before','after']:
            replay_path=ART/(stem+'.'+phase+'-replay.json')
            replay=read(replay_path)
            source=replay['input'];cfg=replay['config'];result=replay['result']
            assert source==inputs[phase]
            assert result['config']==cfg==report[phase]['config']
            assert cfg['asOf']==source['current']['asOf']==('2026-10-19' if phase=='before' else '2026-10-20')
            assert cfg['weightMode']=='quality' and cfg['pollCorrelationEnabled'] is enabled
            assert cfg['includeChannel14'] is cfg['signalNoiseEnabled'] is False
            assert cfg['partyBlocs']['winter']=='a' and cfg['partyBlocs']['hendel']=='other'
            assert cfg['iterations']==result['iterations']==10000 and cfg['seed']==20260912
            assert cfg['applyRecency'] is False and not cfg['pollWeights'] and not cfg['excludedPolls']
            calibration={k:v for k,v in source['calibration'].items() if k!='pollCorrelation'}
            assert calibration==raw_calibration
            profile_path=ART/'before/data/poll-correlation.json' if phase=='before' else ROOT/'data/poll-correlation.json'
            profile=source['calibration']['pollCorrelation']
            assert profile==read(profile_path) and profile['asOf']==cfg['asOf']
            active=[p for p in source['current']['polls'] if p['pollsterId']!='next_data']
            assert len(active)==7 and len(source['current']['polls'])==8
            ids=[p['pollsterId'] for p in active]
            assert len(set(ids))==7 and 'next_data' not in ids
            if phase=='after':
                assert len(source['history']['polls'])==132
                for pid,candidate in candidates.items():
                    poll=next(p for p in source['current']['polls'] if p['pollsterId']==pid)
                    for key in ['id','date','sampleSize','seats','reportedPercentages','fieldworkStart','fieldworkEnd','fieldworkVerified']:
                        assert poll[key]==candidate[key],(pid,key)
                    assert poll.get('publishedBounds',{})==candidate.get('publishedBounds',{})
                    assert poll['date']==('2026-10-20' if pid=='lazar' else '2026-10-19')
            else:
                assert len(source['history']['polls'])==128
            weights=result['pollWeights']
            assert len(weights)==7 and [p['pollsterId'] for p in weights]==ids
            raw=[calibration.get('pollsterQuality',{}).get(pid,{}).get('weight',1) for pid in ids]
            base=[v/sum(raw) for v in raw]
            assert result['methodWeights']=={'quality':1}
            assert len(result['weightContributions'])==1 and result['weightContributions'][0]['method']=='quality'
            for a,b in zip(result['weightContributions'][0]['weights'],base):close(a,b,'Unchanged historical base vector')
            expected=base[:]
            density={}
            matrix=profile['modeledCorrelationMatrix']
            indexes={pid:i for i,pid in enumerate(profile['instituteIds'])}
            assert all(pid in indexes for pid in ids)
            if enabled:
                density={pid:sum(matrix[indexes[pid]][indexes[other]] for other in ids) for pid in ids}
                discounted=[base[i]/density[pid] for i,pid in enumerate(ids)]
                expected=[v/sum(discounted) for v in discounted]
                metadata=result['pollCorrelation']
                assert metadata['historicalAccuracyApplied']=='unchanged_selected_base_policy'
                assert metadata['weightCorrectionApplied']=='once_after_policy_aggregation_before_manual'
                assert set(metadata['eligibleInstitutes'])==set(ids)
                assert 'next_data' not in metadata['eligibleInstitutes']
                assert metadata['coverage']==profile['coverage']
                for pid in ids:
                    close(metadata['redundancyDensity'][pid],density[pid],'Active7 submatrix density')
                    close(metadata['redundancyDiscounts'][pid],1/density[pid],'One density discount')
            else:
                assert 'pollCorrelation' not in result
            for row,value in zip(weights,expected):close(row['weight'],value,'Final independently recomputed weight')
            close(sum(p['weight'] for p in weights),1,'Normalized weights')
            # Recompute the independent/global-DEFF sample policy and active-only
            # off-diagonal information correction directly from the matrix.
            denominators=[max(100,p.get('sampleSize') or 500)/cfg['designEffect'] for p in active]
            independent=sum(expected[i]**2/denominators[i] for i in range(7))
            modeled=independent
            if enabled:
                modeled+=sum(2*expected[i]*expected[j]*matrix[indexes[ids[i]]][indexes[ids[j]]]/math.sqrt(denominators[i]*denominators[j]) for i in range(7) for j in range(i+1,7))
                info=result['pollCorrelation']['informationCorrection']
                close(info['independentVarianceScale'],independent,'Independent variance scale')
                close(info['modeledVarianceScale'],modeled,'Active-submatrix covariance scale')
                close(info['factor'],modeled/independent,'Information inflation factor')
            close(result['nEffective'],1/modeled,'Effective sample information')
            assert result['checks']['eachWorld120'] is result['checks']['blocPartition120'] is True
            close(result['checks']['seatsSum'],120,'Full-run aggregate seats')
            assert len(result['worlds'])==6
            parties=result['parties'];party_ids=[p['id'] for p in parties]
            assert len(set(party_ids))==len(party_ids)
            for world in result['worlds']:
                assert sum(world['seats'])==120 and len(world['seats'])==len(parties)
                for bloc in ['a','b','other']:
                    assert world['blocs'][bloc]==sum(world['seats'][j] for j,pid in enumerate(party_ids) if cfg['partyBlocs'][pid]==bloc)
                assert world['blocs']['arab']==0 and sum(world['blocs'].values())==120
            for p in parties:
                assert sum(p['hist'])==10000
                close(sum(i*n for i,n in enumerate(p['hist']))/10000,p['mean'],'Party histogram mean')
            group_ids=[]
            for group in result['reportingGroups']:
                assert sum(group['hist'])==10000
                close(sum(i*n for i,n in enumerate(group['hist']))/10000,group['stats']['mean'],'Reporting group histogram mean')
                group_ids.extend(group['partyIds'])
            assert len(set(group_ids))==len(group_ids) and set(group_ids)=={p['id'] for p in parties if p['ballot'] is not False}
            for p in parties:
                if p['ballot'] is False:
                    assert p['mean']==0 and p['hist'][0]==10000, 'Synthetic non-ballot Other must never receive seats.'
            close(sum(g['stats']['mean'] for g in result['reportingGroups']),120,'Disjoint reporting partition')
            threshold=result['thresholdJoint']
            assert threshold['total']==sum(row['count'] for row in threshold['patterns'])==10000
            for j,pid in enumerate(threshold['partyIds']):
                failures=sum(row['count'] for row in threshold['patterns'] if row['failed'][j]=='1')
                close(next(p['passProbability'] for p in parties if p['id']==pid),1-failures/10000,'Threshold marginal from actual joint outcomes')
            for bloc in ['a','b','arab','other']:
                assert sum(result['blocHist'][bloc])==10000
            a_count=sum(result['blocHist']['a'][61:]);b_count=sum(result['blocHist']['b'][61:])
            close(result['probabilities']['a'],a_count/10000,'Coalition61 probability')
            close(result['probabilities']['b'],b_count/10000,'Opposition61 probability')
            close(result['probabilities']['neither'],1-(a_count+b_count)/10000,'Neither61 probability')
            assert report[phase]['pollWeights']==weights
            for g in report[phase]['reportingGroups']:
                actual=next(x for x in result['reportingGroups'] if x['id']==g['id'])
                assert g=={k:v for k,v in actual.items() if k!='hist'}
            artifacts[stem]['phases'][phase]={'replaySha256':sha(replay_path),'profileSha256':sha(profile_path),
                'profileAsOf':profile['asOf'],'baseQualityWeights':dict(zip(ids,base)),
                'finalWeights':{p['pollsterId']:p['weight'] for p in weights},'activeSubmatrixDensity':density,
                'informationInflationFactor':modeled/independent,**summary(result)}
            result_checks.append({'report':stem,'phase':phase,'retainedWorldsIndependentlyChecked':6,'iterationsFlagged120':10000,'allHistogramAndJointMasses':10000})
    for phase in ['before','after']:
        a=read(ART/f'model-comparison.{phase}-replay.json')['config']
        b=read(ART/f'model-comparison-similarity.{phase}-replay.json')['config']
        assert {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}=={'pollCorrelationEnabled'}
        assert artifacts['model-comparison']['phases'][phase]['baseQualityWeights']==artifacts['model-comparison-similarity']['phases'][phase]['baseQualityWeights']
    receipt={'status':'PASS','asOf':'2026-10-20','sourcePlanSha256':sha(ART/'source-plan.json'),
        'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'unchangedCalibrationSha256':sha(ROOT/'data/calibration.json'),
        'reviewScriptSha256':sha(Path(__file__)),'siteDefaultSimilarityEnabled':False,'preferredReportingSimilarityEnabled':True,
        'all4SourceCandidatesBound':True,'actualActiveInstitutes':7,'channel14ExcludedBeforeMatrixSelection':True,
        'historicalQualityBaseUnchangedAcrossAllFourReplays':True,'oneActiveSubmatrixDiscountIndependentlyRecomputed':True,
        'covarianceInformationCorrectionIndependentlyRecomputed':True,'winterBloc':'coalition','hendelBloc':'unassigned',
        'worldInvariantScope':'The unchanged reviewed trial loop accumulates its invariant over all10000 trials; this independent review checks all retained6 illustrative worlds per replay plus all marginal histogram/joint counts and aggregate120 accounting. Full10000 vectors are not stored or claimed independently inspected.',
        'resultChecks':result_checks,'reports':artifacts,'preferredSimilarityScenario':artifacts['model-comparison-similarity'],
        'interpretation':'All comparisons are conditional model point estimates. No new significance test or proven calibration superiority is asserted.'}
    out=ART/'model-comparisons-independent-review.json'
    body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if out.exists():assert out.read_bytes()==body,'Preserve dated independent review'
    else:out.write_bytes(body)
    print(json.dumps({'status':'PASS','reviewReceiptSha256':sha(out),'preferredAfter':artifacts['model-comparison-similarity']['phases']['after']}))


if __name__=='__main__':main()
