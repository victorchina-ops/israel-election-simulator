"""Package the requested V3 presentation; retain prior surveys and evidence."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'github-pages';ART=ROOT/'artifacts/site-v3-2026-10-09';PREFIX='sources/2026-10-09-site-v3';BUNDLE=REPO/PREFIX
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
snapshot=read(ROOT/'dashboard/src/data.json');config={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
assert snapshot['buildStatus']=='complete' and snapshot['id']=='dashboard:ad5864c5-c821-45f8-abfc-62e02191e56c'
assert snapshot['features']['chatGPT'] is False
assert config['weightMode']=='quality' and not config['includeChannel14'] and not config['pollCorrelationEnabled'] and not config['signalNoiseEnabled']
manifest=read(ART/'before/manifest.json');assert sha(ROOT/'dashboard/protected-runtime.json')==manifest['files']['dashboard/protected-runtime.json']
for name,digest in manifest['priorEvidence'].items():assert sha(REPO/name)==digest,name
assert read(ART/'regression.json')['status']=='PASS'
qa=read(ART/'qa/local/report.json');assert qa['status']=='passed'
review=read(ART/'independent-code-review.json');assert review['conclusion']=='PASS' and not review['findings']
for name,digest in review['sourceHashes'].items():assert sha(ROOT/name)==digest,name
visual=read(ART/'review/final-review.json');assert visual['conclusion']=='PASS' and visual['buildSha256']==sha(ROOT/'dashboard/dist/index.html')
tests=(ART/'full-tests.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',tests);passed=int(re.search(r'pass\s+(\d+)',tests).group(1));assert passed>=384
html=(ROOT/'dashboard/dist/index.html').read_bytes();clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',html,flags=re.I);assert count==1
assert b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean and sha(ROOT/'dashboard/src/data.json').encode() in clean
for target in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
copies=[(ART/'regression.json','regression.json'),(ART/'full-tests.txt','full-tests.txt'),(ART/'independent-code-review.json','independent-code-review.json'),(ART/'qa/local/report.json','browser-qa.json'),(ART/'review/final-review.json','visual-review.json'),(ART/'review/keyboard-assignment.json','keyboard-assignment.json'),(ART/'before/manifest.json','before-manifest.json'),(ROOT/'dashboard/src/theme.css','implementation/theme.css')]
for source in sorted((ROOT/'dashboard/src/content').rglob('*')):
    if source.is_file():copies.append((source,'implementation/content/'+source.relative_to(ROOT/'dashboard/src/content').as_posix()))
for name in ['audit-site-v3.mjs','browser-site-v3-qa.mjs','package-public-site-v3-2026-10-09.py']:
    copies.append((ROOT/'scripts'/name,'reproduction/'+name))
for name in ['v3-result-party-assignment.test.mjs','site-v3-navigation.test.mjs','about-version3.test.mjs','quick-scenario-controls.test.mjs','v2-scenario-controls.test.mjs','step-control-display-precision.test.mjs']:
    copies.append((ROOT/'tests'/name,'tests/'+name))
for source,name in copies:
    target=BUNDLE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
note='''# גרסה 3 — 9.10.2026

עדכון ממשק לבקשת המשתמש, ללא סקר חדש וללא שינוי בתוצאות ברירת המחדל.

- ביקור חדש נפתח באודות: התמונה המקורית, פרטי הקשר, ההסברים והקרדיטים נשמרו. קישורים לדף מסוים ממשיכים לפתוח אותו.
- Ask ChatGPT הוסר. בחירת בהיר/כהה זמינה בכותרת ונשמרת לאחר רענון.
- שורת הגדרות מהירות מופיעה מעל התוצאות: שיטת שקלול, ערוץ 14, תיקון דמיון, הצבעה ביישובים לא־יהודיים ומוטיבציה לשני הגושים. אלו קיצורי דרך לאותו תרחיש; אין להם מצב נפרד.
- שלוש קבוצות ההגדרות המלאות פרוסות ופתוחות: סקרים, הרכב גושים והשתתפות. הגדרות טכניות משניות נשארות בהרחבות.
- מפלגות בתוצאות מוצגות בקואליציה מימין, ללא שיוך באמצע ובאופוזיציה משמאל. ליד כל מפלגה יש בחירה נגישה של גוש; במחשב אפשר גם לגרור. בכל מעבר המפלגה נגרעת מהגוש הקודם. בנייד מוצגות קבוצות שלמות זו אחר זו.
- המספרים בתצוגה מעוגלים לקריאות, בלי לשנות את קלט החישוב. בכל הדמיה נשמרים 120 מנדטים.

הבנייה משתמשת בנתיב המקור הרשמי של אפליקציית Data: הקוד המוגן שכבר היה בפרויקט תומך ב־features.chatGPT=false ובבחירת מראה. הקוד המוגן לא שונה, וכל 234 הקבצים נבדקו מול המניפסט. הבחירה נדרשה כדי לממש את בקשת המשתמש, שכן הבנייה המוכנה מראש של גרסה 2 עדיין הציגה Ask ChatGPT.

19 קובצי נתונים וכל האוספים המספריים שנבדקו נשמרו. [זהות התוצאות](regression.json), [בדיקות דפדפן](browser-qa.json), [סקירת קוד](independent-code-review.json), [סקירה חזותית](visual-review.json), [בדיקת מקלדת בנייד](keyboard-assignment.json).
'''
(BUNDLE/'version3.he.md').write_text(note,encoding='utf-8',newline='\n')
readme=REPO/'README.md';s=readme.read_text(encoding='utf-8-sig');heading='## גרסה 3 — אפשרויות גלויות ואודות'
assert heading not in s
section='''## גרסה 3 — אפשרויות גלויות ואודות

ביקור חדש נפתח באודות עם התמונה, ההסברים ופרטי היוצר. מעל התוצאות יש שורת אפשרויות מהירות, ולכל מפלגה אפשר לבחור גוש ישירות בתוצאות; במחשב אפשר גם לגרור בין הגושים. ההגדרות המלאות פרוסות בשלוש קבוצות פתוחות. Ask ChatGPT הוסר, ובחירת בהיר/כהה זמינה ונשמרת לאחר רענון.

נתוני הסקרים ותוצאות ברירת המחדל נשמרו. לא נוסף סקר בעדכון זה. [פרטי העדכון והבדיקות](sources/2026-10-09-site-v3/version3.he.md). גרסה 2 והסעיפים הבאים נשמרים כתיעוד היסטורי.

'''
s=s.replace('## גרסה 2 — ממשק ברור יותר',section+'## גרסה 2 — תיעוד הממשק הקודם',1);readme.write_text(s,encoding='utf-8',newline='\n')
attrs=REPO/'.gitattributes';s=attrs.read_text(encoding='utf-8-sig');line='/'+PREFIX+'/** -text'
if line not in s:attrs.write_text(s.rstrip()+'\n'+line+'\n',encoding='utf-8',newline='\n')
for name,digest in manifest['priorEvidence'].items():assert sha(REPO/name)==digest,name
receipt={'siteVersion':3,'dataAsOf':snapshot['dataAsOf'],'newPollCount':0,'appId':snapshot['id'],'buildPath':'official-project-source','protectedRuntimeFilesUnchanged':234,'askChatGptDisabled':True,'appearanceControlVerified':True,'aboutFirstForFreshVisits':True,'originalPortraitAndCopyRestored':True,'directExclusivePartyAssignment':True,'weightsDefault':'quality','includeChannel14Default':False,'pollCorrelationDefault':False,'signalNoiseRetired':True,'testsPassed':passed,'exactNumericalCollections':20,'priorEvidenceFilesPreserved':len(manifest['priorEvidence']),'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'files':[{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha(p)} for p in sorted(BUNDLE.rglob('*')) if p.is_file() and p.name!='release.json']}
write(BUNDLE/'release.json',receipt);write(ART/'publication-receipt.json',receipt)
print(json.dumps({'packagePrepared':True,'testsPassed':passed,'files':len(receipt['files']),'olderEvidencePreserved':len(manifest['priorEvidence']),'publicHtmlSha256':receipt['publishedHtmlSha256']}))
