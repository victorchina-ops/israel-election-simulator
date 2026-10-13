"""Append original-publisher-verified fieldwork evidence for three new polls."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SRC='artifacts/sources/2026-10-02-ingestion/'
rows=[('c14-i24-fieldwork.json',{
 'pollId':'history_next_data_2026-10-01_current','sourcePollId':'next_data_2026-10-01','pollsterId':'next_data',
 'publicationDate':'2026-10-01','fieldworkStart':'2026-10-01','fieldworkEnd':'2026-10-01',
 'eligibleStrict':True,'includeInStrictPostClose':True,
 'sourceUrl':'https://www.c14.co.il/article/1720749','evidencePath':SRC+'c14-2026-10-01-1720749.html',
 'evidenceExtractPath':SRC+'c14-2026-10-01-source-extract.txt','sampleSize':2175,'marginOfErrorPct':None,'collectionMode':None,
 'sourceParagraph':'דיסקליימר: הסקר נערך היום, 1 באוקטובר 2026, באמצעות חברת NEXT DATA בקרב 2,175 בוגרים מכלל האוכלוסייה. ניתוח הנתונים בוצע בידי שלמה פילבר.',
 'certainty':'verified-explicit-archived-original-publisher-fieldwork-dates'}),
 ('c14-i24-fieldwork.json',{
 'pollId':'history_direct_polls_2026-10-01_current','sourcePollId':'direct_polls_2026-10-01','pollsterId':'direct_polls',
 'publicationDate':'2026-10-01','fieldworkStart':'2026-10-01','fieldworkEnd':'2026-10-01',
 'eligibleStrict':True,'includeInStrictPostClose':True,
 'sourceUrl':'https://www.i24news.tv/he/news/israel-elections-2026/polls/artc-761931ef','evidencePath':SRC+'i24-2026-10-01-761931ef.html',
 'evidenceExtractPath':SRC+'i24-2026-10-01-source-extract.txt','sampleSize':504,'marginOfErrorPct':4.3,'collectionMode':'digital system with panel',
 'sourceParagraph':'הסקר נאסף ונערך על ידי דיירקט פולס בע"מ בראשות צוריאל שרון עבור ערוץ i24NEWS, בתאריך ה-1 באוקטובר 2026, באמצעות מערכת דיגיטלית בשילוב פאנל, בקרב 504 נדגמים בוגרים (18+) המהווים מדגם מייצג של האוכלוסייה בישראל. טעות הדגימה הסטטיסטית: 4.3% ± בהסתברות של 95%.',
 'certainty':'verified-explicit-archived-original-publisher-fieldwork-dates'}),
 ('lazar-fieldwork.json',{
 'pollId':'history_lazar_2026-10-02_current','sourcePollId':'lazar_2026-10-02','pollsterId':'lazar',
 'publicationDate':'2026-10-02','fieldworkStart':'2026-09-30','fieldworkEnd':'2026-10-01','eligibleStrict':True,
 'sourceUrl':'https://www.maariv.co.il/news/elections-2026/article-1372750','evidencePath':SRC+'maariv-lazar-2026-10-02-1372750.html',
 'evidenceExtractPath':SRC+'maariv-lazar-2026-10-02-source-extract.txt','sampleSize':602,'initialSampleSize':600,'invitedSampleSize':4413,'marginOfErrorPct':4.0,
 'collectionMode':'Panel4ALL internet panel; stratified sampling then random within strata',
 'evidenceParagraph':'הסקר, שנערך ב-30 בספטמבר וב-1 באוקטובר, מהווה מדגם מייצג של כלל אוכלוסיית ישראל בני 18 ומעלה, יהודים וערבים. גודל המדגם ההתחלתי עמד על 600, ומספר המשיבים בפועל – 602. מספר המבקשים להשתתף – 4,413, וטעות הדגימה עומדת על 4%. הסקר בוצע בשיטות סטטיסטיות מקובלות - דגימת שכבות, ובתוך השכבות דגימה אקראית ובאמצעות פאנל המשיבים האינטרנטי Panel4ALL',
 'certainty':'verified-explicit-archived-original-publisher-fieldwork-dates',
 'accessNote':'Web reader failed; original publisher HTML and original embedded Infogram both retrieved by direct HTTP200.'})]
for name,row in rows:
    path=HERE/name;obj=json.loads(path.read_text(encoding='utf-8-sig'))
    assert row['pollId'] not in {r['pollId'] for r in obj['polls']}
    evidence=ROOT/row['evidencePath'];assert evidence.exists()
    row['evidenceSha256']=hashlib.sha256(evidence.read_bytes()).hexdigest()
    row['reason']='Original publisher explicitly documents actual fieldwork wholly after list closure; publication dates do not infer fieldwork.'
    obj['polls'].append(row)
    if 'auditDate' in obj:obj['auditDate']='2026-10-02'
    if 'checkedAt' in obj:obj['checkedAt']='2026-10-02'
    if 'includedCount' in obj:obj['includedCount']=sum(r.get('eligibleStrict',r.get('includeInStrictPostClose',False)) for r in obj['polls'])
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Added three original-source-verified fieldwork records.')
