"""Let the existing native label ellipsis reserve room for the percentage on320px screens."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
PROJECT=Path('C:/Users/User/Documents/ChatGPT/סקרים ושקרים')
path=PROJECT/'dashboard/src/content/dashboard/threshold-page.css'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
first=read(HERE/'repair-receipt.json')
assert sha(path)==first['afterSha256'],'CSSchangedafterinitialreview'
body=path.read_bytes();old=sha(path)
anchor=b'.threshold-page .tp-chart-logo .party-logo{flex-shrink:1;min-height:0}'
assert body.count(anchor)==1
nl=b'\r\n' if b'\r\n' in body else b'\n'
addition=nl+b'/* Allow the existing label ellipsis to reserve space for its full percentage on narrow screens. */'+nl+b'.threshold-page .tp-logo-chart-plot .bar-family-list-copy{min-width:0}'
path.write_bytes(body.replace(anchor,anchor+addition))
report={'status':'PASS','presentationDate':'2026-10-12','changedFile':first['changedFile'],'beforeSha256':old,'afterSha256':sha(path),'scope':'Only the threshold chart copy grid-item minimumwidth is reset. The existing native label ellipsis remains; full party/value aria-label, marks, controls, text and data stay intact.','protectedRuntimeEdited':False}
(HERE/'narrow-repair-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
