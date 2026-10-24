"""Orchestrate four actual exact recomputations with the unchanged backend cache.

The standard exact histogram caches persist in this process, keyed by the exact
integer times and outcomes. Independent DP uses its separate existing cache.
Combined tail counts, slopes and multiplicity corrections are always recomputed.
This command writes canonical numeric audits only with --run explicitly.
"""
from pathlib import Path
import argparse
import contextlib
import hashlib
import importlib.util
import json
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-21'
ART = ROOT / 'artifacts/poll-checks' / DAY
DISPATCHER = ROOT / 'scripts/run-exact-trends-2026-10-21.py'
DISPATCHER_SHA = 'c569e710b25a6d4e8ee74276953197cc3992e22119aa32cf58789c1ab634fa92'
STAGES = ('bloc', 'party', 'independent-bloc', 'independent-party')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def write(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if path.exists():
        assert path.read_bytes() == body, ('Preserve completed receipt', str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    assert sha(DISPATCHER) == DISPATCHER_SHA
    plan = read(ART / 'source-plan.json')
    validation = read(ART / 'ingestion-validation.json')
    assert plan['asOf'] == validation['asOf'] == DAY
    assert validation['status'] == 'PASS'
    hashes = {p:sha(ROOT / p) for p in ['data/current-polls.json','data/poll-history.json',
        'data/calibration.json','data/parties.json','artifacts/poll-checks/2026-10-21/source-plan.json',
        'artifacts/poll-checks/2026-10-21/ingestion-validation.json',
        *['artifacts/strict-post-close/' + name for name in ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']]]}
    assert read(ROOT / 'data/current-polls.json')['asOf'] == read(ROOT / 'data/poll-history.json')['asOf'] == DAY
    spec = importlib.util.spec_from_file_location('_dated_exact_dispatcher_2026_10_21', DISPATCHER)
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)
    # Imports verify all frozen analyzers, adapters and scalar counters without
    # running numerical enumeration. The transformed sources are compiled here.
    for stage in STAGES:
        dispatcher.transformed(stage, ROOT, ROOT / 'artifacts/strict-post-close')
    preflight = {'status':'PASS','asOf':DAY,'stageOrder':STAGES,'inputHashes':hashes,
        'dispatcherSha256':DISPATCHER_SHA,'scriptSha256':sha(Path(__file__)),
        'cache':'Existing unchanged exact-key LRU caches only; no prior result or p/q reuse',
        'primaryAndIndependentCachesSeparate':True,'combinedTailsRecomputed':True}
    if args.check:
        assert not args.resume
        write(ART / 'numeric-run-preflight.json', preflight)
        print(json.dumps(preflight, ensure_ascii=False))
        return
    assert read(ART / 'numeric-run-preflight.json') == json.loads(json.dumps(preflight))
    log_dir = ART / 'canonical-numeric-runlogs'
    log_dir.mkdir(parents=True, exist_ok=True)
    stages = []
    for ordinal, stage in enumerate(STAGES, 1):
        receipt_path = log_dir / (stage + '-receipt.json')
        if receipt_path.exists():
            assert args.resume, 'Use --resume to validate and retain completed stages'
            receipt = read(receipt_path)
            assert receipt['status'] == 'PASS' and receipt['inputHashes'] == hashes
            assert sha(ROOT / receipt['log']) == receipt['logSha256']
            assert sha(ROOT / receipt['lineage']) == receipt['lineageSha256']
            lineage = read(ROOT / receipt['lineage'])
            assert sha(ROOT / 'artifacts/strict-post-close' / lineage['outputFile']) == lineage['outputSha256']
            stages.append(receipt)
            continue
        log = log_dir / (f'{ordinal:02d}-' + stage + '.log')
        assert not log.exists(), 'Preserve failed logs and choose a reviewed revision before retry'
        print(json.dumps({'status':'START','stage':stage}, ensure_ascii=False), flush=True)
        started = time.monotonic()
        old_argv = sys.argv
        try:
            sys.argv = [str(DISPATCHER), '--stage', stage, '--as-of', DAY, '--publish-canonical']
            with log.open('x', encoding='utf-8') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                dispatcher.main()
        finally:
            sys.argv = old_argv
        assert all(sha(ROOT / p) == h for p,h in hashes.items()), 'Inputs changed during numerical run'
        lineage = ART / 'numeric-lineage' / (stage + '-enumeration-lineage.json')
        scalar = dispatcher.adapter_for(stage)[0].scalar
        receipt = {'status':'PASS','asOf':DAY,'stage':stage,'seconds':round(time.monotonic()-started,3),
            'inputHashes':hashes,'log':log.relative_to(ROOT).as_posix(),'logSha256':sha(log),
            'lineage':lineage.relative_to(ROOT).as_posix(),'lineageSha256':sha(lineage),
            'uniqueCache':scalar.unique_distribution.cache_info()._asdict(),
            'independentDPCache':scalar.dp_distribution.cache_info()._asdict()}
        write(receipt_path, receipt)
        stages.append(receipt)
        print(json.dumps({'status':'PASS','stage':stage,'seconds':receipt['seconds'],
            'uniqueCache':receipt['uniqueCache'],'independentDPCache':receipt['independentDPCache']}), flush=True)
    write(log_dir / 'run-receipt.json', {'status':'PASS','asOf':DAY,'allFourCanonicalStagesPassed':True,
        'inputHashes':hashes,'stages':stages,'dispatcherSha256':DISPATCHER_SHA,'scriptSha256':sha(Path(__file__))})


if __name__ == '__main__':
    main()
