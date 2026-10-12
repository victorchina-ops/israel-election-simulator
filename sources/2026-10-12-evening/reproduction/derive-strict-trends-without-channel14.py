"""Safely regenerate dated Channel 14-OFF evidence from the latest reviewed audit.

Require an explicit matching --as-of. Counts are derived from the source cohort.
Each dated run is immutable: an existing run with different source hashes is
rejected; a complete identical run can only be reused. --check never computes or
writes, and --publish-snapshot explicitly promotes the validated dated snapshot.
The frozen 9 October derivation and its outputs are never edited or invoked.
"""
from pathlib import Path
from datetime import date
from itertools import permutations, product
import copy
import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = ROOT / 'artifacts/strict-post-close'
sys.dont_write_bytecode = True
sys.path.insert(0, str(REVIEWED))
from compressed_searchsorted_exact import integer_score_blocks, exact_counts

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def fail(message):
    raise SystemExit(message)

def is_channel14(row):
    if row.get('pollsterId') == 'next_data':
        return True
    channel = row.get('publisherChannel', row.get('channel'))
    if channel == 14 or isinstance(channel, str) and re.fullmatch(r'(?:14|c14|channel[ _-]?14|ערוץ\s*14|חדשות\s*14)', channel.strip(), re.I):
        return True
    publisher = row.get('publisher')
    return isinstance(publisher, str) and bool(re.fullmatch(r'(?:עכשיו\s*14|ערוץ\s*14|חדשות\s*14|channel\s*14)', publisher.strip(), re.I))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--as-of', required=True, help='Audited source date YYYY-MM-DD; must match both canonical audits and snapshot')
parser.add_argument('--run-id', default='reviewed', help='Dated evidence suffix; choose a new suffix for changed sources on the same day')
parser.add_argument('--output-root', default='artifacts/strict-post-close/without-channel14', help='Evidence directory inside this project artifacts directory')
parser.add_argument('--check', action='store_true', help='Read-only preflight: validate sources, dynamic counts and immutable destination')
parser.add_argument('--publish-snapshot', action='store_true', help='Promote only a validated dated snapshot to the site input')
args = parser.parse_args()
try:
    parsed_date = date.fromisoformat(args.as_of)
except ValueError:
    fail('--as-of must be a valid YYYY-MM-DD date')
if parsed_date.isoformat() != args.as_of:
    fail('--as-of must use the exact YYYY-MM-DD form')
if not args.run_id or any(character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for character in args.run_id):
    fail('--run-id must use only letters, digits, hyphens or underscores')
evidence_root = (ROOT / args.output_root).resolve()
if not evidence_root.is_relative_to((ROOT / 'artifacts').resolve()):
    fail('Evidence output must stay inside this project artifacts directory')
OUT = evidence_root / args.as_of / args.run_id
SITE_SNAPSHOT = ROOT / 'data/strict-party-trends-without-channel14.json'
FROZEN_SCRIPT = ROOT / 'scripts/derive-strict-trends-without-channel14-2026-10-09.py'
FROZEN_EVIDENCE = ROOT / 'artifacts/channel14-default-2026-10-09/strict-without14'
if OUT.resolve().is_relative_to(FROZEN_EVIDENCE.resolve()) or FROZEN_EVIDENCE.resolve().is_relative_to(OUT.resolve()):
    fail('The frozen 9 October evidence is immutable and cannot be a regeneration destination')

def publish(snapshot_path):
    value = read(snapshot_path)
    if value.get('asOf') != args.as_of:
        fail('Cannot publish a snapshot with a different audited date')
    if SITE_SNAPSHOT.exists() and str(read(SITE_SNAPSHOT).get('asOf', '')) > args.as_of:
        fail('Refusing to replace the current site snapshot with an older audited date')
    if not SITE_SNAPSHOT.exists() or SITE_SNAPSHOT.read_bytes() != snapshot_path.read_bytes():
        shutil.copy2(snapshot_path, SITE_SNAPSHOT)

base = read(REVIEWED / 'party-analysis.json')
bloc_base = read(REVIEWED / 'analysis.json')
original_snapshot = read(ROOT / 'data/strict-party-trends.json')
if any(value.get('asOf') != args.as_of for value in [base, bloc_base, original_snapshot]):
    fail('--as-of must match the reviewed party audit, bloc audit and canonical strict snapshot; regenerate those first')
