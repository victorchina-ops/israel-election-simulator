"""Validate actual21Oct cohorts, exact audits and the strict party snapshot.

Counts, new-observation dates and eligibility come from the reviewed source plan
and immutable baseline. Existing OLS/BH/sign-flip checks are reused unchanged.
Only an actual exact-integer disagreement invokes a compact common-threshold
diagnosis with the unchanged independent counter; no tolerance is widened.
"""
from pathlib import Path
from datetime import date
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-21'
ART = ROOT / 'artifacts/poll-checks' / DAY
BEFORE = ART / 'before'
STRICT = ROOT / 'artifacts/strict-post-close'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def imported(name, relative, digest):
    path = ROOT / relative
    assert sha(path) == digest, ('Pinned implementation changed', relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def boundary_check(kind, identity, series, values_key, id_key, primary_observed,
                   own_observed, primary_count, own_count, total, hashes, scalar,
                   counter, allow_compute):
    target = ART / 'numeric-boundaries' / (kind + '-' + identity + '.json')
    identity_record = {'kind':kind,'identity':identity,'primaryObservedHex':float(primary_observed).hex(),
        'independentObservedHex':float(own_observed).hex(),'primaryExtremeCountExact':str(primary_count),
        'independentExtremeCountExact':str(own_count),'totalExact':str(total),'inputHashes':hashes}
    if target.exists():
        receipt = read(target)
        assert all(receipt[k] == v for k,v in identity_record.items())
        assert receipt['status'] == 'PASS' and receipt['toleranceUnchanged'] == 1e-12
        assert receipt['commonThresholdExactIntegerMatch'] and receipt['ownThresholdExactIntegerMatch']
        return target
    assert allow_compute, ('Exact counts disagree; run --resolve-boundaries for only this outcome', kind, identity)
    blocks, support = [], []
    for item in series:
        values = next(row['seats'] for row in item[values_key] if row[id_key] == identity)
        times, weight = item['timeDaysFromFirst'], item['weight']
        primary = scalar.score_blocks(times, np.asarray(values)[:,None], weight, method='unique')[0]
        independent = scalar.independent_blocks(times, np.asarray(values)[:,None], weight)[0]
        assert np.array_equal(primary.values, independent[0])
        assert np.array_equal(primary.multiplicities, independent[1])
        assert sum(int(v) for v in independent[1]) == math.factorial(len(times))
        blocks.append([independent])
        support.append({'pollsterId':item['pollsterId'],'pollIds':item['pollIds'],
            'timeDays':times,'seats':values,'weight':weight,
            'valuesSha256':hashlib.sha256(primary.values.tobytes()).hexdigest(),
            'multiplicitiesSha256':hashlib.sha256(json.dumps([str(int(v)) for v in independent[1]],separators=(',',':')).encode()).hexdigest(),
            'uniqueScores':len(primary.values),'rawMass':str(primary.raw_permutations)})
    print(json.dumps({'status':'BOUNDARY_START','kind':kind,'identity':identity}), flush=True)
    common, common_total, common_sizes = counter.direct_tail_counts(blocks, [primary_observed], tolerance=1e-12)
    own, own_total, own_sizes = counter.direct_tail_counts(blocks, [own_observed], tolerance=1e-12)
    assert common_total == own_total == total
    assert int(common[0]) == primary_count, ('Common-threshold integer discrepancy requires investigation',kind,identity)
    assert int(own[0]) == own_count, ('Own-threshold integer reproduction failed',kind,identity)
    receipt = {**identity_record,'status':'PASS','asOf':DAY,'toleranceUnchanged':1e-12,
        'commonThresholdExactIntegerMatch':True,'ownThresholdExactIntegerMatch':True,
        'allScalarSupportsAndLabeledMassesEqual':True,'commonThresholdCountExact':str(int(common[0])),
        'ownThresholdCountExact':str(int(own[0])),'support':support,
        'commonHalfSizes':common_sizes,'ownHalfSizes':own_sizes,
        'probabilityDifference':(own_count-primary_count)/total,
        'outputsOrFrozenHelpersModified':False,
        'explanation':'Separately computed observed slopes select different fixed1e-12 cutoffs in a discrete null; both exact integer results are retained, and the independent counter matches the primary at the common primary statistic.'}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resolve-boundaries', action='store_true')
    args = parser.parse_args()
    manifest = read(BEFORE / 'manifest.json')
    helper_rel = 'scripts/validate-poll-update-2026-10-20-evening.py'
    helper = imported('_reviewed_numeric_checks_20', helper_rel, manifest['files'][helper_rel])
    backend_rel = 'scripts/exact_scalar_marginals_2026_10_20.py'
    assert sha(ROOT / backend_rel) == manifest['files'][backend_rel]
    import exact_scalar_marginals_2026_10_20 as scalar
    scalar.verify_frozen_counters()
    counter_rel = 'artifacts/strict-post-close/independent-compressed-counts.py'
    counter = imported('_unchanged_independent_counter_21', counter_rel, manifest['reviewedExactHelpers'][counter_rel])
    close, index, bh, sign_flip, midpoint = helper.close, helper.index, helper.bh, helper.sign_flip, helper.midpoint
    paths = ['data/current-polls.json','data/poll-history.json','data/strict-party-trends.json',
        'data/calibration.json','data/parties.json','artifacts/strict-post-close/analysis.json',
        'artifacts/strict-post-close/party-analysis.json','artifacts/strict-post-close/independent-strict-numeric-audit.json',
        'artifacts/strict-post-close/party-independent.json','artifacts/poll-checks/2026-10-21/source-plan.json',
        'artifacts/poll-checks/2026-10-21/ingestion-validation.json',
        *['artifacts/strict-post-close/'+name for name in ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']]]
    hashes = {p:sha(ROOT / p) for p in paths}
    current, history, snapshot, calibration, parties, bloc, party, bi, pi, plan, ingestion = [read(ROOT / p) for p in paths[:11]]
    assert all(doc['asOf'] == DAY for doc in [current,history,snapshot,bloc,party,plan,ingestion])
    assert ingestion['status'] == 'PASS'
    assert len(current['polls']) == len({p['pollsterId'] for p in current['polls']}) == manifest['activePollCount']
    before_history = read(BEFORE / 'data/poll-history.json')
    before_bloc = read(BEFORE / 'artifacts/strict-post-close/analysis.json')
    before_snapshot = read(BEFORE / 'data/strict-party-trends.json')
    for rel in ['data/calibration.json','data/parties.json']:
        assert hashes[rel] == manifest['files'][rel], ('Historical weights/catalogue changed',rel)
    specs = index(plan['polls'], 'pollsterId')
    new_ids = {'history_'+read(ROOT / s['candidatePath'])['id']+'_current' for s in specs.values()}
    eligible_ids = {'history_'+read(ROOT / s['candidatePath'])['id']+'_current' for s in specs.values() if s['strictEligible']}
    assert len(history['polls']) == len(before_history['polls']) + len(specs)
    archive = index(history['polls'], 'id')
    cohort, old_cohort = index(bloc['cohort'],'pollId'), index(before_bloc['cohort'],'pollId')
    assert bloc['cohort'] == party['cohort']
    assert set(cohort) == set(old_cohort) | new_ids and not set(old_cohort) & new_ids
    assert all(cohort[k] == row for k,row in old_cohort.items()), 'Earlier fieldwork decisions changed'
    assert {k for k,row in cohort.items() if row['eligibleStrict']} == {k for k,row in old_cohort.items() if row['eligibleStrict']} | eligible_ids
    candidate_hashes, source_hashes, source_checks = {}, {}, {}
    added_active, removed_active = [], []
    before_active = index(read(BEFORE / 'data/current-polls.json')['polls'],'pollsterId')
    for pid,spec in specs.items():
        candidate_path = ROOT / spec['candidatePath']
        assert sha(candidate_path) == spec['candidateSha256']
        candidate_hashes[spec['candidatePath']] = sha(candidate_path)
        poll = read(candidate_path)
        row = cohort['history_'+poll['id']+'_current']
        assert row['publicationDate'] == poll['date']
        assert row['fieldworkStart'] == poll.get('fieldworkStart') and row['fieldworkEnd'] == poll.get('fieldworkEnd')
        assert row['eligibleStrict'] is spec['strictEligible']
        if spec['strictEligible']:
            assert poll.get('fieldworkVerified') is True
            assert bloc['closure']['firstEligibleFieldworkDate'] <= row['fieldworkStart'] <= row['fieldworkEnd'] <= row['publicationDate']
        for item in spec.get('fieldworkEvidence',[]):
            assert sha(ROOT / item['file']) == item['sha256']
            source_hashes[item['file']] = item['sha256']
        added_active.append(poll['id'])
        removed_active.append(before_active[pid]['id'])
        source_checks[pid] = {'publicationDate':poll['date'],'fieldworkStart':row['fieldworkStart'],
            'fieldworkEnd':row['fieldworkEnd'],'strictEligible':row['eligibleStrict'],'sampleSize':poll.get('sampleSize')}
    eligible = [row for row in cohort.values() if row['eligibleStrict']]
    excluded = [row for row in cohort.values() if not row['eligibleStrict']]
    n_series, n_parties, n_groups = len(bloc['primary']['byPollster']), len(party['testedPartyIds']), len(bloc['groups'])
    n_polls, n_deltas = len(eligible), len(eligible)-n_series
    assert n_polls == manifest['strictEligibleCount'] + len(eligible_ids)
    assert n_parties == len([row for row in parties if row['ballot']]) == before_snapshot['coverage']['partyCount']
    assert party['testedPartyIds'] == [row['id'] for row in parties if row['ballot']]
    assert bloc['normalizedHistoricalWeights'] == party['normalizedHistoricalWeights'] == before_bloc['normalizedHistoricalWeights']
    close(sum(bloc['normalizedHistoricalWeights'].values()),1,'weights')
    assert bloc['historySha256'] == party['historySha256'] == pi['historySha256'] == hashes['data/poll-history.json']
    assert party['baseAnalysisSha256'] == pi['cohortSha256'] == hashes['artifacts/strict-post-close/analysis.json']
    assert snapshot['provenance']['analysisSha256'] == hashes['artifacts/strict-post-close/party-analysis.json']
    assert snapshot['provenance']['historySha256'] == hashes['data/poll-history.json']
    coverage = snapshot['coverage']
    assert coverage['pollCount'] == n_polls and coverage['seriesCount'] == n_series
    assert coverage['deltaCount'] == n_deltas and coverage['partyCount'] == n_parties and coverage['excludedPollCount'] == len(excluded)
    assert coverage['from'] == min(p['fieldworkStart'] for p in eligible) and coverage['to'] == max(p['fieldworkEnd'] for p in eligible)
    assert snapshot['methodology']['partyTests'] == n_parties
    assert snapshot['methodology']['individualTests'] == n_parties*n_series
    assert snapshot['methodology']['signPatterns'] == 2**n_series
    assert snapshot['weightMode'] == 'quality' and snapshot['methodology']['fixedSnapshot']
    assert not snapshot['methodology']['usesCurrentControls']
    exact = math.prod(math.factorial(len(s['pollIds'])) for s in bloc['primary']['byPollster'])
    assert int(snapshot['methodology']['permutationsExact']) == int(bi['totalExact']) == int(pi['nPermutationsExact']) == exact
    assert bi['cohortPolls'] == pi['nPolls'] == n_polls and bi['cohortPollsters'] == pi['nSeries'] == n_series
    assert pi['nParties'] == n_parties and pi['nIndividualTests'] == n_parties*n_series
    assert [{k:v for k,v in row.items() if k != 'byPollster'} for row in snapshot['rows']] == party['primary']['overall']
    assert {row['pollId'] for row in snapshot['cohort']} == set(cohort)
    for row in snapshot['cohort']:
        original = cohort[row['pollId']]
        for key in ['pollsterId','publicationDate','fieldworkStart','fieldworkEnd','eligibleStrict']:
            assert row[key] == original[key]
        if original.get('sourceUrl','').startswith(('http://','https://')):
            assert original['sourceUrl'] in row['sourceUrls']
    labels = {row['pollsterId']:row['label'] for row in snapshot['weights']}
    for row in snapshot['rows']:
        expected = []
        for series in party['primary']['byPollster']:
            value = next(v for v in series['parties'] if v['partyId'] == row['partyId'])
            expected.append({**value,'label':labels[series['pollsterId']], 'pollIds':series['pollIds'],
                'dates':series['publicationDates'],'timeDaysFromFirst':series['timeDaysFromFirst']})
        assert row['byPollster'] == expected
    dp_checks = 0
    for doc, values_key, id_key, pkey, qkey in [(bloc,'groups','group','wholeInstituteSignFlipP','wholeInstituteSignFlipQ'),
            (party,'parties','partyId','wholeSeriesSignFlipP','wholeSeriesSignFlipQ')]:
        for axis in ['primary','publicationDateSensitivity']:
            result = doc[axis]
            assert result['nPolls'] == n_polls and result['nDeltas'] == n_deltas
            assert len(result['overall']) == (n_groups if doc is bloc else n_parties)
            assert len(result['byPollster']) == n_series
            assert int(result['exactCounting']['nPermutationsExact']) == exact
            assert len(result['exactCounting']['extremeCountsExact']) == len(result['exactCounting']['pValues']) == len(result['overall'])
            for row,number,count in zip(result['overall'],result['exactCounting']['pValues'],result['exactCounting']['extremeCountsExact']):
                close(number,int(count)/exact,('exact p',axis))
                close(row['pValue'],number,('reported p',axis))
            for series in result['byPollster']:
                pid = series['pollsterId']
                assert series['weight'] == bloc['normalizedHistoricalWeights'][pid]
                assert all(cohort[k]['eligibleStrict'] for k in series['pollIds'])
                times = [midpoint(cohort[k]) if axis == 'primary' else date.fromisoformat(cohort[k]['publicationDate']).toordinal() for k in series['pollIds']]
                relative = [t-times[0] for t in times]
                assert series['timeDaysFromFirst'] == relative
                assert series.get('publicationDates',series.get('dates')) == [cohort[k]['publicationDate'] for k in series['pollIds']]
                centered = [t-sum(relative)/len(relative) for t in relative]
                denominator = sum(t*t for t in centered)
                assert denominator > 0
                for value in series[values_key]:
                    identity = value[id_key]
                    seats = [sum(archive[k]['seats'].get(p,0) for p in bloc['groups'][identity]) if doc is bloc else archive[k]['seats'].get(identity,0) for k in series['pollIds']]
                    assert value['seats'] == seats
                    slope = sum(7*t/denominator*y for t,y in zip(centered,seats))
                    close(value['slopePerWeek'],slope,('raw OLS',axis,pid,identity))
                    assert value['netDelta'] == seats[-1]-seats[0]
                    block = scalar.score_blocks(relative,seats,method='dp')
                    p = scalar.individual_pvalues(block,[value['slopePerWeek']],tolerance=1e-12)[0]
                    close(value['pValue'],float(p),('independent DP individual p',axis,pid,identity))
                    dp_checks += 1
            bh(result['overall'],'pValue','qValue')
            bh(result['overall'],pkey,qkey)
            bh([row for s in result['byPollster'] for row in s[values_key]],'pValue','qValue')
            for row in result['overall']:
                weighted_slope = sum(s['weight']*next(v['slopePerWeek'] for v in s[values_key] if v[id_key] == row[id_key]) for s in result['byPollster'])
                close(row['slopePerWeek'],weighted_slope,('weighted OLS',axis,row[id_key]))
                delta = sum(s['weight']*next(v['netDelta'] for v in s[values_key] if v[id_key] == row[id_key]) for s in result['byPollster'])
                close(row['weightedNetDelta'],delta,('weighted delta',axis,row[id_key]))
                sign_flip(row,result['byPollster'],values_key,id_key,pkey)
    boundary_paths = []
    for j,row in enumerate(bloc['primary']['overall']):
        assert row['group'] == bi['groups'][j]
        close(row['slopePerWeek'],bi['slopes'][j],('independent bloc slope',row['group']))
        close(row['pValue'],bi['p'][j],('independent bloc p',row['group']))
        pc,ic = int(bloc['primary']['exactCounting']['extremeCountsExact'][j]),int(bi['countsExact'][j])
        if pc != ic:
            boundary_paths.append(boundary_check('bloc',row['group'],bloc['primary']['byPollster'],'groups','group',
                row['slopePerWeek'],bi['slopes'][j],pc,ic,exact,hashes,scalar,counter,args.resolve_boundaries))
    independent_bloc = index(bi['individual'],'pollsterId')
    for series in bloc['primary']['byPollster']:
        other = independent_bloc[series['pollsterId']]
        for j,row in enumerate(series['groups']):
            close(row['slopePerWeek'],other['slope'][j],('individual bloc slope',series['pollsterId'],j))
            close(row['pValue'],other['p'][j],('individual bloc p',series['pollsterId'],j))
    independent_parties = index(pi['overall'],'partyId')
    for j,row in enumerate(party['primary']['overall']):
        other = independent_parties[row['partyId']]
        for key,alias in [('slopePerWeek','slopePerWeek'),('weightedNetDelta','netDelta'),('pValue','p'),('qValue','q'),('wholeSeriesSignFlipP','signFlipP'),('wholeSeriesSignFlipQ','signFlipQ')]:
            close(row[key],other[alias],('independent party',row['partyId'],key))
        pc,ic = int(party['primary']['exactCounting']['extremeCountsExact'][j]),int(other['extremeCountExact'])
        if pc != ic:
            boundary_paths.append(boundary_check('party',row['partyId'],party['primary']['byPollster'],'parties','partyId',
                row['slopePerWeek'],other['slopePerWeek'],pc,ic,exact,hashes,scalar,counter,args.resolve_boundaries))
    individual = {(row['pollsterId'],row['partyId']):row for row in pi['byPollster']}
    assert len(individual) == n_parties*n_series
    for series in party['primary']['byPollster']:
        for row in series['parties']:
            other = individual[(series['pollsterId'],row['partyId'])]
            assert row['seats'] == other['series']
            for key,alias in [('slopePerWeek','slopePerWeek'),('netDelta','delta'),('pValue','p'),('qValue','q')]:
                close(row[key],other[alias],('independent individual party',series['pollsterId'],row['partyId'],key))
    preserved = {rel:digest for rel,digest in manifest['files'].items() if rel.startswith('scripts/')}
    for rel,digest in preserved.items():
        assert sha(ROOT / rel) == digest, ('Prior script changed',rel)
    for group in ['authorContentHashes','protectedRuntimeHashes','reviewedExactHelpers']:
        for rel,digest in manifest[group].items():
            assert sha(ROOT / rel) == digest, ('Protected/frozen input changed',rel)
    lineage_hashes = {}
    for stage in ['bloc','party','independent-bloc','independent-party']:
        path = ART / 'numeric-lineage' / (stage+'-enumeration-lineage.json')
        lineage = read(path)
        assert lineage['status'] == 'PASS' and lineage['asOf'] == DAY
        assert lineage['inputHistorySha256'] == hashes['data/poll-history.json']
        assert sha(STRICT / lineage['outputFile']) == lineage['outputSha256']
        assert sha(ROOT / lineage['reviewedAdapter']) == lineage['reviewedAdapterSha256']
        assert lineage['wrapperSha256'] == manifest['files']['scripts/run-exact-trends-2026-10-21.py']
        assert lineage['scalarBackendSha256'] == manifest['files'][backend_rel]
        for name,digest in lineage['inputAuditHashes'].items():
            assert digest == sha(STRICT / name)
        assert lineage['nullUnchanged'] and lineage['outcomeMarginalExactness'] and not lineage['monteCarlo']
        lineage_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / p) == h for p,h in hashes.items())
    result = {'passed':True,'status':'PASS','asOf':DAY,'runId':'reviewed','newPollCount':len(specs),
        'activePolls':len(current['polls']),'historyPolls':len(history['polls']),'candidatePolls':len(cohort),
        'polls':n_polls,'series':n_series,'deltas':n_deltas,'parties':n_parties,
        'individualTests':n_parties*n_series,'individualBlocTests':n_groups*n_series,'exactPermutations':str(exact),
        'excludedPollCount':len(excluded),'addedActivePollIds':sorted(added_active),'removedActivePollIds':sorted(removed_active),
        'addedHistoryPollIds':sorted(new_ids),'newStrictEligiblePollIds':sorted(eligible_ids),
        'newStrictExcludedPollIds':sorted(new_ids-eligible_ids),'newStrictEligiblePollCount':len(eligible_ids),
        'newPollsIncludedInForecast':True,'newPollsIncludedInStrictTrends':new_ids == eligible_ids,
        'allPriorStrictCohortRowsUnchanged':True,'historicalWeightsAndCatalogueUnchanged':True,
        'memorySafeExactEnumerationWithIndependentDP':True,'reviewedExactHelpersUnchanged':True,
        'rawInputOLSAndBHAndSignFlipsVerified':True,'individualExactDPChecks':dp_checks,
        'sourceChecks':source_checks,'inputHashes':hashes,'candidateHashes':candidate_hashes,'sourceEvidenceHashes':source_hashes,
        'preservedCodeHashes':preserved,'numericLineageHashes':lineage_hashes,
        'boundaryReviewHashes':{p.relative_to(ROOT).as_posix():sha(p) for p in boundary_paths},
        'exactArithmeticRepairInputHashes':{backend_rel:sha(ROOT / backend_rel),helper_rel:sha(ROOT / helper_rel),counter_rel:sha(ROOT / counter_rel)},
        'checkpointManifestSha256':sha(BEFORE / 'manifest.json'),'validatorSha256':sha(Path(__file__))}
    helper.immutable_write(ART / 'strict-validation.json',result)
    helper.immutable_write(STRICT / 'party-validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if not k.endswith('Hashes')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
