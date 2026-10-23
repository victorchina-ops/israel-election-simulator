"""Render actual23Oct full/default summaries after validated numerical outputs.

Only dated workflow locations/pins and explicitly listed receipt routing change.
The21Oct opposition predicate-r1 exception is not inherited.
--check-source compiles without importing/executing numerical implementations.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-23'
ORIGINAL='scripts/build-trend-summaries-2026-10-21.py'
REPLACEMENTS=[('2026-10-21', '2026-10-23', 2)]

def adapted():
    path=ROOT/ORIGINAL
    manifest=json.loads((ART/'before/manifest.json').read_text(encoding='utf-8-sig'))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==manifest['files'][ORIGINAL],('Frozen21Oct workflow source changed',ORIGINAL)
    source=path.read_text(encoding='utf-8-sig')
    for old,new,count in REPLACEMENTS:
        assert source.count(old)==count,(ORIGINAL,old)
        source=source.replace(old,new)
    compile(source,str(path),'exec')
    return path,digest,source

def main():
    path,digest,source=adapted()
    if '--check-source' in sys.argv:
        assert sys.argv[1:]==['--check-source']
        result={'status':'PASS','asOf':'2026-10-23','mode':'compile-dated-workflow-only',
            'original':ORIGINAL,'originalSha256':digest,'replacements':REPLACEMENTS,
            'adaptedSourceSha256':hashlib.sha256(source.encode()).hexdigest(),
            'wrapperSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'canonicalMutation':False,'numericalCountersExecuted':False,
            'priorDatedPredicateExceptionInherited':False}
        target=ART/'numeric-compatibility'/('build-trend-summaries-2026-10-23-source-adaptation.json')
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
        print(json.dumps(result,ensure_ascii=False))
        return
    namespace={'__name__':'_dated23_workflow','__file__':str(Path(__file__).resolve())}
    exec(compile(source,str(path),'exec'),namespace)
    namespace['main']()

if __name__=='__main__':main()
