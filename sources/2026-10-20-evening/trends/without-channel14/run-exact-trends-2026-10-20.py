"""Run pinned historical analyzers with only exact scalar enumeration replaced.

Benchmark mode reads an immutable input root and writes only under the 20 October
artifact folder. Canonical output requires --publish-canonical explicitly. The
registered OLS/GLS, cohort, BH, sign flips and frozen combined-tail counters remain
the pinned source implementation; every textual substitution must match once.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

import exact_scalar_marginals_2026_10_20 as scalar

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-20"
SOURCES = {
 "bloc":("artifacts/analyze-strict-post-close-2026-09-28.py","fc5a4ce6c242192f71380c9ddfe96f3b7889308ded25a41abb1f43a61c5b25f2","analysis.json"),
 "party":("artifacts/analyze-party-trends-strict-2026-09-28.py","4aff7e6b7310e25a5e7845ecc6b084a58d819cae98fac9e14d32c640faafb34c","party-analysis.json"),
 "independent-bloc":("artifacts/audit-strict-full-series-2026-09-28.py","2a811072ea413e9b21db57c764fa6613ef4f1390aec939c5337c2bcbb228fe26","independent-strict-numeric-audit.json"),
 "independent-party":("artifacts/strict-post-close/party-independent.py","9e37df10e256b6af6b0a6eaf3961ac20c6caf72495fe1063e1e7d26aa13bdf68","party-independent.json"),
}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))


def patch_once(source,old,new):
    assert source.count(old)==1,("pinned enumeration substitution mismatch",old[:120],source.count(old))
    return source.replace(old,new,1)


def transform(stage,source,input_root,output_root):
    path=lambda p:f"Path({str(p)!r})"
    if stage in {"bloc","party"}:
        old_root = "ROOT = Path(__file__).resolve().parents[1]" if stage=="bloc" else "ROOT=Path(__file__).resolve().parents[1]"
        old_out = "OUT = ROOT / 'artifacts/strict-post-close'" if stage=="bloc" else "OUT=ROOT/'artifacts/strict-post-close'"
        source=patch_once(source,old_root,"ROOT = "+path(input_root))
        source=patch_once(source,old_out,"OUT = "+path(output_root))
        weight="weight" if stage=="bloc" else "w"
        dense="""        perm=np.array(list(permutations(range(len(pp)))))
        ps=np.einsum('i,pij->pj',coeff,y[perm])
        assert len(ps)==math.factorial(len(pp))
        assert np.allclose(ps.mean(axis=0),0,atol=1e-12)
        distributions.append(integer_score_blocks(t, y.astype(np.int64), perm, WEIGHT))""".replace("WEIGHT",weight)
        replacement="""        unweighted_blocks = scalar.score_blocks(t, y, 1.0, method='unique')
        individual_p = scalar.individual_pvalues(unweighted_blocks, slopes, tolerance=1e-12)
        distributions.append(scalar.score_blocks(t, y, WEIGHT, method='unique'))""".replace("WEIGHT",weight)
        source=patch_once(source,dense,replacement)
        old="float(np.mean(np.abs(ps[:,j])>=abs(slopes[j])-1e-12))" if stage=="bloc" else "float(np.mean(np.abs(ps[:,j])>=abs(slope)-1e-12))"
        source=patch_once(source,old,"float(individual_p[j])")
    elif stage=="independent-bloc":
        source=patch_once(source,"R=Path(__file__).resolve().parents[1]","R="+path(input_root))
        source=source.replace("R/'artifacts/strict-post-close'",path(output_root))
        for name in ("independent-compressed-counts.py","analysis.json","independent-strict-numeric-audit.json"):
            source=patch_once(source,f"R/'artifacts/strict-post-close/{name}'",path(output_root/name))
        old="dist=np.array([coef@y[list(ix)] for ix in itertools.permutations(range(len(rs)))]);individual.append({'pollsterId':pid,'slope':sl.tolist(),'p':(np.abs(dist)>=np.abs(sl)-1e-12).mean(axis=0).tolist()})"
        new="unweighted=scalar.independent_blocks(times,y,1.0);individual.append({'pollsterId':pid,'slope':sl.tolist(),'p':scalar.individual_pvalues(unweighted,sl,tolerance=1e-12).tolist()})"
        source=patch_once(source,old,new)
        source=patch_once(source,"compressed.append(helper.score_blocks(times,y,np.asarray(list(itertools.permutations(range(len(rs))))),weight))","compressed.append(scalar.independent_blocks(times,y,weight))")
        source=patch_once(source," if np.max(np.abs(dist))<1e-12:constant_factor*=len(dist)\n else:blocks.append(weight*dist)","")
    else:
        source=patch_once(source,"ROOT = Path(__file__).resolve().parents[2]","ROOT = "+path(input_root))
        source=patch_once(source,"OUT = Path(__file__).resolve().parent","OUT = "+path(output_root))
        old="""    orders=np.asarray(list(permutations(range(len(polls)))))
    cases=np.asarray([np.linalg.lstsq(design,yy[order],rcond=None)[0][1]
                      for order in orders])
    assert len(cases)==math.factorial(len(polls))
    assert np.max(abs(cases.mean(axis=0)))<1e-10
    pvals=np.mean(abs(cases)>=abs(slope)-1e-10,axis=0)"""
        new="""    unweighted=scalar.independent_blocks(xx,yy,1.0)
    pvals=scalar.individual_pvalues(unweighted,slope,tolerance=1e-10)"""
        source=patch_once(source,old,new)
        source=patch_once(source,"    perms.append(w*cases)\n","")
        source=patch_once(source,"compressed.append(helper.score_blocks(xx, yy, orders, w))","compressed.append(scalar.independent_blocks(xx,yy,w))")
    return source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",required=True,choices=SOURCES)
    parser.add_argument("--as-of",required=True)
    parser.add_argument("--input-root",type=Path)
    parser.add_argument("--output-root",type=Path)
    parser.add_argument("--publish-canonical",action="store_true")
    args=parser.parse_args()
    input_root=(args.input_root or ROOT).resolve()
    if args.publish_canonical:
        assert input_root==ROOT and args.output_root is None and args.as_of=="2026-10-20"
        output_root=ROOT/"artifacts/strict-post-close"
        lineage_dir=ART/"numeric-lineage"
    else:
        assert args.output_root is not None
        output_root=args.output_root.resolve()
        assert output_root.is_relative_to(ART.resolve()),"Benchmark output must stay in dated artifacts"
        lineage_dir=output_root
    assert read(input_root/"data/poll-history.json")["asOf"]==args.as_of
    source_path,digest,output_name=SOURCES[args.stage]
    frozen_path=ROOT/source_path
    assert sha(frozen_path)==digest,"Frozen analyzer changed"
    scalar.verify_frozen_counters()
    output_root.mkdir(parents=True,exist_ok=True)
    lineage_dir.mkdir(parents=True,exist_ok=True)
    if not args.publish_canonical:
        assert not (output_root/output_name).exists(),"Preserve prior benchmark output; choose a new directory"
        required=list(scalar.FROZEN_COUNTER_HASHES)+["lazar-fieldwork.json","n12-kan-c13-fieldwork.json","c14-i24-fieldwork.json","c16-tatika-fieldwork.json","new-unverified-fieldwork-2026-09-30.json"]
        for name in required:
            original=input_root/"artifacts/strict-post-close"/name
            target=output_root/name
            if target.exists():
                assert sha(target)==sha(original)
            else:
                shutil.copy2(original,target)
    code=transform(args.stage,frozen_path.read_text(encoding="utf-8-sig"),input_root,output_root)
    assert "list(permutations(" not in code and "list(itertools.permutations(" not in code
    namespace={"__name__":"__main__","__file__":str(frozen_path),"scalar":scalar}
    exec(compile(code,str(frozen_path),"exec"),namespace)
    lineage={"asOf":args.as_of,"stage":args.stage,"status":"PASS","frozenAnalyzer":source_path,"frozenAnalyzerSha256":digest,
        "transformedSourceSha256":hashlib.sha256(code.encode()).hexdigest(),"wrapperSha256":sha(Path(__file__)),
        "scalarBackendSha256":sha(Path(scalar.__file__)),"frozenCounterHashes":scalar.FROZEN_COUNTER_HASHES,
        "enumeration":"unique scalar assignments with exact repeated-label multiplicity" if args.stage in {"bloc","party"} else "independent labeled-choice count/score DP",
        "nullUnchanged":True,"outcomeMarginalExactness":True,"monteCarlo":False,"cohortAndWeightsUnchanged":True,
        "inputHistorySha256":sha(input_root/"data/poll-history.json"),"outputFile":output_name,"outputSha256":sha(output_root/output_name)}
    destination=lineage_dir/(args.stage+"-enumeration-lineage.json")
    assert not destination.exists(),"Preserve frozen lineage receipts"
    destination.write_text(json.dumps(lineage,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
