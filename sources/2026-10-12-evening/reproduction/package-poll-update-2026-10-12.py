"""Package the two verified observations, fresh audits and unchanged UI at the existing destination."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT/'github-pages';ART=ROOT/'artifacts/poll-checks/2026-10-12-evening'
DAY='2026-10-12';PREFIX='sources/2026-10-12-evening'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
def copy(p,name):
 dest=REPO/PREFIX/name;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==p.read_bytes(),f'Dated evidence differs:{dest}'
 else:shutil.copy2(p,dest)
 files.append({'path':PREFIX+'/'+name,'sha256':sha(dest),'bytes':dest.stat().st_size})
def write(p,obj):p.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
checkpoint=read(ART/'before/manifest.json')
for group in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes']:
 for rel,digest in checkpoint[group].items():assert sha(ROOT/rel)==digest,rel
for name in ['ingestion-validation.json','strict-validation.json','model-comparison-validation.json']:
 assert read(ART/name)['status']=='PASS',name
assert read(ROOT/f'artifacts/poll-correlation/{DAY}/reviewed/independent-audit.json')['status']=='passed'
assert read(ROOT/f'artifacts/strict-post-close/without-channel14/{DAY}/reviewed/validation.json')['status']=='PASS'
reports=sorted((ART/'browser-local').glob('*/report.json'));assert reports
local=reports[-1];assert read(local)['status']=='passed'
tests=(ART/'test-results-final.txt').read_text(encoding='utf-8-sig')
assert re.search(r'fail\s+0(?:\r?\n|$)',tests)
testsPassed=int(re.search(r'pass\s+(\d+)',tests).group(1))
snapshot=read(ROOT/'dashboard/src/data.json');assert snapshot['dataAsOf']==DAY and snapshot['buildStatus']=='complete'
assert snapshot['features']['chatGPT'] is False
cfg={r['key']:r['value'] for r in snapshot['queries']['model_configuration']['rows']}
assert cfg['weightMode']=='quality'
assert all(cfg[k] is False for k in ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])
comparison=read(ART/'model-comparison.json')
assert comparison['status']=='passed' and comparison['onlyControlDateDiffers']
assert {p['pollsterId'] for p in comparison['pollChanges'] if p['changed']}=={'midgam_geva','next_data'}
assert len(comparison['after']['pollWeights'])==7
assert all(p['pollsterId']!='next_data' for p in comparison['after']['pollWeights'])
input={r['key']:r['value'] for r in snapshot['queries']['model_input']['rows']}
assert len(input['current']['polls'])==8 and len(input['history']['polls'])==117
compiled=(ROOT/'dashboard/dist/index.html').read_bytes()
clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',compiled,flags=re.I)
assert count==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
assert sha(ROOT/'dashboard/src/data.json').encode() in clean
for p in [REPO/'index.html',ROOT/'election-simulator.html',ROOT/'artifacts/github-pages-release/index.html']:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(clean)
shutil.copy2(ROOT/'dashboard/src/data.json',ROOT/'dashboard-snapshot.json')
for name in ['current-polls','poll-history','sources','parties','calibration','survey-documents-2026-09-14','strict-party-trends','strict-party-trends-without-channel14','poll-correlation']:
 copy(ROOT/'data'/f'{name}.json',name+'.json')
for name in ['ingestion-receipt-proof-wording-r1.json','ingestion-validation.json','strict-validation.json','model-comparison.json','model-comparison-validation.json','test-results-final.txt']:
 copy(ART/name,name)
for p in sorted((ROOT/'artifacts/strict-post-close').iterdir()):
 if p.is_file():copy(p,'trends/canonical/'+p.name)
for label,folder in [('without-channel14',ROOT/f'artifacts/strict-post-close/without-channel14/{DAY}/reviewed'),('poll-correlation',ROOT/f'artifacts/poll-correlation/{DAY}/reviewed')]:
 for p in sorted(folder.rglob('*')):
  if p.is_file():copy(p,'trends/'+label+'/'+p.relative_to(folder).as_posix())
for name in ['ingest-polls-2026-10-12-evening.py','revise-proof-wording-2026-10-12-evening.py','validate-ingestion-2026-10-12-evening.py','validate-poll-update-2026-10-12.py','build-trend-summaries-2026-10-12.py','build-strict-party-trends.py','derive-strict-trends-without-channel14.py','build-poll-correlation.py','audit-poll-correlation.py','compare-poll-update.mjs','validate-model-comparison-2026-10-12.mjs','browser-poll-update-2026-10-12.mjs','package-poll-update-2026-10-12.py']:
 copy(ROOT/'scripts'/name,'reproduction/'+name)
for name in ['analyze-strict-post-close-2026-09-28.py','audit-strict-full-series-2026-09-28.py','analyze-party-trends-strict-2026-09-28.py']:
 copy(ROOT/'artifacts'/name,'reproduction/'+name)
copy(local,'browser-local-report.json')
copy(ROOT/'scripts/readback-poll-update-2026-10-12.py','reproduction/readback-poll-update-2026-10-12.py')
visual=local.parent/'visual-review.json'
assert visual.is_file();copy(visual,'browser-local-visual-review.json')
copy(ART/'tv-primary/verification-summary.json','source-verification-summary.json')
copy(ART/'israelpolls/source-summary.json','israelpolls-source-summary.json')
assert read(ART/'social/render-checks.json')['visualInspectionCompleted'] is True
social=ROOT/'outputs/social/2026-10-12'
for p in sorted(social.iterdir()):
 if p.is_file():
  dest=REPO/'updates/2026-10-12'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copy2(p,dest)
  files.append({'path':dest.relative_to(REPO).as_posix(),'sha256':sha(dest),'bytes':dest.stat().st_size})
dest=REPO/'updates/2026-10-12/build-figure.py';shutil.copy2(ART/'social/build-figure.py',dest)
files.append({'path':dest.relative_to(REPO).as_posix(),'sha256':sha(dest),'bytes':dest.stat().st_size})
before,after=comparison['before'],comparison['after']
party=lambda id:next(p for p in after['parties'] if p['id']==id)
groups={g['id']:g['stats']['mean'] for g in after['reportingGroups']}
selected=read(ROOT/'data/strict-party-trends-without-channel14.json')
joint=next(r for r in selected['rows'] if r['partyId']=='joint')
bloc=read(ROOT/f'artifacts/strict-post-close/without-channel14/{DAY}/reviewed/party-analysis.json')
blocLabels={'coalition':'קואליציה','opposition':'אופוזיציה ללא ערביות','opposition_raam':'אופוזיציה עם רע״ם'}
blocFindings=[blocLabels[r['group']] for r in bloc['primary']['blocOverall'] if r['qValue']<.05]
partyFindings=[r['partyName'] for r in selected['rows'] if r['qValue']<.05]
heading='## שני סקרים חדשים — 12.10.2026\n\n'
section=heading+f'''נוספו שני סקרים שנאספו ופורסמו ב־12.10: חדשות12 / מדגם–מנו גבע (509 משיבים), וחדשות14 / NEXT DATA–שלמה פילבר (538 משיבים). בחדשות12 הקואליציה נשארת49 והאופוזיציה הלא־ערבית ללא הנדל נשארת54; ש״ס ועוצמה עולות במנדט, הליכוד ויהדות התורה יורדות במנדט. בערוץ14 הקואליציה יורדת63→61, והנדל–זליכה עוברים0→4. הגדרת ״שמאל46״ של ערוץ14 כוללת אותם; בהגדרות האתר הקבועות מדובר42 אופוזיציה ו־4 ללא שיוך, בנוסף13 לערביות. [מקור12](https://www.mako.co.il/news-israel-elections/2026/Article-cc91389788031a1026.htm) · [מקור14](https://www.c14.co.il/article/1735305) · [אימות ההטמעה]({PREFIX}/ingestion-validation.json).

האחוזים שפורסמו נשמרו בנפרד משחזור למודל: ב־12 וינטר1.8%, כחול לבן0.9%, נעם0.5%, הציבור החרדי0.1%; ב־14 וינטר2.9%, כחול לבן0.6%, נעם0.9%, הציבור החרדי0.6%, אח״י0.1% (מיפוי לאחרים במודל בלבד). לא פורסמו אחוזי המפלגות העוברות במקורות שנבדקו; נתונים חסרים אינם אפס ולא הועתקו מהשבוע הקודם. ב־12 כ־8% מתלבטים, עם רכיבים שסכומם8.1%; ב־14 פורסמו5%. מכנה אחוזי התמיכה עדיין אינו מאומת. הווידאו המקורי של12 לא היה נגיש; טקסט המקור והטבלה ההיסטורית נבדקו. הגרפיקה המקורית של14 נבדקה. [מקורות ומגבלות]({PREFIX}/source-verification-summary.json).

ברירת המחדל נשארה דיוק היסטורי, בסיס השתתפות2022, ללא ערוץ14, אות־רעש כבוי ודמיון־סקרים כבוי. לפיכך סקר14 נשמר במאגר, בהיסטוריה ובניתוח הכולל, וזמין במתג; הוא אינו נכנס לתחזית ברירת המחדל. בתחזית זו ממוצע הקואליציה{groups['a']:.2f}, האופוזיציה{groups['b']:.2f}, הערביות{groups['arab']:.2f}, ושאר הרשימות{groups['other']:.2f}; סכומם120. סיכויי המעבר במודל: וינטר{100*party('winter')['passProbability']:.2f}%, הנדל–זליכה{100*party('hendel')['passProbability']:.2f}%. אלו הסתברויות מותנות בהנחות המודל ולא אחוז תמיכה בסקר או הבטחה לבחירות. [השוואת תחזית לפני ואחרי]({PREFIX}/model-comparison.json).

המגמות חושבו מחדש מתוך אותו מדד של שינוי בתוך כל מכון ומשקלי הדיוק ההיסטורי. ללא14: {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים, {selected['coverage']['deltaCount']} דלתות; כלל האיסוף המאומת מתחיל לאחר סגירת הרשימות. שתי התצפיות החדשות זכאיות לניתוח הכולל, וה־14 מוחרג מהגרסה הנפרדת לפי בחירת המפרסם. חמש התצפיות שמועדי איסופן אינם מאומתים נשארות מוחרגות, כולל כאן11.10. במבחן הפרמוטציות הראשי אחרי BH, ממצאי הגושים המובהקים: {', '.join(blocFindings) or 'אין'}; ממצאי המפלגות המובהקים: {', '.join(partyFindings) or 'אין'}. למשותפתΔ={joint['weightedNetDelta']:+.2f}, q={joint['qValue']:.5f}; בדיקת החלפת כיוון סדרות הסוקרים q={joint['wholeSeriesSignFlipQ']:.5f}. מציגים כל הכרעה בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [ניתוח ברירת המחדל]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

[ציוץ](updates/2026-10-12/tweet.he.txt) · [אינפוגרפיקה](updates/2026-10-12/two-polls-one-evening.png) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json). נשמרו8 מכונים פעילים ו־117 תצפיות היסטוריות, כל המקורות, תיקון היישור בנייד ובמחשב והעיצוב הקיים.

'''
readme=REPO/'README.md';body=readme.read_text(encoding='utf-8-sig');assert heading not in body
body=body.replace('## תיקון יישור תרשים אחוז החסימה — 12.10.2026',section+'## תיקון יישור תרשים אחוז החסימה — 12.10.2026',1);readme.write_bytes(body.encode('utf-8'))
attrs=REPO/'.gitattributes';body=attrs.read_text(encoding='utf-8-sig').rstrip()+'\n'
for p in [PREFIX,'updates/2026-10-12']:
 line='/'+p+'/** -text';assert line not in body;body+=line+'\n'
attrs.write_bytes(body.encode('utf-8'))
for rel,digest in checkpoint['frozenEvidenceHashes'].items():assert sha(ROOT/rel)==digest,rel
receipt={'status':'PASS','asOf':DAY,'runId':'evening','newPollCount':2,'activePolls':8,'historyPolls':117,'eligibleFull':41,'eligibleWithout14':33,'testsPassed':testsPassed,'authorContentFilesUnchanged':len(checkpoint['authorContentHashes']),'protectedRuntimeFilesVerified':len(checkpoint['protectedRuntimeHashes']),'frozenEvidenceFilesPreserved':len(checkpoint['frozenEvidenceHashes']),'snapshotSha256':sha(ROOT/'dashboard/src/data.json'),'publishedHtmlSha256':sha(REPO/'index.html'),'featuresChatGPT':False,'defaultWeightMode':'quality','includeChannel14':False,'signalNoiseEnabled':False,'pollCorrelationEnabled':False,'socialDraftOnly':True,'files':files}
write(ART/'publication-receipt.json',receipt);write(REPO/PREFIX/'release.json',receipt)
print(json.dumps({'status':'PASS','files':len(files),'testsPassed':testsPassed,'publishedHtmlSha256':receipt['publishedHtmlSha256']}))