history_path, parties_path = ROOT / 'data/poll-history.json', ROOT / 'data/parties.json'
assert sha(history_path) == base['historySha256'] == bloc_base['historySha256']
assert sha(parties_path) == base['partiesSha256']
original_hashes = {str(path.relative_to(ROOT)): sha(path) for path in [history_path, parties_path,
    REVIEWED / 'party-analysis.json', REVIEWED / 'analysis.json', ROOT / 'data/strict-party-trends.json']}
history = {row['id']: row for row in read(history_path)['polls']}
parties = [row for row in read(parties_path) if row['ballot']]
ids = [row['id'] for row in parties]
names = {row['id']: row['name'] for row in parties}
assert len(ids) > 0 and len(set(ids)) == len(ids)
assert ids == base['testedPartyIds']
cohort = copy.deepcopy(base['cohort'])
for row in cohort:
    row['eligibleFieldwork'] = row['eligibleStrict']
    row['channel14Excluded'] = is_channel14({**history[row['pollId']], **row})
    if row['channel14Excluded']:
        row['eligibleStrict'] = False
        row['selectionReason'] = 'channel14_disabled'
        row['exclusionReason'] = 'channel14_disabled'
eligible = {row['pollId']: row for row in cohort if row['eligibleStrict']}
selected_ids = [series['pollsterId'] for series in base['primary']['byPollster']
    if any(row['pollsterId'] == series['pollsterId'] for row in eligible.values())]
quality = read(ROOT / 'data/calibration.json')['pollsterQuality']
denominator = sum(quality[key]['weight'] for key in selected_ids)
weights = {key: quality[key]['weight'] / denominator for key in selected_ids}
assert len(weights) > 0 and len(eligible) > len(weights)
assert abs(sum(weights.values()) - 1) < 1e-12
groups = bloc_base['groups']
group_ids = list(groups)
assert group_ids and all(set(values).issubset(ids) for values in groups.values())
poll_count, series_count, party_count = len(eligible), len(weights), len(ids)
delta_count, individual_test_count, sign_patterns = poll_count - series_count, party_count * series_count, 2 ** series_count
series_lengths = {key: sum(row['pollsterId'] == key for row in eligible.values()) for key in selected_ids}
if any(length < 2 for length in series_lengths.values()):
    fail('Every selected reviewed series needs at least two eligible observations')
exact_permutations = math.prod(math.factorial(length) for length in series_lengths.values())
if exact_permutations > np.iinfo(np.int64).max:
    fail('The exact null universe exceeds the reviewed counter integer capacity; obtain a reviewed larger-integer counter before regeneration')
source_paths = [REVIEWED / 'party-analysis.json', REVIEWED / 'analysis.json', ROOT / 'data/strict-party-trends.json',
    history_path, parties_path, ROOT / 'data/calibration.json', REVIEWED / 'compressed_searchsorted_exact.py',
    REVIEWED / 'independent-compressed-counts.py', Path(__file__)]
input_manifest = {'schemaVersion': 1, 'asOf': args.as_of, 'runId': args.run_id, 'includeChannel14': False,
    'sourceHashes': {path.relative_to(ROOT).as_posix(): sha(path) for path in source_paths}}
plan = {'asOf': args.as_of, 'output': OUT.relative_to(ROOT).as_posix(), 'polls': poll_count, 'series': series_count,
    'deltas': delta_count, 'partyTests': party_count, 'individualTests': individual_test_count,
    'signPatterns': sign_patterns, 'exactPermutations': str(exact_permutations),
    'channel14ExcludedPollCount': sum(row['channel14Excluded'] for row in cohort),
    'unverifiedExcludedPollCount': sum(not row['eligibleFieldwork'] for row in cohort)}
reusable = False
if OUT.exists():
    if not OUT.is_dir() or not any(OUT.iterdir()):
        fail('The dated evidence destination already exists or is empty; refusing to overwrite a reserved or partial run. Choose a new --run-id')
    manifest_path = OUT / 'inputs-manifest.json'
    if not manifest_path.exists():
        fail('The dated evidence directory already contains unmanifested files; it is immutable. Choose a new --run-id')
    if read(manifest_path) != input_manifest:
        fail('The dated evidence source hashes differ; refusing to overwrite existing evidence. Choose a new --run-id')
    validation_path = OUT / 'validation.json'
    if not validation_path.exists():
        fail('The dated run is incomplete; existing partial evidence is preserved. Choose a new --run-id')
    previous_receipt = read(validation_path)
    if previous_receipt.get('status') != 'PASS' or previous_receipt.get('asOf') != args.as_of:
        fail('The dated run has no matching validated result')
    for name, expected_hash in previous_receipt.get('datedOutputHashes', {}).items():
        candidate = OUT / name
        if not candidate.exists() or sha(candidate) != expected_hash:
            fail('A dated evidence hash no longer matches the validated run')
    if not previous_receipt.get('datedOutputHashes'):
        fail('The dated run lacks immutable output hashes')
    reusable = True
