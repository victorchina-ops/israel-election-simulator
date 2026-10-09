"""Publish the small requested UI amendment without changing existing evidence."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT/'github-pages'; ART=ROOT/'artifacts/turnout-reset-2026-10-09'
PREFIX='sources/2026-10-09-turnout-reset'; BUNDLE=REPO/PREFIX
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
before=read(ART/'before.json'); snapshot=read(ROOT/'dashboard/src/data.json')
assert snapshot['buildStatus']=='complete' and snapshot['id']==before['id']
assert snapshot['features']['chatGPT'] is False
for name,digest in before['dataHashes'].items():assert sha(ROOT/name)==digest,name
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
assert sha(ROOT/'dashboard/protected-runtime.json')==before['files']['dashboard/protected-runtime.json']
assert set(snapshot['queries'])==set(before['queries'])
for key,query in snapshot['queries'].items():assert query['rows']==before['queries'][key]['rows'],key
qa=read(ART/'qa/local/report.json');assert qa['status']=='passed'
audit={'status':'PASS','dataFilesUnchanged':len(before['dataHashes']),'priorEvidenceFilesUnchanged':len(before['priorEvidence']),'queryRowCollectionsUnchanged':len(snapshot['queries']),'protectedRuntimeManifestUnchanged':True,'appIdUnchanged':True,'independentReview':'PASS: shared handler, preserved settings, keyboard/focus and responsive button; no findings','localBrowserChecks':qa['checks']}
write(ART/'audit.json',audit)
assert not BUNDLE.exists(),'Use a new release path rather than overwriting frozen evidence'
html=(ROOT/'dashboard/dist/index.html').read_bytes();clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',html,flags=re.I)
assert count==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
assert sha(ROOT/'dashboard/src/data.json').encode() in clean
for target in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
copies=[(ART/'audit.json','audit.json'),(ART/'qa/local/report.json','browser-qa.json'),(ROOT/'scripts/browser-turnout-reset-qa.mjs','reproduction/browser-turnout-reset-qa.mjs'),(Path(__file__),'reproduction/package-turnout-reset-2026-10-09.py')]
for name in ['QuickScenarioControls.jsx','quick-scenario-controls.css','DashboardContent.jsx']:
    copies.append((ROOT/'dashboard/src/content/dashboard'/name,'implementation/'+name))
for source,name in copies:
    target=BUNDLE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
readme=REPO/'README.md';s=readme.read_text(encoding='utf-8-sig')
heading='## איפוס השתתפות מהיר — 9.10.2026';assert heading not in s
section='''## איפוס השתתפות מהיר — 9.10.2026

בתוך בלוק האפשרויות העליון נוסף כפתור **איפוס השתתפות ומוטיבציה**. הוא מחזיר את אחוזי ההצבעה לבסיס 2022, את המוטיבציה ל־100% ואת מכפיל המעטפות החיצוניות ל־1. כפתור האיפוס התחתון נשאר. שיטת השקלול, בחירת הסקרים והרכב הגושים נשמרים. נבדק במחשב ובנייד, בבהיר ובכהה. נתוני הסקרים ותוצאות ברירת המחדל לא השתנו.

[בדיקות ושימור הנתונים](sources/2026-10-09-turnout-reset/audit.json) · [בדיקת דפדפן](sources/2026-10-09-turnout-reset/browser-qa.json).

'''
assert '## גרסה 3 — אפשרויות גלויות ואודות' in s
s=s.replace('## גרסה 3 — אפשרויות גלויות ואודות',section+'## גרסה 3 — אפשרויות גלויות ואודות',1);readme.write_text(s,encoding='utf-8',newline='\n')
attrs=REPO/'.gitattributes';s=attrs.read_text(encoding='utf-8-sig');line='/'+PREFIX+'/** -text'
if line not in s:attrs.write_text(s.rstrip()+'\n'+line+'\n',encoding='utf-8',newline='\n')
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
receipt={'uiUpdate':'quick-participation-reset','siteVersion':3,'newPollCount':0,'appId':snapshot['id'],'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'audit':audit,'files':[{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha(p)} for p in sorted(BUNDLE.rglob('*')) if p.is_file()]}
write(BUNDLE/'release.json',receipt);write(ART/'publication-receipt.json',receipt)
print(json.dumps({'packagePrepared':True,'files':len(receipt['files']),'publicHtmlSha256':receipt['publishedHtmlSha256'],'audit':audit}))
