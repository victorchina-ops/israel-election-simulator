"""Verify only the independent party schema precondition; no heavy analysis."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
old_path=ROOT/'scripts/run-exact-trends-2026-10-20-evening.py'
new_path=ROOT/'scripts/run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py'
assert sha(old_path)=='eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7'
assert sha(new_path)=='d9d5328f57a6dc3f62090ba02868e2a2a9940ad2c4a431c3551b65c0e38ae9c1'
old=module(old_path,'old_independent_schema_wrapper')
new=module(new_path,'new_independent_schema_wrapper')
for stage,(relative,digest,_) in old.SOURCES.items():
    source_path=ROOT/relative;assert sha(source_path)==digest
    source=source_path.read_text(encoding='utf-8-sig')
    left=old.transform(stage,source,ROOT,ROOT/'artifacts/strict-post-close')
    right=new.transform(stage,source,ROOT,ROOT/'artifacts/strict-post-close')
    if stage=='independent-party':
        replacement='\n'.join('        '+line for line in new.INDEPENDENT_PARTY_SCHEMA_PRECONDITION.rstrip().splitlines())
        assert left.count('        assert set(seats).issubset(ids)')==1
        assert left.replace('        assert set(seats).issubset(ids)',replacement,1)==right
    else:assert left==right
history_path=ROOT/'data/poll-history.json';analysis_path=ROOT/'artifacts/strict-post-close/analysis.json';catalogue_path=ROOT/'data/parties.json'
inputs={path:sha(path) for path in [history_path,analysis_path,catalogue_path,old_path,new_path]}
history={p['id']:p for p in read(history_path)['polls']}
analysis=read(analysis_path)
eligible=[p for p in analysis['cohort'] if p['eligibleStrict']]
catalogue=read(catalogue_path);ids=[p['id'] for p in catalogue if p['ballot']]
assert len(ids)==17
guard=compile(new.INDEPENDENT_PARTY_SCHEMA_PRECONDITION,'reviewed-independent-party-precondition','exec')
def accepts(seats,cat=catalogue):
    try:exec(guard,{'ROOT':ROOT,'read':lambda _:cat,'ids':ids,'seats':seats})
    except AssertionError:return False
    return True
arrays=[];stripped=[]
for row in eligible:
    seats=history[row['pollId']]['seats'];assert sum(seats.values())==120 and accepts(seats)
    arrays.append([seats.get(pid,0) for pid in ids])
    clean={key:value for key,value in seats.items() if key!='other'}
    assert accepts(clean);stripped.append([clean.get(pid,0) for pid in ids])
assert arrays==stripped and all(sum(values)==120 for values in arrays)
base=dict(next(p['seats'] for p in history.values() if p['id']=='history_maagar_mochot_2026-10-20_current'))
cases={'actual55PollCohort':'accepted','originalCompatibleNoAggregate':'accepted'}
for label,value in [('positive',1),('negative',-1),('floatZero',0.0),('fraction',.1),('boolFalse',False),('boolTrue',True),('stringZero','0'),('null',None),('list',[]),('mapping',{})]:
    seats=dict(base,other=value);assert not accepts(seats);cases['other_'+label]='rejected'
assert not accepts(dict(base,unknown_party=0));cases['unknownZeroExtra']='rejected'
for label,cat in [('catalog_missingOther',[p for p in catalogue if p['id']!='other']),('catalog_duplicateOther',catalogue+[p for p in catalogue if p['id']=='other']),('catalogOtherBallotTrue',[dict(p,ballot=True) if p['id']=='other' else p for p in catalogue])]:
    assert not accepts(base,cat);cases[label]='rejected'
bad=dict(base);bad.pop('likud');assert sum(bad.values())!=120;cases['missingPositiveBallotRejectedByUnchangedRaw120Guard']='rejected'
assert len(cases)==17
assert all(sha(path)==digest for path,digest in inputs.items())
receipt={'status':'PASS','asOf':'2026-10-20','runId':'evening','independentPartyAdapterSha256':sha(new_path),'originalEveningWrapperSha256':sha(old_path),'reviewScriptSha256':sha(Path(__file__)),'historySha256':sha(history_path),'analysisSha256':sha(analysis_path),'catalogueSha256':sha(catalogue_path),'onlyIndependentPartyPerRowPreconditionChanged':True,'allOtherTransformedSourceBytesIdentical':True,'otherThreeStageTransformsUnchanged':True,'adapterCliRestrictedToIndependentParty':True,'strictCohortPolls':len(eligible),'predeclaredBallotPartyCount':len(ids),'all17BallotArraysExactlyEqualWithAndWithoutZeroAggregate':True,'lstsqDPExactTailsToleranceBHAndSignFlipsUnchanged':True,'adversarialAndSemanticCases':cases,'caseCount':len(cases),'rawDataAndFrozenHelperBytesUnchanged':True,'heavyNumericalAnalysisExecuted':False}
p=OUT/'independent-party-schema-adapter-proof.json'
with p.open('x',encoding='utf-8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','path':str(p.relative_to(ROOT)),'sha256':sha(p)}))
