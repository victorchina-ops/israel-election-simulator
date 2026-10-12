"""Scoped authored CSS repair; source chart/runtime and all data remain unchanged."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
PROJECT=Path('C:/Users/User/Documents/ChatGPT/סקרים ושקרים')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read(HERE/'before/manifest.json')
relative='dashboard/src/content/dashboard/threshold-page.css'
target=PROJECT/relative
assert sha(target)==manifest['files'][relative],'Source changed since inspected checkpoint'
old=target.read_bytes()
needle=b'.threshold-page .tp-chart-logos{display:grid;padding-block:8px;min-height:0}'
replacement=b'.threshold-page .tp-chart-logos{display:grid;padding-block:8px;min-height:0;contain:size}'
assert old.count(needle)==1
body=old.replace(needle,replacement)
anchor=b'@media(max-width:600px){.threshold-page .tp-logo-chart{grid-template-columns:74px minmax(0,1fr);gap:6px}.threshold-page .tp-chart-logo .party-logo{width:50px;height:24px;flex:0 0 24px}}'
assert body.count(anchor)==1
newline=b'\r\n' if b'\r\n' in old else b'\n'
addition=newline+b'/* Let the native chart determine row height; retain logo width and shrink only when needed. */'+newline+b'.threshold-page .tp-chart-logo .party-logo{flex-shrink:1;min-height:0}'
body=body.replace(anchor,anchor+addition)
for rel,digest in manifest['files'].items():assert sha(PROJECT/rel)==digest,rel
for rel,digest in manifest['frozenPublicEvidenceHashes'].items():assert sha(PROJECT/rel)==digest,rel
target.write_bytes(body)
for rel,digest in manifest['authorContentHashes'].items():
 if rel!=relative:assert sha(PROJECT/rel)==digest,rel
report={'status':'PASS','changedFile':relative,'beforeSha256':hashlib.sha256(old).hexdigest(),'afterSha256':sha(target),'repair':'Size containment stops the logo rail enlarging the parent chart; flex shrink retains native row centers and existing mobile basis. All native marks and chart APIs unchanged.','allPollDataAndSnapshotUnchanged':True,'allOtherAuthorContentUnchanged':True,'protectedRuntimeEdited':False}
(HERE/'repair-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
