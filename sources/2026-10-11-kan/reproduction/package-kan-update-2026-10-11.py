"""Package the reviewed Kan release; keep private research and frozen evidence local."""
from pathlib import Path
import hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT/'github-pages'
ART=ROOT/'artifacts/poll-checks/2026-10-11'
DAY='2026-10-11'
PREFIX='sources/2026-10-11-kan'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def copy(src,relative):
 dest=REPO/relative
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==src.read_bytes(),f'Existing dated evidence differs: {dest}'
 else:shutil.copy2(src,dest)
 return {'path':relative,'sha256':sha(dest),'bytes':dest.stat().st_size}
checkpoint=read(ART/'before/manifest.json')
for category in ['frozenEvidenceHashes','authorContentHashes']:
 for rel,digest in checkpoint[category].items():assert sha(ROOT/rel)==digest,rel
for filename in ['ingestion-validation.json','ingestion-validation-model-only-r1.json','strict-validation.json','independent-final-review.json','model-comparison-validation.json']:
 assert read(ART/filename)['status']=='PASS',filename
assert read(ROOT/f'artifacts/poll-correlation/{DAY}/reviewed/independent-audit.json')['status']=='passed'
assert read(ROOT/f'artifacts/strict-post-close/without-channel14/{DAY}/reviewed/validation.json')['status']=='PASS'
localReports=sorted((ART/'browser-local').glob('*/report.json'))
assert localReports
localPath=localReports[-1]
assert read(localPath)['status']=='passed'
tests=(ART/'test-results-final.txt').read_text(encoding='utf-8-sig')
assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
testsPassed=int(re.search(r'pass\s+(\d+)',tests).group(1))
comparison=read(ART/'model-comparison.json')
assert comparison['status']=='passed' and comparison['onlyControlDateDiffers']
assert [p['pollsterId'] for p in comparison['pollChanges'] if p['changed']]==['kantar']
snapshot=read(ROOT/'dashboard/src/data.json')
cfg={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
assert snapshot['buildStatus']=='complete' and snapshot['features']['chatGPT'] is False
assert cfg['weightMode']=='quality'
assert all(cfg[k] is False for k in ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])
assert snapshot['dataAsOf']==DAY
input={r['key']:r['value'] for r in snapshot['queries']['model_input']['rows']}
assert len(input['current']['polls'])==8 and len(input['history']['polls'])==115
compiled=(ROOT/'dashboard/dist/index.html').read_bytes()
clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',compiled,flags=re.I)
assert count==1
assert b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
assert sha(ROOT/'dashboard/src/data.json').encode() in clean
for p in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
files=[]
for name in ['current-polls','poll-history','sources','parties','calibration','strict-party-trends','strict-party-trends-without-channel14','poll-correlation','survey-documents-2026-09-14']:
 files.append(copy(ROOT/'data'/f'{name}.json',PREFIX+'/'+name+'.json'))
for name in ['ingestion-validation.json','ingestion-validation-model-only-r1.json','ingestion-receipt-model-only-r1.json','strict-validation.json','independent-final-review.json','model-comparison.json','model-comparison-validation.json','test-results-final.txt']:
 files.append(copy(ART/name,PREFIX+'/'+name))
for p in sorted((ROOT/'artifacts/strict-post-close').iterdir()):
 if p.is_file():files.append(copy(p,PREFIX+'/trends/canonical/'+p.name))
for label,folder in [('without-channel14',ROOT/f'artifacts/strict-post-close/without-channel14/{DAY}/reviewed'),('poll-correlation',ROOT/f'artifacts/poll-correlation/{DAY}/reviewed')]:
 for p in sorted(folder.rglob('*')):
  if p.is_file():files.append(copy(p,PREFIX+'/trends/'+label+'/'+p.relative_to(folder).as_posix()))
for name in ['ingest-kan-2026-10-11.py','validate-kan-2026-10-11.py','revise-kan-model-only-2026-10-11.py','validate-kan-update-2026-10-11.py','build-trend-summaries-2026-10-11.py','build-strict-party-trends.py','derive-strict-trends-without-channel14.py','build-poll-correlation.py','audit-poll-correlation.py','compare-poll-update.mjs','validate-model-comparison-2026-10-11.mjs','browser-kan-update-2026-10-11.mjs','package-kan-update-2026-10-11.py']:
 files.append(copy(ROOT/'scripts'/name,PREFIX+'/reproduction/'+name))
for name in ['analyze-strict-post-close-2026-09-28.py','audit-strict-full-series-2026-09-28.py','analyze-party-trends-strict-2026-09-28.py']:
 files.append(copy(ROOT/'artifacts'/name,PREFIX+'/reproduction/'+name))
files.append(copy(localPath,PREFIX+'/browser-local-report.json'))
scan='sources/2026-10-11-scan'
for p in sorted((ART/'source-scan').rglob('*')):
 if p.is_file() and not p.name.startswith(('to120-data.','to120-evidence.')):
  files.append(copy(p,scan+'/'+p.relative_to(ART/'source-scan').as_posix()))
social=ROOT/'outputs/social/2026-10-11'
assert read(ART/'social/render-checks.json')['visualInspectionCompleted'] is True
for p in sorted(social.iterdir()):
 if p.is_file():files.append(copy(p,'updates/2026-10-11/'+p.name))
