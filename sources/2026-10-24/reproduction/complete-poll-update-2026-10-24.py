"""Record completion after public bytes, browser/visual QA and all review receipts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[1];DAY='2026-10-24';ART=ROOT/'artifacts/poll-checks'/DAY;REPO=ROOT/'github-pages'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    release=read(ART/'publication-receipt.json');public=read(ART/'public-readback.json');plan=read(ART/'source-plan.json')
    assert release['status']==public['status']=='PASS' and release['asOf']==public['asOf']==plan['asOf']==DAY
    commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    assert public['commit']==commit and not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain']).strip()
    spec=importlib.util.spec_from_file_location('_release_checks_23',ROOT/'scripts/package-poll-update-2026-10-24.py')
    package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
    browser,visual=package.browser_receipts('public',release['publishedHtmlSha256'],release['snapshotSha256'],release['sourcePlanSha256'])
    for name in ['ingestion-validation.json','strict-validation.json','model-comparison-validation.json','model-comparisons-independent-review.json','staged-review.json','social/render-checks.json','social/independent-review.json']:
        assert read(ART/name)['status']=='PASS'
    assert sha(ROOT/'dashboard/src/data.json')==release['snapshotSha256']==public['snapshotSha256']
    assert sha(REPO/'index.html')==release['publishedHtmlSha256']==public['htmlSha256']
    manifest=read(ART/'before/manifest.json')
    for group in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']:
        for rel,digest in manifest[group].items():assert sha(ROOT/rel)==digest
    current=read(ROOT/'data/current-polls.json');history=read(ROOT/'data/poll-history.json');strict=read(ROOT/'data/strict-party-trends-without-channel14.json')
    assert strict['asOf']==DAY and strict['coverage']['pollCount']==release['eligibleWithout14']
    assert release['historyPolls']==len(history['polls'])==manifest['historyPollCount']+len(plan['polls'])
    assert release['activePolls']==len(current['polls'])==manifest['activePollCount']
    assert set(public['newObservationIds'])=={read(ROOT/s['candidatePath'])['id'] for s in plan['polls']}
    def scenario(stem):
        report=read(ART/(stem+'.json'))
        return {'comparisonFile':stem+'.json','comparisonSha256':sha(ART/(stem+'.json')),
            'configuration':report['after']['config'],'asOf':report['after']['asOf'],'previousAsOf':report['before']['asOf'],
            'modelMeanSeats':{g['id']:g['stats']['mean'] for g in report['after']['reportingGroups']},
            'previousModelMeanSeats':{g['id']:g['stats']['mean'] for g in report['before']['reportingGroups']},
            'thresholdPassPct':{p['id']:100*p['passProbability'] for p in report['after']['parties'] if p['id'] in {'winter','hendel'}},
            'previousThresholdPassPct':{p['id']:100*p['passProbability'] for p in report['before']['parties'] if p['id'] in {'winter','hendel'}},
            'probabilities':report['after']['probabilities']}
    default=scenario('model-comparison');preferred=scenario('model-comparison-similarity')
    assert default['configuration']['pollCorrelationEnabled'] is False and preferred['configuration']['pollCorrelationEnabled'] is True
    render=read(ART/'social/render-checks.json')
    result={'status':'PASS','asOf':DAY,'runId':'reviewed','commit':commit,'url':public['url'],
        'publicationDates':release['observationPublicationDates'],'observationDateKinds':release['observationDateKinds'],
        'newObservationIds':public['newObservationIds'],'activePolls':len(current['polls']),'historyPolls':len(history['polls']),
        'snapshotSha256':release['snapshotSha256'],'publishedHtmlSha256':release['publishedHtmlSha256'],
        'publicFilesVerified':public['filesVerified'],'testsPassed':release['testsPassed'],
        'defaultConfiguration':{'weightMode':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,'turnout':'2022','winter':'coalition','hendel':'unassigned'},
        'modelMeanSeats':default['modelMeanSeats'],'thresholdPassPct':default['thresholdPassPct'],
        'defaultScenario':default,'preferredSimilarityScenario':preferred,'defaultStrictCoverage':strict['coverage'],
        'defaultSignificantPartyTrends':[{'partyId':r['partyId'],'netChange':r['weightedNetDelta'],'p':r['pValue'],'q':r['qValue'],'sensitivityP':r['wholeSeriesSignFlipP'],'sensitivityQ':r['wholeSeriesSignFlipQ']} for r in strict['rows'] if r['qValue']<.05],
        'sourceAccessLimitations':list(dict.fromkeys([*read(ART/'primary-source-public-summary.json').get('accessLimitations',[]),
            *read(ART/'primary-source-public-summary.json').get('coverage',{}).get('limitations',[])])),
        'repostsDeduplicated':True,'missingValuesNotZero':True,'originalDataAndHistoricalWeightsPreserved':True,
        'social':{'tweet':'outputs/social/'+DAY+'/tweet.he.txt','png':'outputs/social/'+DAY+'/'+render['output'],
            'prompt':'outputs/social/'+DAY+'/'+render['prompt'],'automaticTweetPosted':False,
            'socialEvidenceKind':render['socialEvidenceKind'],'sourcePollIds':render['sourcePollIds']},
        'receipts':{'release':sha(ART/'publication-receipt.json'),'publicReadback':sha(ART/'public-readback.json'),
            'publicBrowserReport':sha(browser),'publicVisualReview':sha(visual),'socialRenderChecks':sha(ART/'social/render-checks.json'),
            'socialIndependentReview':sha(ART/'social/independent-review.json'),'independentComparisonsReview':sha(ART/'model-comparisons-independent-review.json')}}
    out=ART/'completed.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','commit':commit,'filesVerified':public['filesVerified'],'preferredScenario':preferred},ensure_ascii=False))


if __name__=='__main__':main()
