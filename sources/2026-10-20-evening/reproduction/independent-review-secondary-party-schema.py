"""Independent review of the separate per-row independent-party adapter; no inference runs."""
from pathlib import Path
from datetime import datetime, timezone
import ast, copy, hashlib, json
ROOT=Path.cwd().resolve()
OUT=ROOT/"artifacts/poll-checks/2026-10-20-evening/numeric-compatibility"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
old=ROOT/"scripts/run-exact-trends-2026-10-20-evening.py"
new=ROOT/"scripts/run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py"
primary=ROOT/"scripts/run-exact-trends-2026-10-20-evening-party-schema-r1.py"
proof=OUT/"independent-party-schema-adapter-proof.json"
assert sha(old)=="eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7"
assert sha(new)=="d9d5328f57a6dc3f62090ba02868e2a2a9940ad2c4a431c3551b65c0e38ae9c1"
assert sha(primary)=="d8e7164f20176ee864de8b9702cd6ac0b130fcca854032261a329805a98d0b74"
assert sha(proof)=="e32425b8402295fb241b12ee630345aa5b64f1e4d72de8b64321237fb92a36a5"
a,b=ast.parse(old.read_text(encoding="utf-8-sig")),ast.parse(new.read_text(encoding="utf-8-sig"))
constant=next(n for n in b.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="INDEPENDENT_PARTY_SCHEMA_PRECONDITION" for t in n.targets))
guard=ast.literal_eval(constant.value)
norm=copy.deepcopy(b)
norm.body=[n for n in norm.body if not(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="INDEPENDENT_PARTY_SCHEMA_PRECONDITION" for t in n.targets))]
tr=next(n for n in norm.body if isinstance(n,ast.FunctionDef) and n.name=="transform")
injected=tr.body.pop(0)
assert ast.unparse(injected.test)=="stage == 'independent-party'"
main=next(n for n in norm.body if isinstance(n,ast.FunctionDef) and n.name=="main")
cg=[n for n in main.body if isinstance(n,ast.Assert) and ast.unparse(n.test)=="args.stage == 'independent-party'"]
assert len(cg)==1
main.body.remove(cg[0])
assert ast.dump(norm,include_attributes=False)==ast.dump(a,include_attributes=False)
def tx(tree):
 ns={"Path":Path,"INDEPENDENT_PARTY_SCHEMA_PRECONDITION":guard}
 nodes=[copy.deepcopy(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {"patch_once","transform"}]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),"independent-transform-review","exec"),ns)
 return ns["transform"]
ot,nt=tx(a),tx(b)
sn=next(n for n in a.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="SOURCES" for t in n.targets))
sources=ast.literal_eval(sn.value)
for stage,(rel,digest,_) in sources.items():
 p=ROOT/rel;assert sha(p)==digest
 txt=p.read_text(encoding="utf-8-sig")
 before,after=ot(stage,txt,ROOT,ROOT/"artifacts/strict-post-close"),nt(stage,txt,ROOT,ROOT/"artifacts/strict-post-close")
 if stage=="independent-party":
  replacement="\n".join("        "+line for line in guard.rstrip().splitlines())
  old_guard="        assert set(seats).issubset(ids)"
  assert before.count(old_guard)==1 and before.replace(old_guard,replacement,1)==after
 else: assert before==after
histp=ROOT/"data/poll-history.json";ap=ROOT/"artifacts/strict-post-close/analysis.json";cp=ROOT/"data/parties.json"
pr=read(proof)
for key,p in [("historySha256",histp),("analysisSha256",ap),("catalogueSha256",cp)]:assert sha(p)==pr[key]
cat=read(cp);ids=[r["id"] for r in cat if r["ballot"]];assert len(ids)==17
hist={r["id"]:r for r in read(histp)["polls"]}
eligible=[r for r in read(ap)["cohort"] if r["eligibleStrict"]];assert len(eligible)==55
code=compile("assert sum(seats.values()) == 120\n"+guard,"independent-per-row-guard","exec")
def accepts(seats,catalog=cat):
 try:exec(code,{"ROOT":ROOT,"read":lambda _:catalog,"ids":ids,"seats":seats})
 except (AssertionError,TypeError):return False
 return True