if args.check:
    print(json.dumps({'status': 'PASS', 'readOnly': True, 'reusesExistingValidatedRun': reusable, **plan}, indent=2))
    raise SystemExit(0)
if reusable:
    if args.publish_snapshot:
        publish(OUT / 'strict-party-trends-without-channel14.json')
    print(json.dumps({'status': 'REUSED', 'wroteDatedEvidence': False, 'publishedSnapshot': args.publish_snapshot, **plan}, indent=2))
    raise SystemExit(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
try:
    OUT.mkdir(exist_ok=False)
except FileExistsError:
    fail('Another run reserved this dated evidence directory; refusing concurrent overwrite')
try:
    with (OUT / 'inputs-manifest.json').open('x', encoding='utf-8') as manifest_file:
        manifest_file.write(json.dumps(input_manifest, ensure_ascii=False, indent=2) + '\n')
except FileExistsError:
    fail('Another run reserved this dated evidence directory; refusing concurrent overwrite')

def bh(rows, pkey='pValue', qkey='qValue'):
    next_value = 1.
    for rank, row in reversed(list(enumerate(sorted(rows, key=lambda item: item[pkey]), 1))):
        next_value = min(next_value, row[pkey] * len(rows) / rank, 1.)
        row[qkey] = next_value

def timing(poll_id, axis):
    row = eligible[poll_id]
    if axis == 'publication':
        return float(date.fromisoformat(row['publicationDate']).toordinal())
    assert row['fieldworkStart'] >= base['closure']['firstEligibleFieldworkDate']
    return (date.fromisoformat(row['fieldworkStart']).toordinal() + date.fromisoformat(row['fieldworkEnd']).toordinal()) / 2

def analyze(axis):
    records, individual, blocks, observed, all_y, all_t, all_orders = [], [], [], [], [], [], []
    for institute in selected_ids:
        poll_ids = sorted([key for key, row in eligible.items() if row['pollsterId'] == institute], key=lambda key: timing(key, axis))
        times = np.asarray([timing(key, axis) for key in poll_ids]); times -= times[0]
        assert len(poll_ids) >= 2 and np.all(np.diff(times) > 0)
        seats = np.asarray([[history[key]['seats'].get(party, 0) for party in ids] for key in poll_ids], dtype=np.int64)
        assert np.all(seats.sum(axis=1) == 120)
        assert np.all(seats >= 0)
        deltas = np.diff(seats, axis=0)
        centered = times - times.mean()
        coefficients = 7 * centered / (centered @ centered)
        slopes = coefficients @ seats
        D = np.diff(np.eye(len(poll_ids)), axis=0); dt = D @ times
        z = np.linalg.solve(D @ D.T, dt); gls = 7 * z / (dt @ z)
        assert np.allclose(slopes, gls @ deltas, atol=1e-12)
        orders = np.asarray(list(permutations(range(len(poll_ids)))))
        null_slopes = np.einsum('i,pij->pj', coefficients, seats[orders])
        assert len(orders) == math.factorial(len(poll_ids))
        assert np.allclose(null_slopes.mean(axis=0), 0, atol=1e-12)
        bloc_seats = np.asarray([[sum(row[ids.index(party)] for party in groups[group]) for group in group_ids] for row in seats], dtype=np.int64)
        outcomes = np.concatenate([seats, bloc_seats], axis=1)
        outcome_slopes = coefficients @ outcomes
        blocks.append(integer_score_blocks(times, outcomes, orders, weights[institute]))
        observed.append(weights[institute] * outcome_slopes)
        all_y.append(outcomes); all_t.append(times); all_orders.append(orders)
        rows = []
        for j, party in enumerate(ids):
            slope = float(slopes[j]) if abs(slopes[j]) > 1e-12 else 0.
            entry = {'pollsterId': institute, 'partyId': party, 'partyName': names[party], 'nPolls': len(poll_ids),
                'nDeltas': len(poll_ids) - 1, 'weight': weights[institute], 'firstPublication': history[poll_ids[0]]['date'],
                'lastPublication': history[poll_ids[-1]]['date'], 'firstSeats': int(seats[0, j]), 'lastSeats': int(seats[-1, j]),
                'netDelta': int(deltas[:, j].sum()), 'slopePerWeek': slope,
                'pValue': float(np.mean(np.abs(null_slopes[:, j]) >= abs(slope) - 1e-12)),
                'constantSeatSeries': bool(np.all(seats[:, j] == seats[0, j])), 'seats': seats[:, j].tolist(), 'deltas': deltas[:, j].tolist()}
            rows.append(entry); individual.append(entry)
        records.append({'pollsterId': institute, 'weight': weights[institute], 'pollIds': poll_ids,
            'publicationDates': [history[key]['date'] for key in poll_ids], 'timeDaysFromFirst': times.tolist(), 'parties': rows})
    bh(individual)
    observed = np.sum(observed, axis=0)
    exact = exact_counts(blocks, observed, tolerance=1e-12)
    sign_patterns = np.asarray(list(product([-1, 1], repeat=len(records))))
    weighted_slopes = np.asarray([weights[institute] * (7 * (times - times.mean()) / ((times - times.mean()) @ (times - times.mean())) @ outcomes)
        for institute, times, outcomes in zip(selected_ids, all_t, all_y)])
    flipped = sign_patterns @ weighted_slopes
    overall = []
    for j, party in enumerate(ids):
        rows = [series['parties'][j] for series in records]
        overall.append({'partyId': party, 'partyName': names[party],
            'weightedFirstSeats': sum(row['weight'] * row['firstSeats'] for row in rows),
            'weightedLastSeats': sum(row['weight'] * row['lastSeats'] for row in rows),
            'weightedNetDelta': sum(row['weight'] * row['netDelta'] for row in rows), 'slopePerWeek': float(observed[j]),
            'pValue': exact['pValues'][j], 'wholeSeriesSignFlipP': float(np.mean(np.abs(flipped[:, j]) >= abs(observed[j]) - 1e-12)),
            'upwardSeries': int(np.sum(weighted_slopes[:, j] > 1e-12)), 'downwardSeries': int(np.sum(weighted_slopes[:, j] < -1e-12)),
            'flatSeries': int(np.sum(np.abs(weighted_slopes[:, j]) <= 1e-12)),
            'zeroSeatsThroughout': all(max(row['seats']) == 0 for row in rows)})
    bh(overall); bh(overall, 'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ')
    bloc_overall = []
    for j, group in enumerate(group_ids, start=len(ids)):
        bloc_overall.append({'group': group,
            'weightedNetDelta': sum(row['weightedNetDelta'] for row in overall if row['partyId'] in groups[group]),
            'slopePerWeek': float(observed[j]), 'pValue': exact['pValues'][j],
            'wholeInstituteSignFlipP': float(np.mean(np.abs(flipped[:, j]) >= abs(observed[j]) - 1e-12))})
        assert abs(sum(row['slopePerWeek'] for row in overall if row['partyId'] in groups[group]) - observed[j]) < 1e-12
    bh(bloc_overall); bh(bloc_overall, 'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ')
    assert abs(sum(row['weightedNetDelta'] for row in overall)) < 1e-12
    assert abs(sum(row['slopePerWeek'] for row in overall)) < 1e-12
    return {'timeAxis': axis, 'nPolls': len(eligible), 'nSeries': len(records), 'nDeltas': len(eligible) - len(records),
        'overall': overall, 'byPollster': records, 'exactCounting': exact, 'wholeSeriesSignPatterns': len(sign_patterns),
        'blocOverall': bloc_overall, 'significantIndividualRaw': [row for row in individual if row['pValue'] < .05],
        'significantIndividualBH': [row for row in individual if row['qValue'] < .05]}, (all_t, all_y, all_orders, observed)

primary, validation_inputs = analyze('fieldwork-midpoint')
secondary, _ = analyze('publication')
assert primary['exactCounting']['nPermutations'] == exact_permutations
assert primary['wholeSeriesSignPatterns'] == sign_patterns
report = {'asOf': base['asOf'], 'includeChannel14': False, 'historySha256': base['historySha256'], 'partiesSha256': base['partiesSha256'],
    'cohort': cohort, 'closure': base['closure'], 'normalizedHistoricalWeights': weights, 'testedPartyIds': ids,
    'method': base['method'], 'limitations': base['limitations'], 'groups': groups, 'primary': primary, 'publicationDateSensitivity': secondary,
    'sourceAnalysisSha256': sha(REVIEWED / 'party-analysis.json'), 'selectionChange': 'Only Channel 14 publisher selection changes; the source cohort is preserved'}
report['outcomeOrder'] = ids + group_ids
report['dependencies'] = {'calibrationSha256': sha(ROOT / 'data/calibration.json'),
    'primaryCounterSha256': sha(REVIEWED / 'compressed_searchsorted_exact.py'),
    'independentCounterSha256': sha(REVIEWED / 'independent-compressed-counts.py'), 'derivationScriptSha256': sha(Path(__file__))}
report['method'] = {**report['method'], 'family': f'Predeclared {party_count} modeled ballot parties, BH across {party_count} overall tests and separately {individual_test_count} institute-party tests; {len(groups)} bloc tests corrected separately.',
    'sensitivity': f'Whole-institute slope sign-flips: {sign_patterns} patterns on {series_count} eligible institute series; BH separately across {party_count} parties and {len(groups)} bloc definitions.'}
write(OUT / 'party-analysis.json', report)

# Independent regression formulation and bounded direct Cartesian tail counting
# verifies the primary formula/searchsorted result; no simulation is substituted.
spec = importlib.util.spec_from_file_location('without14_independent_counts', REVIEWED / 'independent-compressed-counts.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
times_by_series, outcomes_by_series, orders_by_series, observed = validation_inputs
independent_blocks, independent_slopes = [], []
for institute, times, outcomes, orders in zip(selected_ids, times_by_series, outcomes_by_series, orders_by_series):
    design = np.stack([np.ones(len(times)), times / 7], axis=1)
    slope = np.linalg.lstsq(design, outcomes, rcond=None)[0][1]
    independent_slopes.append(weights[institute] * slope)
    independent_blocks.append(helper.score_blocks(times, outcomes, orders, weights[institute]))
assert np.allclose(np.sum(independent_slopes, axis=0), observed, atol=1e-12)
nonzero = [index for index, value in enumerate(observed) if abs(value) > 1e-12]
# The exact primary counter covers every outcome. Independently verify the three
# smallest nonconstant null spaces plus all constant-zero outcomes directly;
# no enormous full Cartesian product is needed for this algorithm regression.
sampled_indexes = sorted(nonzero, key=lambda index: math.prod(primary['exactCounting']['halfSizes'][index]))[:3]
sampled_indexes += [index for index, value in enumerate(observed) if abs(value) <= 1e-12]
sampled_blocks = [[series[index] for index in sampled_indexes] for series in independent_blocks]
counts, total, compressed_sizes = helper.direct_tail_counts(sampled_blocks, observed[sampled_indexes], tolerance=1e-12)
assert [int(value) for value in counts] == [primary['exactCounting']['extremeCounts'][index] for index in sampled_indexes]
assert total == primary['exactCounting']['nPermutations']
independent = {'status': 'PASS', 'method': 'Independent lstsq slopes for all outcomes; sampled direct Cartesian tail enumeration with integer score multiplicities',
    'exactPrimaryCounter': 'Inherited reviewed compressed_searchsorted_exact.py; exact multiplicities over every within-series permutation',
    'independentlyCountedOutcomeIds': [(ids + group_ids)[index] for index in sampled_indexes],
    'independentTailScope': 'Three smallest nonconstant null spaces and every zero-statistic outcome; not a new all-outcome exhaustive independent audit',
    'nPermutationsExact': str(total), 'extremeCountsExact': [str(int(value)) for value in counts], 'compressedHalfSizes': compressed_sizes,
    'historySha256': base['historySha256'], 'partiesSha256': base['partiesSha256'], 'primaryAnalysisSha256': sha(OUT / 'party-analysis.json')}
write(OUT / 'independent-numeric-audit.json', independent)

snapshot = copy.deepcopy(original_snapshot)
snapshot['includeChannel14'] = False
snapshot['selectionPolicy'] = {'includeChannel14': False,
    'excludedPollsterIds': sorted({row['pollsterId'] for row in cohort if row['channel14Excluded']} - set(selected_ids)),
    'preservesSourceHistory': True}
snapshot['coverage'].update({'pollCount': poll_count, 'seriesCount': series_count, 'deltaCount': delta_count,
    'partyCount': party_count, 'excludedPollCount': len(cohort) - len(eligible),
    'from': min(row['fieldworkStart'] for row in eligible.values()), 'to': max(row['fieldworkEnd'] for row in eligible.values()),
    'fieldworkExcludedPollCount': sum(not row['eligibleFieldwork'] for row in cohort),
    'unverifiedExcludedPollCount': sum(not row['eligibleFieldwork'] for row in cohort),
    'channel14ExcludedPollCount': sum(row['channel14Excluded'] for row in cohort)})
snapshot['weights'] = [{**row, 'weight': weights[row['pollsterId']], 'nPolls': series_lengths[row['pollsterId']]}
    for row in original_snapshot['weights'] if row['pollsterId'] in selected_ids]
snapshot['rows'] = []
labels = {row['pollsterId']: row['label'] for row in original_snapshot['weights']}
for row in primary['overall']:
    details = []
    for series in primary['byPollster']:
        entry = next(item for item in series['parties'] if item['partyId'] == row['partyId'])
        details.append({**entry, 'label': labels[series['pollsterId']], 'pollIds': series['pollIds'],
            'dates': series['publicationDates'], 'timeDaysFromFirst': series['timeDaysFromFirst']})
    snapshot['rows'].append({**row, 'byPollster': details})
for row in snapshot['cohort']:
    original = next(item for item in cohort if item['pollId'] == row['pollId'])
    row['eligibleFieldwork'] = original['eligibleFieldwork']
    row['channel14Excluded'] = original['channel14Excluded']
    row['eligibleStrict'] = original['eligibleStrict']
    if row['channel14Excluded']:
        row['exclusionReason'] = 'channel14_disabled'
        row['reason'] = 'הוחרג לפי מתג סקרי ערוץ 14; נתוני המקור נשמרים. מועד האיסוף אומת.' if row['eligibleFieldwork'] else 'הוחרג לפי מתג סקרי ערוץ 14; מועד האיסוף גם לא אומת.'
snapshot['methodology'].update({'permutations': total, 'permutationsExact': str(total), 'signPatterns': sign_patterns,
    'partyTests': party_count, 'individualTests': individual_test_count,
    'usesCurrentControls': 'channel14_switch_only', 'channel14SwitchSelectsPrecomputedSnapshot': True})
snapshot['provenance'].update({'analysisSha256': sha(OUT / 'party-analysis.json'),
    'script': str(Path(__file__).relative_to(ROOT)), 'analysisScript': str(Path(__file__).relative_to(ROOT)),
    'sourceAnalysisSha256': sha(REVIEWED / 'party-analysis.json'), 'independentAuditSha256': sha(OUT / 'independent-numeric-audit.json')})
dated_snapshot = OUT / 'strict-party-trends-without-channel14.json'
write(dated_snapshot, snapshot)
receipt = {'status': 'PASS', 'asOf': base['asOf'], 'polls': poll_count, 'series': series_count, 'deltas': delta_count,
    'partyTests': party_count, 'individualTests': individual_test_count,
    'signPatterns': sign_patterns, 'exactPermutations': str(total), 'immutableSourceHashes': original_hashes,
    'primarySignificantAfterBH': [row['partyId'] for row in primary['overall'] if row['qValue'] < .05],
    'sensitivitySignificantAfterBH': [row['partyId'] for row in primary['overall'] if row['wholeSeriesSignFlipQ'] < .05],
    'snapshotSha256': sha(dated_snapshot),
    'analysisSha256': sha(OUT / 'party-analysis.json'), 'independentAuditSha256': sha(OUT / 'independent-numeric-audit.json')}
assert all(sha(ROOT / path) == original_hash for path, original_hash in original_hashes.items())
assert all(sha(ROOT / path) == original_hash for path, original_hash in input_manifest['sourceHashes'].items())
for counter in ['compressed_searchsorted_exact.py', 'independent-compressed-counts.py']:
    shutil.copy2(REVIEWED / counter, OUT / counter)
receipt['datedOutputHashes'] = {name: sha(OUT / name) for name in ['party-analysis.json', 'independent-numeric-audit.json',
    'strict-party-trends-without-channel14.json', 'compressed_searchsorted_exact.py', 'independent-compressed-counts.py']}
write(OUT / 'validation.json', receipt)
if args.publish_snapshot:
    publish(dated_snapshot)
print(json.dumps({'status': 'PASS', 'publishedSnapshot': args.publish_snapshot, **plan,
    'primarySignificantAfterBH': receipt['primarySignificantAfterBH'],
    'sensitivitySignificantAfterBH': receipt['sensitivitySignificantAfterBH']}, indent=2))
