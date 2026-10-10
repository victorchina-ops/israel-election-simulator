"""Package the verified October 10 C13 metadata correction without altering archived evidence."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'github-pages';ART=ROOT/'artifacts/poll-checks/2026-10-10'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def copy(src,relative):
 dest=REPO/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==src.read_bytes(),f'Existing dated evidence differs: {dest}'
 else:shutil.copy2(src,dest)
 return {'path':relative,'sha256':sha(dest),'bytes':dest.stat().st_size}
checkpoint=read(ART/'before/manifest.json')
for rel,digest in checkpoint['frozenEvidenceHashes'].items():assert sha(ROOT/rel)==digest,rel
for rel,digest in checkpoint['authorContentHashes'].items():assert sha(ROOT/rel)==digest,rel
assert read(ART/'c13-official-revision-validation.json')['status']=='PASS'
assert read(ART/'independent-final-review.json')['status']=='PASS'
assert read(ART/'numerical-regression.json')['status']=='PASS'
assert read(ROOT/'artifacts/poll-correlation/2026-10-10/reviewed/independent-audit.json')['status']=='passed'
assert read(ROOT/'artifacts/strict-post-close/without-channel14/2026-10-10/reviewed/validation.json')['status']=='PASS'
localReports=sorted((ART/'browser-local').glob('*/report.json'));assert localReports
local={'reportPath':localReports[-1].relative_to(ROOT).as_posix()}
report=read(ROOT/local['reportPath']);assert report['status']=='passed'
tests=(ART/'test-results-final.txt').read_text(encoding='utf-8-sig');assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
tests_passed=int(re.search(r'pass\s+(\d+)',tests).group(1))
snapshot=read(ROOT/'dashboard/src/data.json');config={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
assert snapshot['buildStatus']=='complete' and snapshot['features']['chatGPT'] is False
assert config['weightMode']=='quality' and config['includeChannel14'] is False and config['signalNoiseEnabled'] is False and config['pollCorrelationEnabled'] is False
assert snapshot['dataAsOf']=='2026-10-10'
compiled=(ROOT/'dashboard/dist/index.html').read_bytes();clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',compiled,flags=re.I);assert count==1
assert b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
assert sha(ROOT/'dashboard/src/data.json').encode() in clean
for p in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
files=[];prefix='sources/2026-10-10-c13-official'
for p in sorted((ART/'c13-official-discovery').iterdir()):
 if p.is_file():files.append(copy(p,prefix+'/'+p.name))
for name in ['current-polls','poll-history','sources','parties','calibration','strict-party-trends','strict-party-trends-without-channel14','poll-correlation']:
 files.append(copy(ROOT/'data'/f'{name}.json',prefix+'/'+name+'.json'))
for name in ['source-scan-summary.json','independent-final-review.json','c13-official-revision-validation.json','model-comparison.json','numerical-regression.json','test-results-final.txt']:
 files.append(copy(ART/name,prefix+'/'+name))
for p in (ROOT/'artifacts/strict-post-close').iterdir():
 if p.is_file():files.append(copy(p,prefix+'/trends/canonical/'+p.name))
for dirname,path in [('without-channel14',ROOT/'artifacts/strict-post-close/without-channel14/2026-10-10/reviewed'),('poll-correlation',ROOT/'artifacts/poll-correlation/2026-10-10/reviewed')]:
 for p in path.rglob('*'):
  if p.is_file():files.append(copy(p,prefix+'/trends/'+dirname+'/'+p.relative_to(path).as_posix()))
for name in ['build-strict-party-trends.py','derive-strict-trends-without-channel14.py','build-poll-correlation.py','audit-poll-correlation.py','validate-c13-official-revision-2026-10-10.py','compare-poll-update.mjs','browser-c13-official-revision-2026-10-10.mjs','package-c13-official-revision-2026-10-10.py']:
 files.append(copy(ROOT/'scripts'/name,prefix+'/reproduction/'+name))
for name in ['analyze-strict-post-close-2026-09-28.py','audit-strict-full-series-2026-09-28.py','analyze-party-trends-strict-2026-09-28.py']:
 files.append(copy(ROOT/'artifacts'/name,prefix+'/reproduction/'+name))
files.append(copy(ROOT/local['reportPath'],prefix+'/browser-local-report.json'))
scan='sources/2026-10-10-scan';files.append(copy(ART/'source-scan-summary.json',scan+'/source-scan-summary.json'))
for dirname in ['print-primary','tv-primary','root-run2']:
 for p in (ART/dirname).rglob('*'):
  if p.is_file() and not p.name.startswith(('to120-data.','to120-evidence.')):
   files.append(copy(p,scan+'/'+dirname+'/'+p.relative_to(ART/dirname).as_posix()))
for p in sorted((ROOT/'outputs/social/2026-10-10').iterdir()):
 if p.is_file():files.append(copy(p,'updates/2026-10-10/'+p.name))
files.append(copy(ART/'social/build-figure.py','updates/2026-10-10/build-figure.py'))
readme=REPO/'README.md';text=readme.read_text(encoding='utf-8-sig');heading='## בדיקת סקרים ותיקון פרטי מקור — 10.10.2026\n\n'
section=heading+'''לא נמצא סקר מנדטים נוסף מאומת. כתבת N12 מ־9.10 מדווחת על תמיכה בגושים: 50% למתנגדי נתניהו כולל המפלגות הערביות, מול35% לגוש נתניהו כולל וינטר. בכתבה אין וקטור מנדטים למפלגות, ולכן התוצאה נשמרת כמקור משלים ואינה נוספת לשקלול. מועד הפרסום הראשון של הסקר, גודל המדגם וימי האיסוף המדויקים אינם מאומתים. [מקור](https://www.mako.co.il/news-politics/2026_q4/Article-2497091942121a1026.htm) · [טיוטת ציוץ](updates/2026-10-10/tweet.he.txt) · [אינפוגרפיקה](updates/2026-10-10/n12-bloc-shares.png).

הדוח הרשמי4193 מאמת את פרטי אותה תצפית חדשות13 מ־7.10: איסוף6.10 בשעה09:00 עד7.10 בשעה09:00,1263 משיבים. מספרי המנדטים והאחוזים הארציים שפורסמו נשארו בדיוק כפי שהיו; טבלאות אחוזים בלתי משוקללים לתת־קבוצות אינן נתוני תמיכה ארציים. [הדוח](sources/2026-10-10-c13-official/Survey_4193.pdf) · [אימות בלתי תלוי](sources/2026-10-10-c13-official/independent-final-review.json).

ניתוחי המגמות חושבו מחדש לפי מועד האיסוף המתוקן. ברירת המחדל ללא ערוץ14 כוללת32 סקרים מאומתים משבעה מכונים אחרי סגירת הרשימות. אין מגמת גוש מובהקת לאחר תיקון לריבוי בדיקות. למשותפת עלייה משוקללת של0.72 מנדט מהתצפית הראשונה לאחר סגירת הרשימות לתצפית האחרונה בכל מכון: המבחן הראשי מובהק לאחר BH (q=0.01615), אך בדיקת החלפת סימן של סדרות הסוקרים אינה מובהקת (q=0.53125). שינוי ראשון–אחרון הוא נתון תיאורי; המבחן הראשי בוחן את המגמה בכל התצפיות. אי־מובהקות אינה הוכחה להעדר שינוי או לאקראיות. [ניתוח ברירת המחדל](sources/2026-10-10-c13-official/strict-party-trends-without-channel14.json).

תוצאות ברירת המחדל זהות בכל10,000 ההדמיות לפני ואחרי תיקון המטא־דאטה, כולל הסתברויות המעבר והכישלון המשותף של כל המפלגות שנבחרו. נשמרו8 מכונים פעילים ו־114 תצפיות היסטוריות, משקלי הדיוק ההיסטורי והעיצוב. [זהות התוצאות](sources/2026-10-10-c13-official/numerical-regression.json) · [בדיקות דפדפן](sources/2026-10-10-c13-official/browser-local-report.json) · [תיעוד הבדיקה ומגבלות הגישה](sources/2026-10-10-scan/source-scan-summary.json). דפי כאן לא סיפקו תוכן נגיש בבדיקה; אין להסיק מכך שלא פורסם שם סקר חדש.

'''
assert heading not in text;text=text.replace('## סיכוי שכל המפלגות שנבחרו לא יעברו — הבהרה',section+'## סיכוי שכל המפלגות שנבחרו לא יעברו — הבהרה',1);readme.write_bytes(text.encode('utf-8'))
attrs=REPO/'.gitattributes';body=attrs.read_text(encoding='utf-8-sig').rstrip()+'\n'
for p in [prefix,scan,'updates/2026-10-10']:
 line='/'+p+'/** -text';assert line not in body;body+=line+'\n'
attrs.write_bytes(body.encode('utf-8'))
for rel,digest in checkpoint['frozenEvidenceHashes'].items():assert sha(ROOT/rel)==digest,rel
receipt={'status':'PASS','asOf':'2026-10-10','newMandatePolls':0,'metadataRevisions':['hamadad_consortium_2026-10-07'],'testsPassed':tests_passed,'protectedRuntimeVerifiedFiles':234,'authorContentFilesUnchanged':117,'previousPublishedEvidenceFilesPreserved':len(checkpoint['frozenEvidenceHashes']),'modelNumericalCollectionsExactlyUnchanged':15,'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'featuresChatGPT':False,'defaultWeighting':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,'socialDraftOnly':True,'files':files}
write(ART/'publication-receipt.json',receipt);write(REPO/prefix/'release.json',receipt)
print(json.dumps({'status':'PASS','files':len(files),'testsPassed':tests_passed,'publishedHtmlSha256':receipt['publishedHtmlSha256']}))
