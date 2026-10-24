"""Materialize fresh reviewed24Oct operational reconciliations; no counter runs."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-24'
BOUND=ROOT/'artifacts/poll-checks'/DAY/'numeric-boundaries'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['bloc','party'],required=True)
    parser.add_argument('--identity',required=True)
    args=parser.parse_args()
    gate=read(BOUND/'operational-reconciliation-r1/independent-source-review.json')
    assert gate['status']=='PASS_SOURCE_GATE' and gate['asOf']==DAY
    self_path=Path(__file__).resolve()
    assert gate['adaptedFiles'][self_path.relative_to(ROOT).as_posix()]==sha(self_path)
    archived=BOUND/'operational-reconciliation-r1'/self_path.name
    assert sha(archived)==sha(self_path)
    relative='scripts/verify-operational-tail-reconciliation-2026-10-24-r1.py'
    assert gate['adaptedFiles'][relative]==sha(ROOT/relative)
    spec=importlib.util.spec_from_file_location('_fresh24_operational_verifier',ROOT/relative)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    result=helper.verify(args.kind,args.identity)
    target=BOUND/(args.kind+'-'+args.identity+'-operational-r1.json')
    assert not target.exists(),('Preserve dated evidence',str(target))
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','validationKind':helper.KIND,'path':target.relative_to(ROOT).as_posix(),
        'sha256':sha(target),'commonAdditionThresholdMatchesPrimary':result['commonAdditionThresholdMatchesPrimary'],
        'numericalCountersExecuted':False}))


if __name__=='__main__':main()
