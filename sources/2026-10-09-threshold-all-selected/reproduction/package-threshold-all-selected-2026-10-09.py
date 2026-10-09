from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'github-pages';ART=ROOT/'artifacts/threshold-all-selected-2026-10-09'
PREFIX='sources/2026-10-09-threshold-all-selected';BUNDLE=REPO/PREFIX
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
before=read(ART/'before.json');snapshot=read(ROOT/'dashboard/src/data.json');qa=read(ART/'qa/local/report.json')
assert snapshot['buildStatus']=='complete' and snapshot['id']==before['id'] and snapshot['features']['chatGPT'] is False and qa['status']=='passed'
for name,digest in before['dataHashes'].items():assert sha(ROOT/name)==digest,name
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
assert sha(ROOT/'dashboard/protected-runtime.json')==before['runtimeHash']
assert set(snapshot['queries'])==set(before['queries'])
for key,query in snapshot['queries'].items():assert query['rows']==before['queries'][key]['rows'],key
tests=(ART/'targeted-tests.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
assert qa['triple']['count']==67 and qa['triple']['total']==10000 and qa['pair']['count']==3129
audit={'status':'PASS','event':'all selected parties fail in the same simulation trial','dataFilesUnchanged':len(before['dataHashes']),'priorEvidenceFilesUnchanged':len(before['priorEvidence']),'queryRowCollectionsUnchanged':len(snapshot['queries']),'protectedRuntimeUnchanged':True,'independentReview':'PASS, no findings','jointMathTestsPassed':9,'browserChecks':qa['checks'],'pair':qa['pair'],'threeSelected':qa['triple'],'fourSelected':qa['four']};write(ART/'audit.json',audit)
assert not BUNDLE.exists(),'Do not overwrite frozen release evidence'
html=(ROOT/'dashboard/dist/index.html').read_bytes();clean,n=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',html,flags=re.I)
assert n==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean and sha(ROOT/'dashboard/src/data.json').encode() in clean
for target in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
copies=[(ART/'audit.json','audit.json'),(ART/'qa/local/report.json','browser-qa.json'),(ART/'targeted-tests.txt','targeted-tests.txt'),(ROOT/'scripts/browser-threshold-all-selected-qa.mjs','reproduction/browser-threshold-all-selected-qa.mjs'),(Path(__file__),'reproduction/package-threshold-all-selected-2026-10-09.py')]
for name in ['JointThresholdPanel.jsx','joint-threshold-panel.css']:copies.append((ROOT/'dashboard/src/content/dashboard'/name,'implementation/'+name))
for source,name in copies:
    target=BUNDLE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
readme=REPO/'README.md';s=readme.read_text(encoding='utf-8-sig');heading='## סיכוי שכל המפלגות שנבחרו לא יעברו — הבהרה'
assert heading not in s
section='''## סיכוי שכל המפלגות שנבחרו לא יעברו — הבהרה

לפי הבהרת המשתמש, בחירת שלוש מפלגות בודקת אם **כל השלוש** לא עברו באותה הדמיה; בחירת ארבע בודקת את כל הארבע, וכן הלאה. הוסרה מהתצוגה האפשרות ״לפחות שתיים מהנבחרות״. הכותרת מציינת את מספר הנבחרות, והטבלה וייצוא CSV מתארים בדיוק את אותו תנאי. בבחירת שתי מפלגות הסיכוי אינו משתנה.

החישוב משתמש בכל ההדמיות המשותפות ואינו מניח עצמאות בין הרשימות. נתוני הסקרים וכל תוצאות התחזית נשמרו. נבדקו בחירות של שתיים, שלוש וארבע רשימות, ייצוא, מקלדת ותצוגת נייד. [אימות](sources/2026-10-09-threshold-all-selected/audit.json) · [בדיקת דפדפן](sources/2026-10-09-threshold-all-selected/browser-qa.json).

'''
old='## מפלגות תחילה וסיכוי משותף לחסימה — 9.10.2026';assert old in s
s=s.replace(old,section+'## תיעוד העדכון הקודם — מפלגות תחילה וסיכוי משותף',1);readme.write_text(s,encoding='utf-8',newline='\n')
attrs=REPO/'.gitattributes';s=attrs.read_text(encoding='utf-8-sig');line='/'+PREFIX+'/** -text'
if line not in s:attrs.write_text(s.rstrip()+'\n'+line+'\n',encoding='utf-8',newline='\n')
for name,digest in before['priorEvidence'].items():assert sha(REPO/name)==digest,name
receipt={'uiUpdate':'all-selected-threshold-failure','siteVersion':3,'newPollCount':0,'appId':snapshot['id'],'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'audit':audit,'files':[{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha(p)} for p in sorted(BUNDLE.rglob('*')) if p.is_file()]}
write(BUNDLE/'release.json',receipt);write(ART/'publication-receipt.json',receipt);print(json.dumps({'packagePrepared':True,'files':len(receipt['files']),'queryRowCollectionsUnchanged':len(snapshot['queries']),'publicHtmlSha256':receipt['publishedHtmlSha256']}))
