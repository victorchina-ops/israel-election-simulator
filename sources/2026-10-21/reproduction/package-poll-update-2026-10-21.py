"""Package21Oct factual data and reproduction evidence after existing QA checks.

--check is a complete preflight. Frozen source formatting is preserved through
exact per-file/hash/line diagnostics, established before any package is written.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-21'
ART=ROOT/'artifacts/poll-checks'/DAY
REPO=ROOT/'github-pages'
PREFIX='sources/'+DAY
SOCIAL=ROOT/'outputs/social'/DAY
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
encoded=lambda x:(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
SOURCE_APPENDIX={
    'source-israelpolls/scan-receipt.json':('israelpolls-scan-receipt.json','5cb51b196aa9f49501d295f5396ed30d4bf1950e4ab6b510b26880b6524566dd'),
    'source-israelpolls/n12-history-table.png':('n12-history-table.png','455183961bd265f3df9f38584f7ccbb65537e03179c0ac7d9f3c6495dd8fc03d'),
    'source-israelpolls/c13-secondary-graphic-review.json':('c13-secondary-graphic-review.json','b3d950fc722f46c9046662652353b415a1e6baeaff038390c03b7063bf1b24c3'),
    'source-israelpolls/c13-published-graphic.png':('c13-published-graphic.png','c59e5e8c284bd6528c40a42149c1c53e52b75dc88dcbd55dcf0d672fc45eccaa'),
    'source-c13/independent-candidate-review.json':('c13-independent-candidate-review.json','84a55f995a587c0e0bfd11ae965a92255966a4d18e3256d8b5df970f3d462f70'),
    'source-root-coverage.json':('source-root-coverage.json','b2775516606b69f56f510af09a80616abd349cae3591bef0c761c1722919509c'),
}


def browser_receipts(phase,html_sha,snapshot_sha,plan_sha):
    reports=sorted((ART/('browser-'+phase)).glob('*/report.json'))
    direct=ART/('browser-'+phase)/'report.json'
    if direct.exists():reports.append(direct)
    assert reports,'Fresh browser evidence required'
    path=reports[-1];doc=read(path);visual=path.parent/'visual-review.json';review=read(visual)
    assert doc['status']=='passed' and doc['asOf']==DAY and doc['phase']==phase
    assert doc['browserAutomation']=='cua' and len(doc['checks'])>=6
    assert doc['officialSourceSnapshotSha256']==snapshot_sha and doc['servedHTMLSha256']==html_sha
    assert doc['sourcePlanSha256']==plan_sha
    assert review['status']=='passed' and review['browserReportSha256']==sha(path)
    assert review['visualInspectionCompleted'] and len(review['reviewedScreenshots'])>=3
    for name,digest in review['reviewedScreenshots'].items():
        assert Path(name).name==name and sha(path.parent/name)==digest
    return path,visual


def pinned_whitespace(source,public_path,accepted_hashes):
    # Git diagnoses the exact unchanged source bytes as a newly added file.
    with tempfile.TemporaryDirectory(prefix='poll-format-') as tmp:
        empty=Path(tmp)/'empty';empty.write_bytes(b'')
        run=subprocess.run(['git','-c','core.whitespace=cr-at-eol','-c','core.autocrlf=false','diff','--no-index','--check','--',str(empty),str(source)],capture_output=True)
    diagnostics=[]
    for line in run.stdout.decode('utf-8').splitlines():
        if not line or line.startswith('+'):continue
        match=re.search(r':(\d+): (new blank line at EOF\.|trailing whitespace\.)$',line)
        assert match,('Unexpected format diagnostic',source,line)
        diagnostics.append(public_path+':'+match.group(1)+': '+match.group(2))
    assert run.returncode in {0,1,2,3} and not run.stderr,('Format probe failed',source,run.stderr)
    if diagnostics:
        rel=source.relative_to(ROOT).as_posix()
        assert accepted_hashes.get(rel)==sha(source),('Fix formatting in new code; frozen evidence alone may retain exact diagnostics',rel,diagnostics)
        return {'path':public_path,'sourcePath':rel,'sha256':sha(source),'diagnostics':diagnostics}
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    assert not (ART/'publication-receipt.json').exists() and not (REPO/'updates'/DAY).exists()
    manifest=read(ART/'before/manifest.json');plan=read(ART/'source-plan.json');ingestion=read(ART/'ingestion-validation.json')
    assert plan['status']=='reviewed' and plan['asOf']==DAY and plan['publicCopyrightScopeReviewed']
    for name in ['ingestion-validation.json','strict-validation.json','model-comparison-validation.json','model-comparisons-independent-review.json']:
        assert read(ART/name)['status']=='PASS' and read(ART/name)['asOf']==DAY
    assert ingestion['sourcePlanSha256']==sha(ART/'source-plan.json')
    strict_validation=read(ART/'strict-validation.json')
    for rel,digest in strict_validation['inputHashes'].items():assert sha(ROOT/rel)==digest,('Validated numeric input changed',rel)
    adapter_gate=read(ART/'numeric-boundaries/opposition-predicate-adapter-independent-review.json')
    assert adapter_gate['status']=='PASS-SOURCE-GATE' and adapter_gate['asOf']==DAY
    assert adapter_gate['adapterSha256']==strict_validation['validatorSha256']==sha(ROOT/adapter_gate['adapterPath'])
    assert adapter_gate['diagnosisSha256']==sha(ART/'numeric-boundaries/opposition-predicate-diagnosis.json')
    assert adapter_gate['numericIndependentReviewSha256']==sha(ART/'numeric-boundaries/opposition-predicate-independent-review.json')
    full=read(ROOT/'data/strict-party-trends.json');default=read(ROOT/'data/strict-party-trends-without-channel14.json')
    current=read(ROOT/'data/current-polls.json');history=read(ROOT/'data/poll-history.json')
    assert full['asOf']==default['asOf']==current['asOf']==history['asOf']==DAY
    assert len(current['polls'])==manifest['activePollCount']==ingestion['activePollCount']
    assert len(history['polls'])==manifest['historyPollCount']+len(plan['polls'])==ingestion['historyPollCount']
    assert full['coverage']['pollCount']==ingestion['fullStrict']['polls']
    assert default['coverage']['pollCount']==ingestion['defaultWithoutChannel14']['polls']
    def preserved():
        for group in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']:
            for rel,digest in manifest[group].items():assert sha(ROOT/rel)==digest,(group,rel)
        mutable={'current-polls.json','poll-history.json','sources.json','survey-documents-2026-09-14.json','strict-party-trends.json','strict-party-trends-without-channel14.json','poll-correlation.json'}
        for p in (ROOT/'data').glob('*.json'):
            if p.name not in mutable:assert sha(p)==manifest['files'][p.relative_to(ROOT).as_posix()]
    preserved()
    selected_dir=[p.parent for p in (ROOT/'artifacts/strict-post-close/without-channel14'/DAY).glob('*/party-analysis.json') if sha(p)==default['provenance']['analysisSha256']]
    assert len(selected_dir)==1 and read(selected_dir[0]/'validation.json')['status']=='PASS'
    corr=read(ROOT/'data/poll-correlation.json')
    corr_dirs=[p.parent for p in (ROOT/'artifacts/poll-correlation'/DAY).glob('*/profile.json') if read(p)==corr]
    assert len(corr_dirs)==1 and read(corr_dirs[0]/'independent-audit.json')['status']=='passed'
    snapshot=read(ROOT/'dashboard/src/data.json');snapshot_sha=sha(ROOT/'dashboard/src/data.json')
    assert snapshot['dataAsOf']==DAY and snapshot['buildStatus']=='complete' and snapshot['features']['chatGPT'] is False
    cfg={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
    assert cfg['weightMode']=='quality' and all(cfg[k] is False for k in ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])
    assert cfg['partyBlocs']['winter']=='a' and cfg['partyBlocs']['hendel']=='other'
    comparison=read(ART/'model-comparison.json');similarity=read(ART/'model-comparison-similarity.json');independent=read(ART/'model-comparisons-independent-review.json')
    assert independent['snapshotSha256']==snapshot_sha and independent['sourcePlanSha256']==sha(ART/'source-plan.json')
    for stem,enabled in [('model-comparison',False),('model-comparison-similarity',True)]:
        report=read(ART/(stem+'.json'));assert report['status']=='passed'
        assert independent['reports'][stem]['sha256']==sha(ART/(stem+'.json'))
        assert {p['pollsterId'] for p in report['pollChanges'] if p['changed']}=={s['pollsterId'] for s in plan['polls']}
        for phase in ['before','after']:
            c=report[phase]['config'];assert c['pollCorrelationEnabled'] is enabled and c['includeChannel14'] is c['signalNoiseEnabled'] is False
    compiled=(ROOT/'dashboard/dist/index.html').read_bytes()
    clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',compiled,flags=re.I)
    assert count==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
    assert snapshot_sha.encode() in clean
    browser,visual=browser_receipts('local',hashlib.sha256(compiled).hexdigest(),snapshot_sha,sha(ART/'source-plan.json'))
    tests=(ART/'test-results-final.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
    passed=int(re.search(r'pass\s+(\d+)',tests).group(1))
    assert passed>=read(ART/'before/artifacts/poll-checks/2026-10-20-evening/completed.json')['testsPassed']
    render=read(ART/'social/render-checks.json');social_review=read(ART/'social/independent-review.json')
    assert render['status']==social_review['status']=='PASS' and render['asOf']==DAY
    assert render['visualInspectionCompleted'] and social_review['visualInspectionCompleted']
    assert social_review['renderReceiptSha256']==sha(ART/'social/render-checks.json') and social_review['imageSha256']==render['outputSha256']
    # The current-model tweet and a source-only image are separate evidence.
    assert render['modelComparisonFile']=='model-comparison-similarity.json'
    assert render['modelComparisonSha256']==sha(ART/render['modelComparisonFile'])
    if render.get('imageEvidenceKind')=='published_poll_comparison':
        source_review=read(ART/'social/source-pixel-review.json')
        assert source_review.get('status')=='PASS-SOURCE-BOUND-IMAGE'
        assert source_review['visualInspectionCompleted'] and source_review['meansOrProbabilitiesShown'] is False
        assert source_review['imageSha256']==render['outputSha256']
        assert render['sourcePixelReviewSha256']==sha(ART/'social/source-pixel-review.json')
    for key in ['output','prompt']:
        assert Path(render[key]).name==render[key] and sha(SOCIAL/render[key])==render[key+'Sha256']
    assert 'https://victorchina-ops.github.io/israel-election-simulator/' in (SOCIAL/'tweet.he.txt').read_text(encoding='utf-8-sig')
    copies={};writes={};files={}
    def copy(source,relative):
        assert source.is_file() and not Path(relative).is_absolute() and '..' not in Path(relative).parts
        dest=REPO/relative
        assert dest not in copies or sha(copies[dest])==sha(source)
        if dest.exists():assert dest.read_bytes()==source.read_bytes(),('Existing dated evidence differs',relative)
        copies[dest]=source;files[relative]={'path':relative,'sha256':sha(source),'bytes':source.stat().st_size}
    def source(source,name):copy(source,PREFIX+'/'+name)
    accepted=dict(manifest['files'])
    receipt=read(ART/'ingestion-receipt.json')
    existing=dict(receipt['publicEvidenceFiles']);existing.update({'source-plan.json':sha(ART/'source-plan.json'),'ingestion-receipt.json':sha(ART/'ingestion-receipt.json')})
    for p in (REPO/PREFIX).rglob('*'):
        if p.is_file():
            rel=p.relative_to(REPO/PREFIX).as_posix();assert existing.get(rel)==sha(p),('Unaccounted source file',rel)
            files[p.relative_to(REPO).as_posix()]={'path':p.relative_to(REPO).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
    for s in plan['polls']:
        assert sha(ROOT/s['candidatePath'])==s['candidateSha256']
        for item in s['publicFiles']:
            assert sha(ROOT/item['sourcePath'])==item['sha256'];accepted[item['sourcePath']]=item['sha256']
            source(ROOT/item['sourcePath'],s['folder']+'/'+item['publicName'])
    public_summary=ART/'primary-source-public-summary.json';summary=read(public_summary)
    assert summary['asOf']==DAY and summary['fullCopyrightedArticleBodiesExcluded'] is True
    assert set(summary['newObservationIds'])=={read(ROOT/s['candidatePath'])['id'] for s in plan['polls']}
    source(public_summary,public_summary.name)
    for item in plan.get('sourceReview',{}).get('publicFiles',[]):
        assert sha(ROOT/item['sourcePath'])==item['sha256'];source(ROOT/item['sourcePath'],'source-discovery/'+item['publicName']);accepted[item['sourcePath']]=item['sha256']
    additional_source=[]
    for relative,(name,digest) in SOURCE_APPENDIX.items():
        path=ART/relative;assert sha(path)==digest
        source(path,'source-discovery/'+name)
        accepted[path.relative_to(ROOT).as_posix()]=digest
        additional_source.append({'sourcePath':path.relative_to(ROOT).as_posix(),'publicPath':PREFIX+'/source-discovery/'+name,'sha256':digest})
    for name in ['current-polls','poll-history','sources','parties','calibration','survey-documents-2026-09-14','strict-party-trends','strict-party-trends-without-channel14','poll-correlation']:
        source(ROOT/'data'/(name+'.json'),name+'.json')
    for name in ['source-plan.json','ingestion-preflight.json','ingestion-receipt.json','ingestion-validation.json','strict-validation.json','model-comparison.json','model-comparison-similarity.json','model-comparison-validation.json','model-comparisons-independent-review.json','test-results-final.txt']:
        source(ART/name,name)
    for name in ['analysis.json','by-pollster.csv','independent-strict-numeric-audit.json','party-analysis.json','party-by-pollster.csv','party-independent.json','party-overall.csv','party-summary-he.md','party-validation.json','summary-he.md','n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json','lazar-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']:
        source(ROOT/'artifacts/strict-post-close'/name,'trends/canonical/'+name)
    for label,folder in [('without-channel14',selected_dir[0]),('poll-correlation',corr_dirs[0]),('numeric-lineage',ART/'numeric-lineage'),('numeric-boundaries',ART/'numeric-boundaries')]:
        for p in sorted(folder.rglob('*')):
            if p.is_file():assert p.suffix.lower() not in {'.html','.htm'};source(p,'trends/'+label+'/'+p.relative_to(folder).as_posix())
    reproducers=['ingest-polls-2026-10-21.py','validate-ingestion-2026-10-21.py','run-exact-trends-2026-10-21.py','recompute-strict-trends-2026-10-21.py','validate-strict-trends-2026-10-21.py','build-trend-summaries-2026-10-21.py','build-strict-party-trends.py','derive-strict-trends-without-channel14.py','build-poll-correlation.py','audit-poll-correlation.py','compare-poll-update-2026-10-21.mjs','compare-poll-update.mjs','compare-poll-update-similarity-2026-10-20-evening.mjs','validate-model-comparison-2026-10-21.mjs','review-model-comparisons-2026-10-21.py','review-model-comparisons-2026-10-20-evening.py','build-trend-summaries-2026-10-20-evening.py','exact_scalar_marginals_2026_10_20.py','run-exact-trends-2026-10-20-evening.py','run-exact-trends-2026-10-20-evening-party-schema-r1.py','run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py','validate-poll-update-2026-10-20-evening.py','package-poll-update-2026-10-21.py','review-staged-poll-update-2026-10-21.py','readback-poll-update-2026-10-21.py','complete-poll-update-2026-10-21.py']
    for name in reproducers:source(ROOT/'scripts'/name,'reproduction/'+name)
    for name in ['validate-strict-trends-2026-10-21-predicate-r1.py','diagnose-opposition-boundary-2026-10-21.py','validate-strict-cohort-2026-10-21.py','promote-strict-validation-2026-10-21.py']:
        source(ROOT/'scripts'/name,'reproduction/'+name)
    source(ART/'strict-validation-promotion.json','strict-validation-promotion.json')
    source(browser,'browser-local-report.json');source(visual,'browser-local-visual-review.json')
    for name in ['render-checks.json','independent-review.json']:source(ART/'social'/name,'social/'+name)
    if render.get('imageEvidenceKind')=='published_poll_comparison':source(ART/'social/source-pixel-review.json','social/source-pixel-review.json')
    for p in SOCIAL.iterdir():
        if p.is_file():assert p.suffix.lower() in {'.png','.txt','.json'};copy(p,'updates/'+DAY+'/'+p.name)
    # Bind preserved formatting up front; no global whitespace ignore exists.
    whitespace=[]
    for dest,original in copies.items():
        entry=pinned_whitespace(original,dest.relative_to(REPO).as_posix(),accepted)
        if entry:whitespace.append(entry)
    def means(report,phase):return {g['id']:g['stats']['mean'] for g in report[phase]['reportingGroups']}
    def thresholds(report,phase):return {p['id']:100*p['passProbability'] for p in report[phase]['parties'] if p['id'] in {'winter','hendel'}}
    def mean_label(report):
        labels={'a':'קואליציה','b':'אופוזיציה ללא ערביות','arab':'מפלגות ערביות','other':'הנדל–זליכה ושאר הרשימות'}
        return '; '.join(labels[k]+' '+format(v,'.2f') for k,v in means(report,'after').items())
    def threshold_label(report):
        labels={'winter':'וינטר','hendel':'הנדל–זליכה'}
        return '; '.join(labels[k]+' '+format(v,'.2f')+'%' for k,v in thresholds(report,'after').items())
    paragraphs=[]
    for s in plan['polls']:
        p=read(ROOT/s['candidatePath']);field=(str(p.get('fieldworkStart'))+'–'+str(p.get('fieldworkEnd'))) if p.get('fieldworkVerified') else 'לא אומת'
        paragraphs.append(f"{p['publisher']} / {p['pollster']}: פרסום {p['date']}; איסוף {field}; מדגם {p.get('sampleSize') if p.get('sampleSize') is not None else 'לא פורסם'}. [מקור]({p['sourceUrl']}).")
    heading='## עדכון '+DAY+'\n\n'
    def names(key):return ', '.join(r['partyName'] for r in default['rows'] if r[key]<.05) or 'אין'
    section=heading+'\n\n'.join(paragraphs)+f"\n\nנוספו {len(plan['polls'])} סקרים; במאגר {len(current['polls'])} מכונים פעילים ו־{len(history['polls'])} תצפיות היסטוריות. מועדי פרסום ואיסוף נשמרים בנפרד; שדות חסרים אינם אפס. [המקורות והמגבלות]({PREFIX}/primary-source-public-summary.json).\n\n"
    section+=f"מבחני המגמות חושבו מחדש: בקבוצה המלאה {full['coverage']['pollCount']} סקרים זכאים; ללא ערוץ 14 {default['coverage']['pollCount']}. {ingestion['fullStrict']['unknownFieldworkExcluded']} פרסומים הוחרגו עקב איסוף לא מאומת. החרגת ערוץ 14 בברירת המחדל היא בחירת מפרסם נפרדת. במבחן הפרמוטציות הראשי אחרי BH, מובהקות: {names('qValue')}; בהיפוך כיוון סדרות מכונים אחרי BH, מובהקות: {names('wholeSeriesSignFlipQ')}. אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [סיכום המגמות]({PREFIX}/trends/canonical/party-summary-he.md).\n\n"
    section+=f"ברירת המחדל נשמרה: דיוק היסטורי, ללא ערוץ 14, דמיון סקרים כבוי ואות־רעש כבוי. ממוצעי המנדטים במודל: {mean_label(comparison)}; סיכויי מעבר במודל: {threshold_label(comparison)}. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).\n\n"
    section+=f"תרחיש הדיווח המועדף מוסיף דמיון סקרים באותם תנאים, עם וינטר בקואליציה והנדל–זליכה ללא שיוך. ממוצעי המנדטים: {mean_label(similarity)}; סיכויי מעבר במודל: {threshold_label(similarity)}. אלו תוצאות מודל, לא אחוזי תמיכה שפורסמו. דמיון תחזיות אינו מדידת חפיפת משיבים או שגיאות משותפות, ולא הוכח כמשפר כיול. [השוואת התרחיש]({PREFIX}/model-comparison-similarity.json).\n\n"
    section+=f"[טיוטת ציוץ](updates/{DAY}/tweet.he.txt) · [איור לשיתוף](updates/{DAY}/{render['output']}) · [אימות עצמאי]({PREFIX}/model-comparisons-independent-review.json).\n\n"
    body=(REPO/'README.md').read_text(encoding='utf-8-sig');assert heading not in body
    match=re.search(r'^## ',body,re.M);assert match
    writes[REPO/'README.md']=(body[:match.start()]+section+body[match.start():]).encode('utf-8')
    attrs=(REPO/'.gitattributes').read_text(encoding='utf-8-sig').rstrip()+'\n'
    for prefix in [PREFIX,'updates/'+DAY]:
        line='/'+prefix+'/** -text';assert line not in attrs;attrs+=line+'\n'
    writes[REPO/'.gitattributes']=attrs.encode('utf-8')
    for p in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:writes[p]=clean
    writes[ROOT/'dashboard-snapshot.json']=(ROOT/'dashboard/src/data.json').read_bytes()
    release={'status':'PASS','asOf':DAY,'runId':'reviewed','newPollCount':len(plan['polls']),
        'observationDateKinds':{read(ROOT/s['candidatePath'])['id']:read(ROOT/s['candidatePath']).get('dateKind') for s in plan['polls']},
        'observationPublicationDates':sorted({read(ROOT/s['candidatePath'])['date'] for s in plan['polls']}),
        'activePolls':len(current['polls']),'historyPolls':len(history['polls']),'eligibleFull':full['coverage']['pollCount'],'eligibleWithout14':default['coverage']['pollCount'],
        'unknownFieldworkExcluded':ingestion['fullStrict']['unknownFieldworkExcluded'],'testsPassed':passed,
        'snapshotSha256':snapshot_sha,'publishedHtmlSha256':hashlib.sha256(clean).hexdigest(),'featuresChatGPT':False,
        'defaultWeightMode':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,
        'winterDefaultBloc':'coalition','hendelDefaultBloc':'unassigned','preferredReportingSimilarityEnabled':True,
        'reviewedExactHelpersUnchanged':manifest['reviewedExactHelpers'],'socialDraftOnly':True,
        'fullArticleBodiesExcludedFromNewRelease':True,'compiledTo120DatasetExcludedFromNewRelease':True,
        'sourcePlanSha256':sha(ART/'source-plan.json'),'comparisonHashes':{s:sha(ART/(s+'.json')) for s in ['model-comparison','model-comparison-similarity']},
        'additionalSourceEvidence':additional_source,
        'whitespaceEvidence':whitespace,'files':[files[k] for k in sorted(files)]}
    if args.check:
        print(json.dumps({'status':'PASS','phase':'package-preflight-no-files-written','files':len(files),'whitespaceEvidence':whitespace},ensure_ascii=False));return
    for dest,original in copies.items():
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(original,dest)
    for dest,body in writes.items():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
    (ART/'publication-receipt.json').write_bytes(encoded(release));(REPO/PREFIX/'release.json').write_bytes(encoded(release))
    preserved();print(json.dumps({'status':'PASS','files':len(files),'publishedHtmlSha256':release['publishedHtmlSha256']}))


if __name__=='__main__':main()
