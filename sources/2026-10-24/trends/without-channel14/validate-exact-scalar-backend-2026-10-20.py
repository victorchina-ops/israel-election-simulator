"""Prove scalar exactness on exhaustive toys and frozen 19 October outputs."""
from collections import Counter
from itertools import permutations, product
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import time

import numpy as np
import exact_scalar_marginals_2026_10_20 as scalar
from compressed_searchsorted_exact import ScalarBlock, exact_counts

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/"artifacts/poll-checks/2026-10-20"
BEFORE=ART/"before"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))


def freeze(path,value):
    body=json.dumps(value,ensure_ascii=False,indent=2)+"\n"
    assert not path.exists(),"Preserve completed proof; choose a new reviewed revision"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(body,encoding="utf-8")
    print(json.dumps({"status":"PASS","receipt":path.relative_to(ROOT).as_posix(),"sha256":sha(path)}))


def toys():
    started=time.perf_counter()
    cases=[([0,1,3],[-1,0,1]),([0,.5,2,6],[-2,-2,0,3]),([0,2,4,9,10],[0,0,0,4,4]),
           ([0,1,4,7,9,11],[-3,-3,-1,0,0,5]),([0,.5,1,2,3,5,8],[0,0,1,1,2,2,2]),
           ([0,2,7],[0,0,0]),([0,1,9],[-4,-4,-4])]
    records=[]
    for times,values in cases:
        u=scalar.integer_times(times)
        centered=[len(u)*x-sum(u) for x in u]
        oracle=Counter(sum(c*y for c,y in zip(centered,order)) for order in permutations(values))
        unique=scalar.unique_distribution(u,scalar.integer_outcomes(values))
        dp=scalar.dp_distribution(u,scalar.integer_outcomes(values))
        assert dict(unique[0])==dict(dp[0])==dict(oracle)
        assert unique[1:]==dp[1:] and unique[1]==math.factorial(len(values))
        assert sum(score*mass for score,mass in oracle.items())==0
        records.append({"times":times,"outcomes":values,"labeledMass":unique[1],"uniqueScores":len(oracle)})
    spec=importlib.util.spec_from_file_location("independent_large_mass",scalar.FROZEN/"independent-compressed-counts.py")
    independent=importlib.util.module_from_spec(spec);spec.loader.exec_module(independent)
    raw=math.factorial(13)
    block=ScalarBlock(np.asarray([-1.,0.,1.]),np.asarray([raw//4,raw//2,raw//4],dtype=np.int64),raw)
    observed=[0.,1.,2.,1.+1e-12,2.+2e-12]
    blocks=[[block for _ in observed],[block for _ in observed]]
    result=exact_counts(blocks,observed,tolerance=1e-12)
    counts,total,_=independent.direct_tail_counts([[(block.values,block.multiplicities) for _ in observed]]*2,observed,tolerance=1e-12)
    oracle=[sum(int(a)*int(b) for (x,a),(y,b) in product(zip(block.values,block.multiplicities),repeat=2)
                if abs(float(x)+float(y))>=abs(stat)-1e-12) for stat in observed]
    assert total==result["nPermutations"]==raw**2>np.iinfo(np.int64).max
    assert type(result["nPermutations"]) is int
    assert result["extremeCounts"]==[int(x) for x in counts]==oracle
    assert all(type(x) is int and 0<=x<=raw**2 for x in result["extremeCounts"])
    assert result["extremeCounts"][0]==raw**2
    freeze(ART/"scalar-review/toy-equivalence.json",{
        "status":"PASS","asOf":"2026-10-20","cases":records,
        "largeMass":{"rawBlockMass":str(raw),"total":str(total),"extremeCountsExact":[str(x) for x in oracle],
                     "thresholds":observed,"primaryAndIndependentAndManualAgree":True,"pythonIntegerProductsAndTails":True},
        "meanExactlyZero":True,"allMassesEqualFactorial":True,"noMonteCarlo":True,
        "elapsedSeconds":time.perf_counter()-started,"backendSha256":sha(Path(scalar.__file__)),
        "validatorSha256":sha(Path(__file__)),"frozenCounterHashes":scalar.FROZEN_COUNTER_HASHES})


def compare_value(old,new,path=""):
    if isinstance(old,(float,int)) and not isinstance(old,bool):
        assert isinstance(new,(float,int)) and math.isclose(old,new,rel_tol=0,abs_tol=1e-12),(path,old,new)
    elif isinstance(old,list):
        assert isinstance(new,list) and len(old)==len(new),path
        for i,(a,b) in enumerate(zip(old,new)):compare_value(a,b,f"{path}/{i}")
    elif isinstance(old,dict):
        assert set(old)==set(new),(path,set(old)^set(new))
        for key in old:compare_value(old[key],new[key],f"{path}/{key}")
    else:
        assert old==new,(path,old,new)


def archive19(output):
    assert output.resolve().is_relative_to(ART.resolve())
    assert read(BEFORE/"data/poll-history.json")["asOf"]=="2026-10-19"
    checked=[]
    for filename in ["analysis.json","party-analysis.json"]:
        previous=read(BEFORE/"artifacts/strict-post-close"/filename)
        revised=read(output/filename)
        assert revised["asOf"]==previous["asOf"]=="2026-10-19"
        for key in ["cohort","normalizedHistoricalWeights","closure"]:compare_value(previous[key],revised[key],filename+"/"+key)
        for axis in ["primary","publicationDateSensitivity"]:
            # Includes every individual p/q, endpoint, OLS/GLS/sign flip and exact tail count string.
            compare_value(previous[axis],revised[axis],filename+"/"+axis)
            assert previous[axis]["exactCounting"]["extremeCountsExact"]==revised[axis]["exactCounting"]["extremeCountsExact"]
        checked.append({"file":filename,"frozenSha256":sha(BEFORE/"artifacts/strict-post-close"/filename),"newSha256":sha(output/filename)})
    bi=read(output/"independent-strict-numeric-audit.json");old_bi=read(BEFORE/"artifacts/strict-post-close/independent-strict-numeric-audit.json")
    pi=read(output/"party-independent.json");old_pi=read(BEFORE/"artifacts/strict-post-close/party-independent.json")
    compare_value(old_bi,bi,"independent-bloc")
    # Source-analysis provenance hashes change only because its source file is regenerated in the benchmark.
    for key in old_pi:
        if key!="cohortSha256":compare_value(old_pi[key],pi[key],"independent-party/"+key)
    assert pi["cohortSha256"]==sha(output/"analysis.json")
    full=read(output/"analysis.json");party=read(output/"party-analysis.json")
    assert bi["countsExact"]==full["primary"]["exactCounting"]["extremeCountsExact"]
    assert [r["extremeCountExact"] for r in pi["overall"]]==party["primary"]["exactCounting"]["extremeCountsExact"]
    freeze(ART/"scalar-review/archive19-equivalence.json",{
        "status":"PASS","baselineAsOf":"2026-10-19","asOf":"2026-10-20","comparisonTolerance":1e-12,
        "allPrimaryAndPublicationAxisResultsAgree":True,"exactCombinedTailIntegersAgree":True,
        "independentDPTailsAgreeWithFrozenReference":True,"allIndividualPAndBHAndSignFlipResultsAgree":True,
        "cohortAndWeightsAndEffectsUnchanged":True,"frozenOutputs":checked,
        "backendSha256":sha(Path(scalar.__file__)),"wrapperSha256":sha(ROOT/"scripts/run-exact-trends-2026-10-20.py"),
        "validatorSha256":sha(Path(__file__)),"checkpointManifestSha256":sha(BEFORE/"manifest.json"),
        "frozenCounterHashes":scalar.FROZEN_COUNTER_HASHES,
        "benchmarkLineageHashes":{p.name:sha(p) for p in output.glob("*-enumeration-lineage.json")}})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toys",action="store_true")
    parser.add_argument("--archive19",type=Path)
    args=parser.parse_args()
    assert args.toys or args.archive19
    if args.toys:toys()
    if args.archive19:archive19(args.archive19)
