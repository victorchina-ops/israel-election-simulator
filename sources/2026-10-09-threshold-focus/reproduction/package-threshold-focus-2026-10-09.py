"""Package threshold-first UI and exact joint-run accounting; freeze old evidence."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'github-pages';ART=ROOT/'artifacts/threshold-focus-2026-10-09'
PREFIX='sources/2026-10-09-threshold-focus';BUNDLE=REPO/PREFIX
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
before=read(ART/'before.json');snapshot=read(ROOT/'dashboard/src/data.json')
assert snapshot['buildStatus']=='complete' and snapshot['id']==before['id'] and snapshot['features']['chatGPT'] is False
for name,digest in before['dataHashes'].items():assert sha(ROOT/name)==digest,name
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
assert sha(ROOT/'dashboard/protected-runtime.json')==before['runtimeHash']
assert set(snapshot['queries'])==set(before['queries'])
for key,query in snapshot['queries'].items():
    old=before['queries'][key]['rows'];new=query['rows']
    if key=='simulation_summary':
        old=[r for r in old if r['key']!='generatedAt'];new=[r for r in new if r['key'] not in ['generatedAt','thresholdJoint']]
    assert new==old,key
old=read(ART/'before-baseline.json')['result'];new=read(ROOT/'artifacts/dashboard-baseline.json')['result']
for key,value in old.items():
    if key!='generatedAt':assert new[key]==value,key
assert new['thresholdJoint']['total']==new['iterations'] and sum(p['count'] for p in new['thresholdJoint']['patterns'])==new['iterations']
qa=read(ART/'qa/local/report.json');assert qa['status']=='passed'
tests=(ART/'full-tests.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',tests);passed=int(re.search(r'pass\s+(\d+)',tests).group(1));assert passed>=396
audit={'status':'PASS','dataFilesUnchanged':len(before['dataHashes']),'priorEvidenceFilesUnchanged':len(before['priorEvidence']),'oldQueryRowValuesUnchanged':True,'addedSummaryField':'thresholdJoint','oldFullSimulationResultsUnchangedExceptGeneratedAt':True,'jointOutcomeTotal':new['thresholdJoint']['total'],'usesAllTrialsExactAllocatorVerdicts':True,'assumesIndependentPartyOutcomes':False,'protectedRuntimeManifestUnchanged':True,'appIdUnchanged':True,'independentCodeReview':'PASS, no blocking findings; stale-result robustness concern resolved by setting busy synchronously before config mutation','testsPassed':passed,'localBrowserChecks':qa['checks'],'defaultWinterHendelJointFail':qa['defaultPair']}
write(ART/'audit.json',audit)
assert not BUNDLE.exists(),'Use a new release directory rather than overwrite frozen evidence'
html=(ROOT/'dashboard/dist/index.html').read_bytes();clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',html,flags=re.I)
assert count==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean and sha(ROOT/'dashboard/src/data.json').encode() in clean
for target in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
copies=[(ART/'audit.json','audit.json'),(ART/'full-tests.txt','full-tests.txt'),(ART/'qa/local/report.json','browser-qa.json'),(ROOT/'scripts/browser-threshold-focus-qa.mjs','reproduction/browser-threshold-focus-qa.mjs'),(Path(__file__),'reproduction/package-threshold-focus-2026-10-09.py'),(ROOT/'tests/joint-threshold-probabilities.test.mjs','tests/joint-threshold-probabilities.test.mjs')]
for name in ['DashboardContent.jsx','ThresholdPage.jsx','threshold-page.css','JointThresholdPanel.jsx','joint-threshold-panel.css','joint-threshold-probabilities.js','model/simulate.js']:
    copies.append((ROOT/'dashboard/src/content/dashboard'/name,'implementation/'+name))
for source,name in copies:
    target=BUNDLE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
readme=REPO/'README.md';s=readme.read_text(encoding='utf-8-sig');heading='## מפלגות תחילה וסיכוי משותף לחסימה — 9.10.2026';assert heading not in s
section='''## מפלגות תחילה וסיכוי משותף לחסימה — 9.10.2026

בלשונית **מפלגות וחסימה** סיכויי המעבר מופיעים תחילה, בלי בלוקי הגושים וההגדרות מעליהם. ההגדרות ממשיכות להגיע מהתמונה הכללית, עם קישור לשינוי שלהן.

אפשר לבחור שתי מפלגות או יותר ולבדוק אם **לפחות שתיים מהנבחרות** או **כולן** לא יעברו יחד. הסיכוי מחושב מספירת תוצאות החסימה המדויקות בכל ההדמיות, בלי להכפיל הסתברויות נפרדות או להניח עצמאות. בחירת המפלגות מציגה תשובה מאותן הרצות, ללא שינוי בתחזית. נדרשות חזרות ואומדן תמיכה לכל מפלגה שנבחרה; נתון חסר אינו אפס. טווח Wilson של 95% מתאר רק את שגיאת החישוב מההרצות, והסיכויים מותנים במודל ובהנחות ההשתתפות. בנייד התשובה מופיעה לפני רשימת הבחירה. אפשר לייצא את השאלה וההתפלגות ל־CSV.

בברירת המחדל הנוכחית, דיוק היסטורי וערוץ 14 מוחרג: וינטר והנדל–זליכה לא עברו יחד ב־3,129 מתוך 10,000 הרצות, כלומר **31.29% לפי המודל**. לא נוסף סקר, וכל תוצאות התחזית הקיימות נשמרו. [אימות הנתונים והחישוב](sources/2026-10-09-threshold-focus/audit.json) · [בדיקות דפדפן](sources/2026-10-09-threshold-focus/browser-qa.json).

'''
assert '## איפוס השתתפות מהיר — 9.10.2026' in s;s=s.replace('## איפוס השתתפות מהיר — 9.10.2026',section+'## איפוס השתתפות מהיר — 9.10.2026',1);readme.write_text(s,encoding='utf-8',newline='\n')
attrs=REPO/'.gitattributes';s=attrs.read_text(encoding='utf-8-sig');line='/'+PREFIX+'/** -text'
if line not in s:attrs.write_text(s.rstrip()+'\n'+line+'\n',encoding='utf-8',newline='\n')
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
receipt={'uiUpdate':'threshold-parties-first-and-joint-probability','siteVersion':3,'newPollCount':0,'appId':snapshot['id'],'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'audit':audit,'files':[{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha(p)} for p in sorted(BUNDLE.rglob('*')) if p.is_file()]}
write(BUNDLE/'release.json',receipt);write(ART/'publication-receipt.json',receipt)
print(json.dumps({'packagePrepared':True,'files':len(receipt['files']),'testsPassed':passed,'oldEvidencePreserved':len(before['priorEvidence']),'publicHtmlSha256':receipt['publishedHtmlSha256']}))