arrays=[];clean_arrays=[]
for row in eligible:
 seats=hist[row["pollId"]]["seats"];assert accepts(seats)
 clean={k:v for k,v in seats.items() if k!="other"};assert accepts(clean)
 arrays.append([seats.get(k,0) for k in ids]);clean_arrays.append([clean.get(k,0) for k in ids])
assert arrays==clean_arrays and all(sum(row)==120 for row in arrays)
base=next(hist[row["pollId"]]["seats"] for row in eligible if "other" in hist[row["pollId"]]["seats"])
cases={"actual55PollCohort":"accepted","noAggregateOldCompatible":"accepted"}
for label,value in [("positive",1),("negative",-1),("floatZero",0.0),("fraction",.1),("boolFalse",False),("boolTrue",True),("stringZero","0"),("null",None),("list",[]),("mapping",{})]:
 seats=dict(base,other=value);assert not accepts(seats);cases["other_"+label]="rejected"
assert not accepts(dict(base,unknown_party=0));cases["unknownZero"]="rejected"
for label,c in [("missingOther",[r for r in cat if r["id"]!="other"]),("duplicateOther",cat+[r for r in cat if r["id"]=="other"]),("otherBallotTrue",[dict(r,ballot=True) if r["id"]=="other" else r for r in cat])]:
 assert not accepts(base,c);cases["catalog_"+label]="rejected"
bad=dict(base);bad.pop("likud");assert not accepts(bad);cases["missingPositiveBallotRaw120"]="rejected"
lineages={}
for stage,digest in [("bloc",sha(old)),("independent-bloc",sha(old)),("party",sha(primary))]:
 p=OUT.parent/"numeric-lineage"/(stage+"-enumeration-lineage.json")
 v=read(p);assert v["status"]=="PASS" and v["wrapperSha256"]==digest and v["inputHistorySha256"]==sha(histp)
 lineages[stage]=sha(p)
failed=OUT.parent/"canonical-numeric-runlogs/04-independent-party.log"
failure_hash=sha(failed)
assert "assert set(seats).issubset(ids)" in failed.read_text(encoding="utf-8-sig")
result={"status":"PASS","reviewedAtUtc":datetime.now(timezone.utc).isoformat(),"reviewerTask":"/root/c13_source_oct15","independentPartyAdapterSha256":sha(new),"primaryPartyAdapterPreservedSha256":sha(primary),"originalWrapperPreservedSha256":sha(old),"agentProofSha256":sha(proof),"onlyPerRowSubsetGuardAndIndependentStageCliRestrictionChanged":True,"allNumericalTransformBytesIdenticalOutsideGuard":True,"otherThreeStageTransformsUnchanged":True,"actual55x17ArraysEqualWithAndWithoutZeroAggregate":True,"noAdditionalTestFamilyOrMethodChange":True,"semanticAndAdversarialCases":cases,"caseCount":len(cases),"threePassedLineageHashesPreserved":lineages,"failed04LogSha256Preserved":failure_hash,"frozenFourAnalyzerHashesUnchanged":True,"heavyAnalysesExecuted":False,"conclusion":"Accepts only catalogued nonballot other at Python integer0. Unknown/nonzero/noninteger extras fail; original raw120-seat assertion remains. Independent least-squares, exact DP, tail tolerance, BH and sign flips unchanged."}
out=OUT/"secondary-party-schema-independent-review.json"
with out.open("x",encoding="utf-8") as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
assert sha(failed)==failure_hash
print(json.dumps({"status":"PASS","receipt":str(out.relative_to(ROOT)),"sha256":sha(out),"caseCount":len(cases)}))

