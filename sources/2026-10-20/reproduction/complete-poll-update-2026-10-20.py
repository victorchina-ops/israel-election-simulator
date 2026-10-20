"""Save completion only after exact public readback and public visual QA."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-20'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
release=read(ART/'publication-receipt.json')
public=read(ART/'public-readback.json')
assert release['status']==public['status']=='PASS'
commit=subprocess.check_output(['git','-C',str(ROOT/'github-pages'),'rev-parse','HEAD'],text=True).strip()
assert public['commit']==commit
assert not subprocess.check_output(['git','-C',str(ROOT/'github-pages'),'status','--porcelain']).strip()
reports=sorted((ART/'browser-public').glob('*/report.json'))
if (ART/'browser-public/report.json').exists():
    reports.append(ART/'browser-public/report.json')
assert reports
browser=reports[-1]
browser_report=read(browser)
assert browser_report['status']=='passed' and browser_report['asOf']=='2026-10-20' and browser_report['phase']=='public'
assert browser_report['browserAutomation']=='cua'
assert browser_report['officialSourceSnapshotSha256']==release['snapshotSha256']
assert browser_report['servedHTMLSha256']==release['publishedHtmlSha256']
assert browser_report['sourcePlanSha256']==sha(ART/'source-plan.json')==release['sourcePlanSha256']
assert len(browser_report['checks'])>=6
visual=browser.parent/'visual-review.json'
assert read(visual)['status']=='passed' and read(visual)['browserReportSha256']==sha(browser)
assert read(visual)['visualInspectionCompleted'] is True
assert len(read(visual)['reviewedScreenshots'])>=3
for name,digest in read(visual)['reviewedScreenshots'].items():
    assert Path(name).name==name and sha(visual.parent/name)==digest
manifest=read(ART/'before/manifest.json')
for group in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']:
    for rel,digest in manifest[group].items():
        assert sha(ROOT/rel)==digest,(group,rel)
assert sha(ROOT/'dashboard/src/data.json')==release['snapshotSha256']==public['snapshotSha256']
assert sha(ROOT/'github-pages/index.html')==release['publishedHtmlSha256']==public['htmlSha256']
for name in ['ingestion-validation.json','strict-validation.json','model-comparison-validation.json','model-comparisons-independent-review.json','staged-review.json','social/render-checks.json','social/independent-review.json']:
    assert read(ART/name)['status']=='PASS'
tests=(ART/'test-results-final.txt').read_text(encoding='utf-8-sig')
assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
comparison=read(ART/'model-comparison.json')
after=comparison['after']
groups={g['id']:g['stats']['mean'] for g in after['reportingGroups']}
parties={p['id']:p for p in after['parties']}
preferred=read(ART/'model-comparison-similarity.json')
independent=read(ART/'model-comparisons-independent-review.json')
assert independent['reports']['model-comparison-similarity']['sha256']==sha(ART/'model-comparison-similarity.json')
assert independent['snapshotSha256']==release['snapshotSha256']
assert preferred['status']=='passed' and preferred['after']['config']['pollCorrelationEnabled'] is True
preferred_groups={g['id']:g['stats']['mean'] for g in preferred['after']['reportingGroups']}
preferred_before_groups={g['id']:g['stats']['mean'] for g in preferred['before']['reportingGroups']}
preferred_parties={p['id']:p for p in preferred['after']['parties']}
strict=read(ROOT/'data/strict-party-trends-without-channel14.json')
joint=next(r for r in strict['rows'] if r['partyId']=='joint')
receipt={
    'status':'PASS','asOf':'2026-10-20','publicationDates':release['observationPublicationDates'],'runId':'reviewed',
    'commit':commit,'url':'https://victorchina-ops.github.io/israel-election-simulator/',
    'newObservationIds':public['newObservationIds'],
    'observationDateKinds':release['observationDateKinds'],
    'activePolls':release['activePolls'],'historyPolls':release['historyPolls'],
    'snapshotSha256':release['snapshotSha256'],'publishedHtmlSha256':release['publishedHtmlSha256'],
    'publicFilesVerified':public['filesVerified'],'testsPassed':release['testsPassed'],
    'defaultConfiguration':{'weightMode':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,'turnout':'2022','winter':'coalition','hendel':'unassigned'},
    'modelMeanSeats':groups,'thresholdPassPct':{p:100*parties[p]['passProbability'] for p in ['winter','hendel']},
    'preferredSimilarityScenario':{
        'label':'Preferred reporting scenario; separate from unchanged website defaults',
        'comparisonFile':'model-comparison-similarity.json','comparisonSha256':sha(ART/'model-comparison-similarity.json'),
        'configuration':{'weightMode':'quality','includeChannel14':False,'pollCorrelationEnabled':True,'signalNoiseEnabled':False,'turnout':'2022','winter':'coalition','hendel':'unassigned'},
        'asOf':preferred['after']['asOf'],'previousAsOf':preferred['before']['asOf'],
        'modelMeanSeats':preferred_groups,'previousModelMeanSeats':preferred_before_groups,
        'meanSeatChanges':{key:preferred_groups[key]-preferred_before_groups[key] for key in preferred_groups},
        'thresholdPassPct':{p:100*preferred_parties[p]['passProbability'] for p in ['winter','hendel']},
        'previousThresholdPassPct':{p['id']:100*p['passProbability'] for p in preferred['before']['parties'] if p['id'] in ['winter','hendel']},
        'probabilities':preferred['after']['probabilities'],
        'limitation':'Experimental forecast-similarity heuristic; not measured respondent overlap, error correlation or proven superior calibration.'},
    'defaultStrictCoverage':strict['coverage'],
    'jointTrend':{'netChange':joint['weightedNetDelta'],'p':joint['pValue'],'q':joint['qValue'],'sensitivityP':joint['wholeSeriesSignFlipP'],'sensitivityQ':joint['wholeSeriesSignFlipQ']},
    'defaultSignificantPartyTrends':[{'partyId':r['partyId'],'netChange':r['weightedNetDelta'],'p':r['pValue'],'q':r['qValue'],'sensitivityP':r['wholeSeriesSignFlipP'],'sensitivityQ':r['wholeSeriesSignFlipQ']} for r in strict['rows'] if r['qValue']<.05],
    'sourceAccessLimitations':read(ART/'primary-source-public-summary.json').get('accessLimitations',[]),
    'repostsDeduplicated':True,'missingValuesNotZero':True,'originalDataAndHistoricalWeightsPreserved':True,
    'social':{'tweet':'outputs/social/2026-10-20/tweet.he.txt','png':'outputs/social/2026-10-20/'+read(ART/'social/render-checks.json')['output'],'prompt':'outputs/social/2026-10-20/'+read(ART/'social/render-checks.json')['prompt'],'generator':'built-in image_gen','automaticTweetPosted':False},
    'receipts':{'release':sha(ART/'publication-receipt.json'),'publicReadback':sha(ART/'public-readback.json'),'publicBrowserReport':sha(browser),'publicVisualReview':sha(visual),'socialRenderChecks':sha(ART/'social/render-checks.json'),'socialIndependentReview':sha(ART/'social/independent-review.json'),'independentComparisonsReview':sha(ART/'model-comparisons-independent-review.json')}
}
assert release['asOf']==public['asOf']==strict['asOf']=='2026-10-20'
assert release['newPollCount']==4 and release['historyPolls']==132
assert set(public['newObservationIds'])=={'midgam_geva_2026-10-19','hamadad_consortium_2026-10-19','next_data_2026-10-19','lazar_2026-10-20'}
assert release['eligibleFull']==52 and release['eligibleWithout14']==strict['coverage']['pollCount']==41
out=ART/'completed.json'
assert not out.exists(),'Preserve dated completion'
out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','commit':commit,'filesVerified':public['filesVerified'],'meanSeats':groups,'thresholdPassPct':receipt['thresholdPassPct']}))
