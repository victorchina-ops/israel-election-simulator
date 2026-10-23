"""Run the four unchanged reviewed exact transforms on the 23 October cohort.

The 20 October scalar backend and schema adapters remain immutable. This thin
dated dispatcher changes input/output locations only. --check-transforms compiles
the transformed sources without executing counters or modifying canonical data.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-23'
ART = ROOT / 'artifacts/poll-checks' / DAY
ADAPTERS = {
    'base': ('scripts/run-exact-trends-2026-10-20-evening.py', 'eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7'),
    'party': ('scripts/run-exact-trends-2026-10-20-evening-party-schema-r1.py', 'd8e7164f20176ee864de8b9702cd6ac0b130fcca854032261a329805a98d0b74'),
    'independent-party': ('scripts/run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py', 'd9d5328f57a6dc3f62090ba02868e2a2a9940ad2c4a431c3551b65c0e38ae9c1'),
}
BACKEND = ('scripts/exact_scalar_marginals_2026_10_20.py', 'ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035')
STAGES = ('bloc', 'independent-bloc', 'party', 'independent-party')
AUDITS = ('lazar-fieldwork.json', 'n12-kan-c13-fieldwork.json', 'c14-i24-fieldwork.json', 'c16-tatika-fieldwork.json', 'new-unverified-fieldwork-2026-09-30.json')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def adapter_for(stage):
    key = stage if stage in {'party', 'independent-party'} else 'base'
    rel, digest = ADAPTERS[key]
    path = ROOT / rel
    assert sha(path) == digest, ('Reviewed adapter changed', rel)
    assert sha(ROOT / BACKEND[0]) == BACKEND[1], 'Reviewed scalar backend changed'
    spec = importlib.util.spec_from_file_location('_reviewed_exact_' + key.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scalar.verify_frozen_counters()
    return module, rel, digest


def transformed(stage, input_root, output_root):
    module, adapter_rel, adapter_sha = adapter_for(stage)
    analyzer, digest, output_name = module.SOURCES[stage]
    frozen_path = ROOT / analyzer
    assert sha(frozen_path) == digest, ('Frozen analyzer changed', analyzer)
    code = module.transform(stage, frozen_path.read_text(encoding='utf-8-sig'), input_root, output_root)
    assert 'list(permutations(' not in code and 'list(itertools.permutations(' not in code
    compile(code, str(frozen_path), 'exec')
    return module, frozen_path, output_name, code, adapter_rel, adapter_sha


def write_once(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists(), ('Preserve dated receipt', str(path))
    path.write_bytes(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--as-of', required=True, choices=[DAY])
    parser.add_argument('--input-root', type=Path)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--publish-canonical', action='store_true')
    parser.add_argument('--check-transforms', action='store_true')
    args = parser.parse_args()
    input_root = (args.input_root or ROOT).resolve()
    if args.check_transforms:
        assert not args.publish_canonical and args.stage is None
        assert args.input_root is None and args.output_root is None
        rows = []
        for stage in STAGES:
            module, frozen_path, name, code, rel, digest = transformed(stage, ROOT, ROOT / 'artifacts/strict-post-close')
            rows.append({'stage':stage, 'adapter':rel, 'adapterSha256':digest,
                'analyzer':frozen_path.relative_to(ROOT).as_posix(), 'analyzerSha256':sha(frozen_path),
                'transformedSourceSha256':hashlib.sha256(code.encode()).hexdigest(), 'outputFile':name})
        result = {'status':'PASS', 'asOf':DAY, 'mode':'compile-transforms-only', 'wrapperSha256':sha(Path(__file__)),
            'backend':BACKEND[0], 'backendSha256':BACKEND[1], 'stages':rows,
            'canonicalMutation':False, 'numericalCountersExecuted':False,
            'reuse':'Transforms called from unchanged reviewed 20 October adapters; no inference implementation copied or altered.'}
        write_once(ART / 'numeric-transform-preflight.json', result)
        print(json.dumps(result, ensure_ascii=False))
        return
    assert args.stage is not None
    if args.publish_canonical:
        assert input_root == ROOT and args.output_root is None
        output_root = ROOT / 'artifacts/strict-post-close'
        lineage_dir = ART / 'numeric-lineage'
    else:
        assert args.output_root is not None
        output_root = args.output_root.resolve()
        assert output_root.is_relative_to(ART.resolve()), 'Staged output must stay in new dated artifacts'
        lineage_dir = output_root
    assert read(input_root / 'data/poll-history.json')['asOf'] == args.as_of
    assert read(input_root / 'data/current-polls.json')['asOf'] == args.as_of
    module, frozen_path, output_name, code, adapter_rel, adapter_sha = transformed(args.stage, input_root, output_root)
    destination = lineage_dir / (args.stage + '-enumeration-lineage.json')
    assert not destination.exists(), 'Preserve completed lineage receipts'
    output_root.mkdir(parents=True, exist_ok=True)
    lineage_dir.mkdir(parents=True, exist_ok=True)
    if not args.publish_canonical:
        assert not (output_root / output_name).exists(), 'Choose a new staged directory'
        for name in [*module.scalar.FROZEN_COUNTER_HASHES, *AUDITS]:
            source, target = input_root / 'artifacts/strict-post-close' / name, output_root / name
            if target.exists():
                assert sha(target) == sha(source)
            else:
                shutil.copy2(source, target)
    namespace = {'__name__':'__main__', '__file__':str(frozen_path), 'scalar':module.scalar}
    exec(compile(code, str(frozen_path), 'exec'), namespace)
    result = {'status':'PASS', 'asOf':args.as_of, 'stage':args.stage,
        'frozenAnalyzer':frozen_path.relative_to(ROOT).as_posix(), 'frozenAnalyzerSha256':sha(frozen_path),
        'reviewedAdapter':adapter_rel, 'reviewedAdapterSha256':adapter_sha,
        'wrapperSha256':sha(Path(__file__)), 'scalarBackendSha256':BACKEND[1],
        'transformedSourceSha256':hashlib.sha256(code.encode()).hexdigest(),
        'frozenCounterHashes':module.scalar.FROZEN_COUNTER_HASHES,
        'inputHistorySha256':sha(input_root / 'data/poll-history.json'),
        'inputAuditHashes':{name:sha(input_root / 'artifacts/strict-post-close' / name) for name in AUDITS},
        'outputFile':output_name, 'outputSha256':sha(output_root / output_name),
        'enumeration':'unique scalar assignments with exact repeated-label multiplicity' if args.stage in {'bloc','party'} else 'independent labeled-choice count/score DP',
        'nullUnchanged':True, 'outcomeMarginalExactness':True, 'monteCarlo':False, 'cohortAndWeightsUnchanged':True}
    write_once(destination, result)


if __name__ == '__main__':
    main()
