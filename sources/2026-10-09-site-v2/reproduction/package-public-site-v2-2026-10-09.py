"""Publish the reviewed V2 interface, retaining all old poll/source evidence."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'github-pages';ART=ROOT/'artifacts/site-v2-2026-10-09'
PREFIX='sources/2026-10-09-site-v2';BUNDLE=REPO/PREFIX
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
snapshot=read(ROOT/'dashboard/src/data.json');config={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
assert snapshot['buildStatus']=='complete' and snapshot['id']=='dashboard:ad5864c5-c821-45f8-abfc-62e02191e56c'
assert config['weightMode']=='quality' and not config['includeChannel14'] and not config['pollCorrelationEnabled'] and not config['signalNoiseEnabled']
audit=read(ART/'regression.json');assert audit['status']=='PASS' and len(audit['exactNumericalCollections'])==20
assert read(ART/'qa/local/report.json')['status']=='passed'
assert read(ART/'qa/controls/report.json')['status'] in ['pass','passed','PASS']
assert read(ART/'qa/methods/report.json')['passed'] is True
review=read(ART/'independent-code-review.json')
assert review['conclusion']=='PASS' and not review['unresolvedFindings']
for name,digest in review['sourceSha256'].items():assert sha(ROOT/name)==digest,name
threshold=read(ART/'review/threshold-v2/qa.json')
assert threshold['status']=='passed' and threshold['buildSha256']==sha(ROOT/'dashboard/dist/index.html')
text=(ART/'full-tests.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',text);passed=int(re.search(r'pass\s+(\d+)',text).group(1));assert passed>=374
manifest=read(ART/'before/manifest.json')
for name,digest in manifest['priorEvidence'].items():assert sha(REPO/name)==digest,name
html=(ROOT/'dashboard/dist/index.html').read_bytes();clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',html,flags=re.I);assert count==1
assert b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean and sha(ROOT/'dashboard/src/data.json').encode() in clean
for target in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
copies=[(ART/'regression.json','regression.json'),(ART/'full-tests.txt','full-tests.txt'),(ART/'independent-code-review.json','independent-code-review.json'),
 (ART/'review/ui-ux-review.he.md','ui-ux-review.he.md'),(ART/'review/v2-review-result.he.md','v2-visual-review.he.md'),(ART/'review/threshold-v2/qa.json','threshold-qa.json'),(ART/'qa/local/report.json','browser-qa.json'),(ART/'qa/controls/report.json','controls-qa.json'),(ART/'qa/methods/report.json','methods-qa.json'),(ART/'before/manifest.json','before-manifest.json')]
for source in sorted((ROOT/'dashboard/src/content').rglob('*')):
    if source.is_file():copies.append((source,'implementation/content/'+source.relative_to(ROOT/'dashboard/src/content').as_posix()))
for name in ['audit-site-v2.mjs','browser-site-v2-qa.mjs','browser-v2-controls-qa.mjs','package-public-site-v2-2026-10-09.py']:
    copies.append((ROOT/'scripts'/name,'reproduction/'+name))
for name in ['site-v2-policy.test.mjs','v2-scenario-controls.test.mjs','threshold-v2-histogram.test.mjs','signal-noise-ui.test.mjs']:
    copies.append((ROOT/'tests'/name,'tests/'+name))
for source,name in copies:
    target=BUNDLE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
note='''# גרסה 2 — ממשק, ניווט והסברים, 9.10.2026

זהו עדכון ממשק ללא הוספת סקר. הוסרה האפשרות הניסיונית ״אות ורעש״ לבקשת המשתמש: ההשוואה הראתה שהפעלתה משתמשת במקורות ובמועדי תצפית שונים, ולכן אין לייחס את ההפרש במנדטים למסנן בלבד או להציגו כתחזית עדיפה. תרחיש ישן שביקש אותה נטען עם האפשרות כבויה, תוך הודעה מפורשת ושמירת יתר ההגדרות. הדוחות, הניסוי והקרדיט לאריאל דניאלי/עד120 נשמרים בארכיון.

הניווט מחולק לשש משימות: תמונת מצב, מפלגות וחסימה, מגמות, תרחישי מנדטים, הסקרים, ושיטות והסברים. הגדרות התרחיש מרוכזות בהרחבה אחת; בה שלוש קטגוריות, ושני המתגים שנותרו בתוך הגדרות הסקרים. במחשב הם בשורה אחת ובנייד בטור. התוצאות מתעדכנות אוטומטית וההגדרות נשמרות במעבר בין דפים.

תמונת המצב מציגה סיכויי רוב, ממוצע מנדטים וטווח המכיל 90% מההדמיות. זהו פיזור מותנה במודל, ולא התחייבות לתוצאות הבחירות. רווחי הסמך הטכניים של ההרצות נשארים בפירוט ובייצוא, ואינם מוצגים כטווח בחירות. סיכוי לרוב חשבוני אינו סיכוי להרכבת ממשלה.

פירוט המפלגות וארכיון הדוחות סגורים בתחילה ונפתחים לפי צורך. הרשימות הקרובות ל־50% סיכוי מעבר מוצגות ראשונות. הלוגואים גדולים יותר. הטבלה המאומתת של שינוי ומובהקות נשארת לפני הגרפים. אין שינוי בערכי p/q או בהגדרות ניתוח המגמות.

עמודת המודל בדף הסקרים מציגה את אותו תרחיש שנבחר בשאר הדפים, במקום שילוב שמרני קבוע. כל עמודות הסקרים המקוריות נשמרו בנפרד. דף ההסברים מפרט מקור לעומת שחזור לעומת סימולציה, שקלול היסטורי, חסימה ובאדר–עופר, בסיס השתתפות 2022, מבחן ראשי ובדיקת רגישות, מקורות וקרדיטים.

ברירת המחדל נשארה דיוק היסטורי, ערוץ 14 כבוי, תיקון דמיון כבוי, 10,000 הדמיות והשתתפות 2022. נתוני 8 הסקרים העדכניים, 114 הסקרים ההיסטוריים, הכיול, פרופיל הדמיון והניתוחים המאומתים נשמרו. 20 אוספים מספריים, כולל כל 10,000 ההדמיות, זהים בדיוק לגרסה הקודמת. בכל הרצה נשמרים 120 מנדטים ושיוך בלעדי לכל מפלגה.

נבדקו כל ששת הדפים ב־1440, 390 ו־320 פיקסלים, ניווט במקלדת, מתגים, טעינת תרחישים וייצוא PNG/CSV/JSON. [סקירת הממשק](ui-ux-review.he.md), [בדיקת זהות התוצאות](regression.json), [אימות דפדפן](browser-qa.json), [סקירת קוד עצמאית](independent-code-review.json).
'''
(BUNDLE/'version2.he.md').write_text(note,encoding='utf-8',newline='\n')
readme=REPO/'README.md';s=readme.read_text(encoding='utf-8-sig')
section='''## גרסה 2 — ממשק ברור יותר

האתר אורגן מחדש לפי שש משימות: תמונת מצב, מפלגות וחסימה, מגמות, תרחישי מנדטים, הסקרים ושיטות והסברים. התוצאות מופיעות מוקדם יותר; ההגדרות מרוכזות ב״התאימו את התחזית״, ופירוט מפלגות ודוחות נפתח לפי צורך. דף ההסברים מציג את דרך החישוב, המקורות והמגבלות. עמודת התחזית בדף הסקרים תואמת כעת לשיטת השקלול שנבחרה.

אפשרות אות ורעש **בוטלה**. טעינת תרחיש ישן אינה מפעילה אותה מחדש, והניסוי נשמר בארכיון. נותרו שני מתגים: ערוץ 14 ודמיון בין סקרים; שניהם כבויים כברירת מחדל. נתוני המקור, הדיוק ההיסטורי ותוצאות ברירת המחדל נשמרו בדיוק. לא נוסף סקר בעדכון זה.

[השינויים והבדיקות](sources/2026-10-09-site-v2/version2.he.md) · [סקירת UI/UX](sources/2026-10-09-site-v2/ui-ux-review.he.md) · [זהות התוצאות](sources/2026-10-09-site-v2/regression.json). '''+str(passed)+''' בדיקות עברו, בנוסף לבדיקות דפדפן וייצוא. העדכונים ההיסטוריים בהמשך העמוד הם תיעוד לגרסאות קודמות; המצב הנוכחי הוא גרסה 2.

'''
assert '## גרסה 2 — ממשק ברור יותר' not in s
s=s.replace('## ברירות המחדל',section+'## ברירות המחדל',1)
s=s.replace('ערוץ 14 מוחרג ואות ורעש כבוי. אלה ערכי פתיחה','ערוץ 14 מוחרג, דמיון בין סקרים כבוי ואפשרות אות ורעש מבוטלת. אלה ערכי פתיחה',1)
s=s.replace('## מתג עצמאי: דמיון בין סקרים','## תיעוד גרסאות קודמות — ארכיון\n\nהסעיפים הבאים מתעדים את ההתנהגות בזמן הפרסום המקורי. הם אינם מגדירים את הממשק הנוכחי; בפרט, אות ורעש הוסר בגרסה 2.\n\n## מתג עצמאי: דמיון בין סקרים',1)
readme.write_text(s,encoding='utf-8',newline='\n')
attrs=REPO/'.gitattributes';s=attrs.read_text(encoding='utf-8-sig');line='/'+PREFIX+'/** -text'
if line not in s:attrs.write_text(s.rstrip()+'\n'+line+'\n',encoding='utf-8',newline='\n')
for name,digest in manifest['priorEvidence'].items():assert sha(REPO/name)==digest,name
receipt={'siteVersion':2,'dataAsOf':snapshot['dataAsOf'],'newPollCount':0,'signalNoiseRetired':True,'legacyImportProtected':True,'weightingDefault':'quality','includeChannel14Default':False,'pollCorrelationDefault':False,'sameAppId':snapshot['id'],'samePublicDestination':True,'testsPassed':passed,'exactNumericalCollections':20,'previousEvidenceFilesPreserved':len(manifest['priorEvidence']),'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'publishedHtmlSha256':sha(REPO/'index.html'),'files':[{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha(p)} for p in sorted(BUNDLE.rglob('*')) if p.is_file() and p.name!='release.json']}
write(BUNDLE/'release.json',receipt);write(ART/'publication-receipt.json',receipt)
print(json.dumps({'packagePrepared':True,'newEvidenceFiles':len(receipt['files']),'previousEvidencePreserved':receipt['previousEvidenceFilesPreserved'],'testsPassed':passed,'htmlSha256':receipt['publishedHtmlSha256']}))
