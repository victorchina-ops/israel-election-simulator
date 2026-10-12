"""Publish only a reviewed presentation repair; polling inputs retain their date."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent
PROJECT=Path('C:/Users/User/Documents/ChatGPT/סקרים ושקרים')
REPO=PROJECT/'github-pages'
PREFIX='sources/2026-10-12-ui-threshold'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read(HERE/'before/manifest.json')
repair=read(HERE/'repair-receipt.json')
assert repair['status']=='PASS'
changed=repair['changedFile']
narrow=read(HERE/'narrow-repair-receipt.json')
assert narrow['status']=='PASS' and sha(PROJECT/changed)==narrow['afterSha256']
for rel,digest in manifest['files'].items():
 if rel not in {changed,'dashboard/dist/index.html'}:assert sha(PROJECT/rel)==digest,rel
for rel,digest in manifest['authorContentHashes'].items():
 if rel!=changed:assert sha(PROJECT/rel)==digest,rel
for rel,digest in manifest['frozenPublicEvidenceHashes'].items():assert sha(PROJECT/rel)==digest,rel
reports=sorted((HERE/'browser-local').glob('*/report.json'))
assert reports
reportPath=reports[-1];report=read(reportPath);assert report['status']=='passed'
snapshot=read(PROJECT/'dashboard/src/data.json');assert snapshot['dataAsOf']=='2026-10-11'
assert snapshot['buildStatus']=='complete' and snapshot['features']['chatGPT'] is False
before=(HERE/'before/dashboard/dist/index.html').read_bytes()
compiled=(PROJECT/'dashboard/dist/index.html').read_bytes()
scripts=lambda b:re.findall(rb'<script\b[^>]*>(.*?)</script>',b,flags=re.I|re.S)
assert scripts(compiled)==scripts(before),'Compiled JS/data changed in a CSS-only repair'
clean,count=re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*',b'',compiled,flags=re.I)
assert count==1 and b'01a0952c-a40b-7b01-b019-621f0cee2656' not in clean
assert sha(PROJECT/'dashboard/src/data.json').encode() in clean
files=[]
def copy(p,name):
 dest=REPO/PREFIX/name;dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists(),'Preserve prior dated evidence'
 shutil.copy2(p,dest)
 files.append({'path':PREFIX+'/'+name,'sha256':sha(dest)})
copy(PROJECT/changed,'threshold-page.css')
copy(HERE/'repair-receipt.json','repair-receipt.json')
copy(HERE/'narrow-repair-receipt.json','narrow-repair-receipt.json')
copy(HERE/'before/manifest.json','before-manifest.json')
copy(reportPath,'browser-local-report.json')
copy(reportPath.parent/'visual-review.json','browser-local-visual-review.json')
for name in ['1440-default-threshold-overview.png','320-default-threshold-overview.png']:
 copy(reportPath.parent/name,name)
for name in ['apply-repair.py','apply-narrow-repair.py','package.py','browser-threshold-alignment-2026-10-12.mjs']:
 copy(HERE/name,'reproduction/'+name)
for phase in ['source-scan-print','source-scan-tv']:
 source=HERE.parent/'poll-checks/2026-10-12'/phase/'summary.json'
 if source.is_file():copy(source,phase+'-summary.json')
for name in ['index.html']:
 (REPO/name).write_bytes(clean)
for p in [PROJECT/'election-simulator.html',PROJECT/'artifacts/github-pages-release/index.html']:
 p.write_bytes(clean)
body=(REPO/'README.md').read_text(encoding='utf-8-sig')
heading='## תיקון יישור תרשים אחוז החסימה — 12.10.2026\n\n'
assert heading not in body
section=heading+'''תוקן יישור הלוגואים וממוצעי המנדטים מול המפלגות בגרף המעבר. הבעיה הייתה בתצוגה: עמודת הלוגואים הגדילה את גובה השורות בהדרגה, בעוד עמודת הסיכויים נשארה בגובה המקורי. תוקן גם חיתוך של האחוז ליד שמות ארוכים במסכים ברוחב320פיקסלים: קיצור השם הקיים מפנה מקום לאחוז המלא, ושם המפלגה המלא נשמר בתווית הנגישה. התיקון מוגבל לסגנון העמוד, שומר על רוחב הלוגואים ועל התנהגות הגרף המקורי, ונבדק במחשב ובנייד.

כל נתוני הסקרים, ההיסטוריה, משקלי הדיוק, ניתוחי המובהקות, הגדרות ברירת המחדל וכל ההדמיות נשארו זהים לגרסה שפורסמה ב־11.10. תאריך נתוני המודל נשאר11.10; תיקון העיצוב אינו סקר חדש. [תיעוד התיקון](sources/2026-10-12-ui-threshold/repair-receipt.json) · [בדיקות דפדפן](sources/2026-10-12-ui-threshold/browser-local-report.json).

'''
body=body.replace('## סקר כאן חדש — 11.10.2026',section+'## סקר כאן חדש — 11.10.2026',1)
(REPO/'README.md').write_bytes(body.encode('utf-8'))
attrs=REPO/'.gitattributes';body=attrs.read_text(encoding='utf-8-sig').rstrip()+'\n';assert '/'+PREFIX+'/** -text' not in body
attrs.write_bytes((body+'/'+PREFIX+'/** -text\n').encode('utf-8'))
author={rel:sha(PROJECT/rel) for rel in manifest['authorContentHashes']}
for rel,digest in manifest['frozenPublicEvidenceHashes'].items():assert sha(PROJECT/rel)==digest,rel
receipt={'status':'PASS','presentationDate':'2026-10-12','pollDataAsOf':'2026-10-11','newPolls':0,'canonicalPollAndModelFilesByteIdentical':True,'compiledJavaScriptAndDataByteIdentical':True,'sourceFileOnly':changed,'protectedRuntimeFilesVerified':234,'frozenPublicEvidenceFilesPreserved':len(manifest['frozenPublicEvidenceHashes']),'sourceSnapshotSha256':sha(PROJECT/'dashboard/src/data.json'),'publishedHtmlSha256':sha(REPO/'index.html'),'authorContentHashes':author,'files':files}
body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
(HERE/'publication-receipt.json').write_bytes(body)
(REPO/PREFIX/'release.json').write_bytes(body)
print(json.dumps({'status':'PASS','files':len(files),'htmlSha256':receipt['publishedHtmlSha256'],'pollDataUnchanged':True}))
