"""Prepare a dated ingester from the unchanged16Oct reviewed implementation."""
from pathlib import Path
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-19'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=ROOT/'scripts/ingest-polls-2026-10-16-maariv.py'
    checkpoint=read(ART/'before/manifest.json')
    assert sha(old)==checkpoint['files'][old.relative_to(ROOT).as_posix()]
    plan=read(ART/'source-plan.json')
    assert plan['asOf']=='2026-10-19' and plan['status']=='reviewed'
    old_ids={'kantar':'kantar_2026-10-15','next_data':'next_data_2026-10-14','direct_polls':'direct_polls_2026-10-13'}
    audit_paths={'kantar':'artifacts/strict-post-close/n12-kan-c13-fieldwork.json','next_data':'artifacts/strict-post-close/c14-i24-fieldwork.json','direct_polls':'artifacts/strict-post-close/c14-i24-fieldwork.json'}
    assert {p['pollsterId'] for p in plan['polls']}==set(old_ids)
    expected={}
    for spec in plan['polls']:
        candidate=ROOT/spec['candidatePath'];assert sha(candidate)==spec['candidateSha256']
        poll=read(candidate);pid=poll['pollsterId'];assert poll['replacesPollId']==old_ids[pid]
        expected[pid]={'folder':spec['folder'],'oldId':old_ids[pid],'oldDate':old_ids[pid][-10:],'date':poll['date'],'audit':audit_paths[pid]}
    code=old.read_text(encoding='utf-8')
    code=code.replace('2026-10-16-maariv','2026-10-19')
    code=code.replace('DAY = "2026-10-16"','DAY = "2026-10-19"')
    code=code.replace('BASELINE = "2026-10-15"','BASELINE = "2026-10-16"')
    code,count=re.subn(r'EXPECTED = \{.*?\nREGISTERS =', 'EXPECTED = '+repr(expected)+'\nREGISTERS =',code,flags=re.S)
    assert count==1
    code=code.replace('== 124','== 125').replace('124+len(plan["polls"])','125+len(plan["polls"])')
    code=code.replace('"הוחלף בסקר 16.10; נשמר בהיסטוריה"','f"הוחלף בסקר {poll[\'date\']}; נשמר בהיסטוריה"')
    code=code.replace('"הוחלף בסקר שפורסם ב־16.10.2026; נשמר בהיסטוריה."','f"הוחלף בסקר שפורסם ב־{poll[\'date\']}; נשמר בהיסטוריה."')
    code=code.replace('" — 16.10.2026"','" — "+poll["date"]')
    old_start=code.index('    note = ("עדכון ב־16.10.2026:')
    old_end=code.index('    current.update(',old_start)
    code=code[:old_start]+'''    note = ("עדכון מ־19.10.2026: נוספו סקרי כאן, ערוץ 14 ו־i24. " + details +
        f" שמונה מכונים פעילים ו־{len(history['polls'])} סקרים בהיסטוריה. כל הסקרים הקודמים נשמרו; " +
        "שדות חסרים אינם אפס. תאריך הפרסום נפרד מתאריך האיסוף. ערוץ 14 מוחרג כברירת מחדל מהשקלול.")
'''+code[old_end:]
    code=code.replace('version="2026-10-16.maariv-v1"','version="2026-10-19.v1"')
    code=code.replace('"""Ingest the verified October 16 Lazar/Maariv observation in a new dated run.','"""Ingest three reviewed observations in the19Oct audit, preserving publication and fieldwork dates.')
    code=code.replace('Requires an immutable reviewed source plan and unchanged completed October 15 Israel Hayom checkpoint.','Requires the immutable reviewed19Oct source plan and unchanged completed16Oct checkpoint.')
    compile(code,'ingest-polls-2026-10-19.py','exec')
    target=ROOT/'scripts/ingest-polls-2026-10-19.py'
    if target.exists():assert target.read_text(encoding='utf-8')==code
    else:target.write_text(code,encoding='utf-8')
    print(json.dumps({'status':'PASS','sourcePlanSha256':sha(ART/'source-plan.json'),'ingesterSha256':sha(target),'expected':expected},ensure_ascii=False))

if __name__=='__main__':main()
