"""Focused exact-counter diagnosis of one existing bloc outcome; no canonical changes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, math, sys, time
import numpy as np
ROOT=Path.cwd().resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/"scripts"))
import exact_scalar_marginals_2026_10_20 as backend
from compressed_searchsorted_exact import compressed_searchsorted_tail
OUT=ROOT/"artifacts/poll-checks/2026-10-20-evening/numeric-compatibility/float-boundary"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
basep=ROOT/"artifacts/strict-post-close/analysis.json"
indp=ROOT/"artifacts/strict-post-close/independent-strict-numeric-audit.json"
hp=ROOT/"data/poll-history.json"
frozen=ROOT/"artifacts/strict-post-close/independent-compressed-counts.py"
assert sha(frozen)=="8a725d5bfca3a0f40a8f6e72f038e76877ec88e0d444b8fbf07686da3f1b924d"
backend.verify_frozen_counters()
inputs={str(p.relative_to(ROOT)):sha(p) for p in [basep,indp,hp,frozen,Path(backend.__file__)]}
base,ind=read(basep),read(indp)
assert base["historySha256"]==sha(hp)
j=ind["groups"].index("opposition_raam")
primary=next(r for r in base["primary"]["overall"] if r["group"]=="opposition_raam")
pobs=primary["slopePerWeek"];iobs=ind["slopes"][j]
assert pobs==-0.156095834367954 and iobs==-0.15609583436795355
total=int(ind["totalExact"])
pc=int(base["primary"]["exactCounting"]["extremeCountsExact"][j])
ic=int(ind["countsExact"][j])
assert pc==329198046923753075400612249600
assert ic==329198046923755811804125593600
history={r["id"]:r for r in read(hp)["polls"]}
group=base["groups"]["opposition_raam"]
blocks=[];details=[]
for series in base["primary"]["byPollster"]:
 t=series["timeDaysFromFirst"]
 y=next(r["seats"] for r in series["groups"] if r["group"]=="opposition_raam")
 assert y==[sum(history[k]["seats"].get(pid,0) for pid in group) for k in series["pollIds"]]
 w=series["weight"]
 pb=backend.score_blocks(t,np.asarray(y)[:,None],w,method="unique")[0]
 ib=backend.independent_blocks(t,np.asarray(y)[:,None],w)[0]
 assert np.array_equal(pb.values,ib[0]) and np.array_equal(pb.multiplicities,ib[1])
 assert sum(int(v) for v in ib[1])==math.factorial(len(t))
 blocks.append([ib])
 details.append({"pollsterId":series["pollsterId"],"n":len(t),"timeDays":t,"seats":y,"weight":w,"uniqueScores":len(ib[0]),"rawPermutationMass":str(math.factorial(len(t))),"floatValuesSha256":hashlib.sha256(ib[0].tobytes()).hexdigest(),"exactMultiplicities":[str(int(v)) for v in ib[1]],"valuesHex":[float(v).hex() for v in ib[0]]})
assert math.prod(int(d["rawPermutationMass"]) for d in details)==total
spec=importlib.util.spec_from_file_location("frozen_boundary_independent_counter",frozen)
counter=importlib.util.module_from_spec(spec);spec.loader.exec_module(counter)
print(json.dumps({"status":"START","outcome":"opposition_raam","primaryObservedHex":pobs.hex(),"independentObservedHex":iobs.hex(),"seriesUniqueSizes":[d["uniqueScores"] for d in details]}),flush=True)
started=time.monotonic()
counts_common,common_total,common_sizes=counter.direct_tail_counts(blocks,[pobs],tolerance=1e-12)
common=int(counts_common[0])
print(json.dumps({"status":"COMMON_THRESHOLD_DONE","count":str(common),"matchesPrimary":common==pc,"elapsedSeconds":time.monotonic()-started}),flush=True)
counts_own,own_total,own_sizes=counter.direct_tail_counts(blocks,[iobs],tolerance=1e-12)
own=int(counts_own[0])
print(json.dumps({"status":"OWN_THRESHOLD_DONE","count":str(own),"matchesIndependent":own==ic,"elapsedSeconds":time.monotonic()-started}),flush=True)
assert common_total==own_total==total
result={
 "schemaVersion":1,"status":"PASS" if common==pc and own==ic else "INVESTIGATE",
 "reviewedAtUtc":datetime.now(timezone.utc).isoformat(),"outcome":"opposition_raam",
 "inputSha256":inputs,"reviewerTask":"/root/c13_source_oct15",
 "primaryObserved":pobs,"primaryObservedHex":pobs.hex(),"independentObserved":iobs,"independentObservedHex":iobs.hex(),"observedDifference":pobs-iobs,
 "toleranceUnchanged":1e-12,
 "primaryCutoffHex":(abs(pobs)-1e-12).hex(),"independentCutoffHex":(abs(iobs)-1e-12).hex(),
 "observedDifferenceInUlps":abs(pobs-iobs)/math.ulp(pobs),
 "totalPermutationsExact":str(total),"archivedPrimaryExtremeCountExact":str(pc),"archivedIndependentExtremeCountExact":str(ic),
 "independentCounterAtPrimaryObservedCountExact":str(common),"independentCounterAtOwnObservedCountExact":str(own),
 "commonThresholdExactIntegerMatch":common==pc,"independentOwnThresholdIntegerMatch":own==ic,
 "boundaryMultiplicityDifferenceExact":str(own-common),"boundaryProbabilityMass":(own-common)/total,
 "primaryP":pc/total,"independentP":ic/total,"commonThresholdP":common/total,
 "allPrimaryUniqueAndIndependentDpScalarBlocksByteIdentical":True,
 "nullMassRestoredByExactLabeledMultiplicities":True,"halfSizes":common_sizes,"elapsedSeconds":time.monotonic()-started,
 "numericalOutputsOrFrozenHelpersModified":False,
 "inference":"If common-threshold integers agree, discrepancy is solely the16-ULP difference in separately computed OLS observed statistic moving the fixed1e-12 cutoff across a tiny atom of the discrete permutation null. It does not change either reported result and is not resolved by changing tolerance.",
 "seriesBlocks":details
}
for rel,digest in inputs.items():assert sha(ROOT/rel)==digest
dest=OUT/"focused-common-threshold-review.json"
with dest.open("x",encoding="utf-8") as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":result["status"],"receipt":str(dest.relative_to(ROOT)),"sha256":sha(dest)}),flush=True)