files.append(copy(ART/'social/build-figure.py','updates/2026-10-11/build-figure.py'))
fmt=lambda value:f'{value:.2f}'
before,after=comparison['before'],comparison['after']
selected=read(ROOT/'data/strict-party-trends-without-channel14.json')
joint=next(r for r in selected['rows'] if r['partyId']=='joint')
party=lambda id:next(p for p in after['parties'] if p['id']==id)
group=lambda record,id:next(p for p in record['reportingGroups'] if p['id']==id)
heading='## סקר כאן חדש — 11.10.2026\n\n'
section=heading+f'''נוסף סקר כאן / קנטאר — דודי חסיד מ־11.10.2026,554 משיבים: גוש נתניהו53 כולל וינטר, אופוזיציה50 ללא ערביות, ערביות13 והנדל–זליכה4. וינטר חזר ל־4 מנדטים לאחר0 בסקר כאן מ־4.10. מול סקר קנטאר / ישראל היום מ־8.10, שהיה הפעיל במודל, וינטר עולה מ־0 ל־4; הליכוד, ביחד, הציונות הדתית והנדל–זליכה יורדים כל אחד במנדט. [גרפיקת המקור החוזרת](https://x.com/IsraelPolls/status/2109338230902693893) · [טבלת המקור](https://x.com/IsraelPolls/status/2109340303660552420) · [אימות ההטמעה]({PREFIX}/ingestion-validation.json).

הגרפיקה המשודרת והטבלה של IsraelPolls נפתחו ונבדקו. דפי כאן ומדוריו החזירו403; הפרסום המקורי המלא, ימי האיסוף, שיטת הדגימה וטעות הדגימה אינם מאומתים ונשארים חסרים. אחוז התמיכה המדויק בוינטר לא פורסם במקורות שנבדקו. נשמרו כחול לבן0.9%, הציבור החרדי0.9%, צבע שחור0.7% ואח״י0.5%; שתי האחרונות נשמרות בשמותיהן, ו־1.2% לרכיב אחרים הוא סכום מתועד לצורכי המודל. אין העתקת ערכים חסרים מסקר קודם. כתבת מעריב המצטטת את כאן אינה סקר נוסף. [מגבלות ואסמכתאות]({scan}/summary.json).

התחזית חושבה באותן הגדרות לפני ואחרי:10,000 הדמיות, שקלול לפי דיוק היסטורי, ללא ערוץ14, בסיס השתתפות2022, מפלגות ערביות והנדל–זליכה מחוץ לשני הגושים. סיכויי מעבר החסימה במודל: וינטר{fmt(100*party('winter')['passProbability'])}%, הנדל–זליכה{fmt(100*party('hendel')['passProbability'])}%. אלה תוצאות מותנות של המודל, לא אחוז תמיכה שפורסם ולא תחזית ודאית לבחירות. נשמרו8 מכונים פעילים ו־115 תצפיות היסטוריות; סקר כאן החדש מחליף רק את הסקר הפעיל של קנטאר. [השוואת המודל]({PREFIX}/model-comparison.json).

מבחן המגמות המחמיר ממשיך לכלול{selected['coverage']['pollCount']} סקרים משבעה מכונים ללא ערוץ14, שכל איסופם אומת אחרי סגירת הרשימות. סקר כאן החדש מוצג בתחזית ובהיסטוריה, אך מוחרג ממבחן זה עד אימות ימי האיסוף. תוצאות המובהקות נשארו זהות: אין מגמת גוש מובהקת אחרי BH; למשותפת שינוי משוקלל ראשון–אחרון{joint['weightedNetDelta']:+.2f} מנדט, מובהק במבחן פרמוטציות הזמן (q={joint['qValue']:.5f}), ולא מובהק בבדיקת החלפת כיוון סדרות הסוקרים (q={joint['wholeSeriesSignFlipQ']:.5f}). הבדיקה הנוספת מבוססת על שבעה מכונים ולכן כוחה מוגבל. אין להסיק מאי־מובהקות שהשינוי אקראי או שאינו קיים. [בדיקות המגמות]({PREFIX}/strict-validation.json).

[טיוטת ציוץ](updates/2026-10-11/tweet.he.txt) · [אינפוגרפיקה](updates/2026-10-11/threshold-chances.png) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json).

'''
readme=REPO/'README.md';body=readme.read_text(encoding='utf-8-sig')
assert heading not in body
body=body.replace('## בדיקת סקרים ותיקון פרטי מקור — 10.10.2026',section+'## בדיקת סקרים ותיקון פרטי מקור — 10.10.2026',1)
readme.write_bytes(body.encode('utf-8'))
attrs=REPO/'.gitattributes';body=attrs.read_text(encoding='utf-8-sig').rstrip()+'\n'
for prefix in [PREFIX,scan,'updates/2026-10-11']:
 line='/'+prefix+'/** -text';assert line not in body;body+=line+'\n'
attrs.write_bytes(body.encode('utf-8'))
for category in ['frozenEvidenceHashes','authorContentHashes']:
 for rel,digest in checkpoint[category].items():assert sha(ROOT/rel)==digest,rel
receipt={'status':'PASS','asOf':DAY,'newMandatePolls':1,'pollId':'kantar_2026-10-11','activePollCount':8,'historyPollCount':115,'strictNewPollEligible':False,'testsPassed':testsPassed,'authorContentFilesUnchanged':len(checkpoint['authorContentHashes']),'previousPublishedEvidenceFilesPreserved':len(checkpoint['frozenEvidenceHashes']),'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'compiledHtmlSha256':sha(ROOT/'dashboard/dist/index.html'),'publishedHtmlSha256':sha(REPO/'index.html'),'featuresChatGPT':False,'defaultWeighting':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,'privateGileadResearchPublished':False,'socialDraftOnly':True,'files':files}
write(ART/'publication-receipt.json',receipt)
write(REPO/PREFIX/'release.json',receipt)
print(json.dumps({'status':'PASS','files':len(files),'testsPassed':testsPassed,'publishedHtmlSha256':receipt['publishedHtmlSha256']}))
