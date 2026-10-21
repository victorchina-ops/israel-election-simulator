"""Narrow21Oct opposition predicate compatibility around the unchanged validator.

Only the bloc/opposition boundary check uses the independently reviewed four-
count diagnosis. Every other case and every cohort/OLS/BH/DP/snapshot check runs
the original21Oct validator unchanged. No output, probability or tolerance edits.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import inspect
import json
import math
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-21'
ORIGINAL=ROOT/'scripts/validate-strict-trends-2026-10-21.py'
ORIGINAL_SHA='26508c81b8c6f664105edb69d0a1a7b757b21904081e7fdd3bde1230f8e90a7a'
DIAGNOSIS=ART/'numeric-boundaries/opposition-predicate-diagnosis.json'
DIAGNOSIS_SHA='c414a4dc5e979f8da467296c038035d7dffb937961fee26945cfb665d78ff74a'
REVIEW=ART/'numeric-boundaries/opposition-predicate-independent-review.json'
REVIEW_SHA='2fef6af558447f563218c62d2423ecb1cd1244e9e5adf38fabd7c27726a04cce'
REPRODUCER=ROOT/'scripts/diagnose-opposition-boundary-2026-10-21.py'
REPRODUCER_SHA='eba421c317aa995007faa76f48bbffdf87cd2607f11a5b35e589a0eb2ee76492'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def write_once(path,value):
    body=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.exists():assert path.read_bytes()==body,('Preserve dated evidence',str(path))
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)


def main():
    assert sha(ORIGINAL)==ORIGINAL_SHA==sha(ART/'numeric-boundaries/failed/validate-strict-trends-2026-10-21.py')
    spec=importlib.util.spec_from_file_location('_unchanged_strict_validator_21_predicate_r1',ORIGINAL)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    functions={k:v for k,v in vars(base).items() if inspect.isfunction(v)}
    original_boundary=base.boundary_check
    def reviewed_boundary(kind,identity,series,values_key,id_key,primary_observed,own_observed,
                          primary_count,own_count,total,hashes,scalar,counter,allow_compute):
        if (kind,identity)!=('bloc','opposition'):
            return original_boundary(kind,identity,series,values_key,id_key,primary_observed,own_observed,
                primary_count,own_count,total,hashes,scalar,counter,allow_compute)
        assert REVIEW_SHA is not None and sha(REVIEW)==REVIEW_SHA
        assert sha(DIAGNOSIS)==DIAGNOSIS_SHA and sha(REPRODUCER)==REPRODUCER_SHA
        proof,review=read(DIAGNOSIS),read(REVIEW)
        assert proof['status']==review['status']=='PASS' and proof['asOf']==review['asOf']=='2026-10-21'
        assert proof['outcome']==review['outcome']=='opposition'
        assert review['diagnosisSha256']==DIAGNOSIS_SHA and review['reproducerSha256']==REPRODUCER_SHA
        assert review['inputHashes']==proof['inputHashes']
        assert review['operationalPredicatesDistinct'] and not review['pOrQChanged'] and not review['frozenMethodsChanged']
        assert review['heavyCounterRunByReviewer'] is False and review['checks'] and all(v is True for v in review['checks'].values())
        assert proof['toleranceUnchanged']==review['toleranceUnchanged']==1e-12
        assert not proof['outputsOrFrozenHelpersModified'] and proof['allScalarSupportsAndLabeledMassesEqual']
        for rel,digest in proof['inputHashes'].items():
            assert sha(ROOT/rel)==digest
            if rel in hashes:assert hashes[rel]==digest
        expected={'primaryObservedHex':float(primary_observed).hex(),'independentObservedHex':float(own_observed).hex(),
            'primaryExtremeCountExact':str(primary_count),'independentExtremeCountExact':str(own_count),'totalExact':str(total)}
        assert all(proof[k]==review[k]==v for k,v in expected.items())
        assert proof['commonSubtractionPredicateIntegerMatch'] and proof['originalDirectOwnThresholdIntegerMatch']
        ps=int(proof['twoPointerSubtractionAtPrimaryCountExact']);ia=int(proof['directAtOwnObservedCountExact'])
        ap=int(proof['directAtPrimaryObservedCountExact']);so=int(proof['twoPointerSubtractionAtOwnCountExact'])
        assert ps==primary_count and ia==own_count and ap!=primary_count
        decomposition=proof['signedCountDecomposition']
        assert int(decomposition['predicateAtPrimary'])==ap-ps
        assert int(decomposition['directObservedShift'])==ia-ap
        assert int(decomposition['subtractionObservedShift'])==so-ps
        assert int(decomposition['predicateAtIndependent'])==ia-so
        assert (ap-ps)+(ia-ap)==(so-ps)+(ia-so)==int(decomposition['totalDifference'])==own_count-primary_count
        assert proof['decompositionIsSignedNetCountDifferenceNotPairEnumeration'] is True
        assert proof['halfSizes']==proof['subtractionHalfSizes']
        assert math.prod(int(v) for v in proof['rawHalfMasses'])==total
        assert len(proof['support'])==len(series)
        for support,item in zip(proof['support'],series):
            values=next(v['seats'] for v in item[values_key] if v[id_key]==identity)
            assert support['pollsterId']==item['pollsterId'] and support['pollIds']==item['pollIds']
            assert support['timeDays']==item['timeDaysFromFirst'] and support['seats']==values and support['weight']==item['weight']
            block=scalar.score_blocks(item['timeDaysFromFirst'],values,item['weight'],method='dp')[0]
            assert support['rawMass']==str(block.raw_permutations)==str(math.factorial(len(values)))
            assert support['uniqueScores']==len(block.values)
            assert support['valuesSha256']==hashlib.sha256(block.values.tobytes()).hexdigest()
            assert support['multiplicitiesSha256']==hashlib.sha256(json.dumps([str(int(v)) for v in block.multiplicities],separators=(',',':')).encode()).hexdigest()
        receipt={'status':'PASS','asOf':'2026-10-21','kind':kind,'identity':identity,**expected,
            'inputHashes':hashes,'toleranceUnchanged':1e-12,'operationalPredicatesDistinct':True,
            'primarySubtractionPredicateIntegerMatch':True,'independentAdditionOwnThresholdIntegerMatch':True,
            'commonAdditionThresholdMatchesPrimary':False,
            'primarySubtractionCountExact':str(ps),'independentAdditionOwnCountExact':str(ia),
            'independentAdditionAtPrimaryCountExact':str(ap),'primarySubtractionAtIndependentCountExact':str(so),
            'signedCountDecomposition':decomposition,'support':proof['support'],
            'diagnosisPath':DIAGNOSIS.relative_to(ROOT).as_posix(),'diagnosisSha256':DIAGNOSIS_SHA,
            'independentReviewPath':REVIEW.relative_to(ROOT).as_posix(),'independentReviewSha256':REVIEW_SHA,
            'reproducerPath':REPRODUCER.relative_to(ROOT).as_posix(),'reproducerSha256':REPRODUCER_SHA,
            'baseValidatorSha256':ORIGINAL_SHA,'adapterSha256':sha(Path(__file__)),
            'commonDirectThresholdMatchClaimed':False,'probabilitiesOrFrozenMethodsModified':False,
            'scope':'Only actual21Oct bloc/opposition floating comparisons; both original integer counts reproduced under their respective operational predicates. No tolerance, p/q or other validation checks changed.'}
        target=ART/'numeric-boundaries/bloc-opposition-predicate-r1.json';write_once(target,receipt)
        return target
    # These are the only imported-validator global replacements. All original
    # function objects except the one scoped boundary wrapper remain identical.
    base.boundary_check=reviewed_boundary
    base.__file__=str(Path(__file__).resolve())
    assert all(vars(base)[name] is fn for name,fn in functions.items() if name!='boundary_check')
    ast_nodes=ast.parse(ORIGINAL.read_text(encoding='utf-8-sig')).body
    main_ast=next(n for n in ast_nodes if isinstance(n,ast.FunctionDef) and n.name=='main')
    compatibility={'status':'PASS-SOURCE-COMPATIBILITY','asOf':'2026-10-21','baseValidatorSha256':ORIGINAL_SHA,
        'adapterSha256':sha(Path(__file__)),'baseMainAstSha256':hashlib.sha256(ast.dump(main_ast,include_attributes=False).encode()).hexdigest(),
        'baseFileBytesEqualPreservedFailureSource':True,'allOriginalNonBoundaryFunctionObjectsRetained':True,
        'onlyValidatorGlobalReplacements':['boundary_check','__file__'],'numericScope':['bloc','opposition'],
        'diagnosisSha256':DIAGNOSIS_SHA,'independentReviewSha256':REVIEW_SHA,'numericalVerdict':False}
    write_once(ART/'numeric-boundaries/predicate-r1-source-compatibility.json',compatibility)
    base.main()


if __name__=='__main__':main()
