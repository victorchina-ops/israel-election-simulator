import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';

const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const auditPath = 'artifacts/strict-post-close/party-analysis.json';
const audit = read(auditPath);
const blocAudit = read('artifacts/strict-post-close/analysis.json');
const priorAudit = read('artifacts/strict-post-close/archive-2026-10-02/party-analysis.json');
const october4Audit = read('artifacts/strict-post-close/archive-2026-10-04/party-analysis.json');
const october5Audit = read('artifacts/strict-post-close/archive-2026-10-05/party-analysis.json');
const october6Audit = read('artifacts/strict-post-close/archive-2026-10-06/party-analysis.json');
const october7Audit = read('artifacts/strict-post-close/archive-2026-10-07/party-analysis.json');
const october7BlocAudit = read('artifacts/strict-post-close/archive-2026-10-07/analysis.json');
const october1Audit = read('artifacts/strict-post-close/archive-2026-10-01/party-analysis.json');
const independent = read('artifacts/strict-post-close/party-independent.json');
const snapshot = read('data/strict-party-trends.json');
const current = read('data/current-polls.json');
const history = read('data/poll-history.json');
const sources = read('data/sources.json');
const october8BaselineCurrent = read('data/history/before-c13-metadata-2026-10-08/data/current-polls.json');
const october8BaselineHistory = read('data/history/before-c13-metadata-2026-10-08/data/poll-history.json');
// Freeze the morning metadata revision separately from the later new-poll release.
// Historical stage checks must not treat subsequently replaced institutes as changes to that stage.
const october8MetadataFolder = 'data/history/before-new-polls-2026-10-08/';
const october8MetadataAudit = read(october8MetadataFolder + auditPath);
const october8MetadataCurrent = read(october8MetadataFolder + 'data/current-polls.json');
const october8MetadataHistory = read(october8MetadataFolder + 'data/poll-history.json');
const october8MetadataSources = read(october8MetadataFolder + 'data/sources.json');
const october8EveningFolder = 'data/history/before-maariv-2026-10-09/';
const october8EveningAudit = read(october8EveningFolder + auditPath);
const october8EveningSnapshot = read(october8EveningFolder + 'data/strict-party-trends.json');
const parties = read('data/parties.json');
const close = (actual, expected, label = '') => assert.ok(Math.abs(actual - expected) < 1e-11, `${label}: ${actual} != ${expected}`);
const sum = values => values.reduce((total, value) => total + value, 0);
const average = values => sum(values) / values.length;
const slope = (times, seats) => {
  const center = average(times), centered = times.map(value => value - center);
  return 7 * sum(centered.map((value, index) => value * seats[index])) / sum(centered.map(value => value * value));
};
function bh(rows, pKey, qKey) {
  const order = rows.map((row, index) => ({index, p: row[pKey]})).sort((a, b) => a.p - b.p);
  let running = 1;
  for (let i = order.length - 1; i >= 0; i--) {
    const item = order[i];
    running = Math.min(running, item.p * order.length / (i + 1));
    close(rows[item.index][qKey], running, `${rows[item.index].partyId} ${qKey}`);
  }
}
function permutations(values) {
  assert.ok(values.length <= 8, 'Dense permutations are reserved for small independent equivalence toys');
  if (values.length <= 1) return [values];
  return values.flatMap((value, index) => permutations(values.filter((_, i) => i !== index)).map(tail => [value, ...tail]));
}
const factorial = n => {
  let value = 1n;
  for (let i = 2n; i <= BigInt(n); i++) value *= i;
  return value;
};
const exactProbability = (count, total) => Number(BigInt(count)) / Number(BigInt(total));
function assertNearestFloatFromExactRatio(actual, numerator, denominator) {
  let count = BigInt(numerator), total = BigInt(denominator);
  assert.ok(total > 0n && count >= -total && count <= total);
  assert.ok(Number.isFinite(actual) && Math.abs(actual) <= 1);
  if (count === 0n) {
    assert.equal(actual, 0);
    return;
  }
  assert.equal(Math.sign(actual), count < 0n ? -1 : 1);
  if (count < 0n) count = -count;
  const bytes = Buffer.alloc(8);
  bytes.writeDoubleLE(Math.abs(actual));
  const bits = bytes.readBigUInt64LE();
  assert.ok(bits > 0n && bits < 0x7ff0000000000000n);
  const ratio = encoding => {
    const exponent = Number((encoding >> 52n) & 0x7ffn);
    const fraction = encoding & ((1n << 52n) - 1n);
    const significand = exponent === 0 ? fraction : (1n << 52n) + fraction;
    const power = exponent === 0 ? -1074 : exponent - 1023 - 52;
    return power >= 0 ? [significand << BigInt(power), 1n] : [significand, 1n << BigInt(-power)];
  };
  const [value, scale] = ratio(bits);
  const [lower, lowerScale] = ratio(bits - 1n), [upper, upperScale] = ratio(bits + 1n);
  // Compare the exact integer ratio with both binary64 rounding midpoints.
  // This avoids separately rounding huge numerator and denominator to Number.
  const lowerDifference = count * (2n * lowerScale * scale) - total * (lower * scale + value * lowerScale);
  const upperDifference = count * (2n * upperScale * scale) - total * (upper * scale + value * upperScale);
  const even = (bits & 1n) === 0n;
  assert.ok(lowerDifference > 0n || (lowerDifference === 0n && even), 'Below the exact nearest-float rounding interval');
  assert.ok(upperDifference < 0n || (upperDifference === 0n && even), 'Above the exact nearest-float rounding interval');
}
const scalarPermutationCache = new Map();
function scalarPermutationHistogram(times, seats) {
  assert.equal(times.length, seats.length);
  assert.ok(seats.length >= 2 && seats.every(Number.isSafeInteger));
  assert.ok(times.every(value => Number.isFinite(value) && Number.isSafeInteger(value * 2)));
  const orderedSeats = [...seats].sort((a, b) => a - b);
  const key = JSON.stringify([times, orderedSeats]);
  if (scalarPermutationCache.has(key)) return scalarPermutationCache.get(key);
  const doubled = times.map(value => value * 2), n = seats.length;
  const timeTotal = sum(doubled);
  const coefficients = doubled.map(value => n * value - timeTotal);
  const denominator = sum(coefficients.map((value, i) => value * doubled[i]));
  assert.ok(denominator > 0 && Number.isSafeInteger(denominator));
  const frequencies = new Map();
  for (const value of orderedSeats) frequencies.set(value, (frequencies.get(value) ?? 0) + 1);
  const labels = [...frequencies.keys()], remaining = [...frequencies.values()];
  const multiplicity = remaining.reduce((value, count) => value * factorial(count), 1n);
  const scores = new Map();
  let assignments = 0n;
  function visit(position, score) {
    if (position === n) {
      assert.ok(Number.isSafeInteger(score));
      scores.set(score, (scores.get(score) ?? 0n) + multiplicity);
      assignments++;
      return;
    }
    for (let index = 0; index < labels.length; index++) {
      if (!remaining[index]) continue;
      remaining[index]--;
      visit(position + 1, score + coefficients[position] * labels[index]);
      remaining[index]++;
    }
  }
  visit(0, 0);
  const total = [...scores.values()].reduce((value, mass) => value + mass, 0n);
  assert.equal(total, factorial(n), 'Every labeled permutation retains its exact multiplicity');
  assert.equal([...scores].reduce((value, [score, mass]) => value + BigInt(score) * mass, 0n), 0n);
  assert.equal(assignments * multiplicity, total);
  const result = {scores, total, assignments, denominator};
  scalarPermutationCache.set(key, result);
  return result;
}
function scalarPermutationProbability(times, seats, observed) {
  const histogram = scalarPermutationHistogram(times, seats);
  const cutoff = Math.abs(observed) - 1e-12;
  let extreme = 0n;
  for (const [score, mass] of histogram.scores) {
    if (Math.abs(14 * score / histogram.denominator) >= cutoff) extreme += mass;
  }
  assert.ok(extreme >= 0n && extreme <= histogram.total);
  return exactProbability(extreme, histogram.total);
}
const fileSha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function pythonHexFloat(value) {
  const parts = /^(-?)0x([0-9a-f]+)\.([0-9a-f]+)p([+-]?\d+)$/i.exec(value);
  assert.ok(parts, `invalid reviewed float encoding: ${value}`);
  const significand = BigInt('0x' + parts[2] + parts[3]);
  assert.ok(significand <= BigInt(Number.MAX_SAFE_INTEGER));
  return (parts[1] ? -1 : 1) * Number(significand) * 2 ** (Number(parts[4]) - 4 * parts[3].length);
}
let verifiedBlocBoundary;
function reviewedBlocBoundary(checked) {
  if (verifiedBlocBoundary) return verifiedBlocBoundary;
  const path = 'artifacts/poll-checks/2026-10-20-evening/numeric-compatibility/float-boundary/focused-common-threshold-review.json';
  assert.equal(fileSha256(path), 'a0ece1bb9589de317a739a043fe649dcfe13b65b2c7e6dfc94c4742027d9b6ba');
  const proof = read(path);
  assert.equal(proof.status, 'PASS');
  assert.equal(proof.outcome, 'opposition_raam');
  for (const [file, hash] of Object.entries(proof.inputSha256)) assert.equal(fileSha256(file), hash, file);
  assert.equal(fileSha256('artifacts/strict-post-close/compressed_searchsorted_exact.py'),
    '22918f50bec91553d715600f1949f45a8140779eaf81b956fdcf623f98b6c1a1');
  assert.equal(fileSha256('artifacts/strict-post-close/independent-compressed-counts.py'),
    '8a725d5bfca3a0f40a8f6e72f038e76877ec88e0d444b8fbf07686da3f1b924d');
  assert.equal(fileSha256('scripts/exact_scalar_marginals_2026_10_20.py'),
    'ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035');
  const index = checked.groups.indexOf(proof.outcome);
  assert.ok(index >= 0);
  assert.equal(blocAudit.primary.overall[index].group, proof.outcome);
  assert.equal(blocAudit.primary.overall[index].slopePerWeek, pythonHexFloat(proof.primaryObservedHex));
  assert.equal(checked.slopes[index], pythonHexFloat(proof.independentObservedHex));
  assert.equal(proof.primaryObserved, pythonHexFloat(proof.primaryObservedHex));
  assert.equal(proof.independentObserved, pythonHexFloat(proof.independentObservedHex));
  assert.equal(proof.toleranceUnchanged, 1e-12);
  assert.equal(Math.abs(proof.primaryObserved) - 1e-12, pythonHexFloat(proof.primaryCutoffHex));
  assert.equal(Math.abs(proof.independentObserved) - 1e-12, pythonHexFloat(proof.independentCutoffHex));
  assert.equal(proof.observedDifference, proof.primaryObserved - proof.independentObserved);
  assert.equal(proof.observedDifferenceInUlps, 16);
  assert.equal(proof.commonThresholdExactIntegerMatch, true);
  assert.equal(proof.independentOwnThresholdIntegerMatch, true);
  assert.equal(proof.allPrimaryUniqueAndIndependentDpScalarBlocksByteIdentical, true);
  assert.equal(proof.nullMassRestoredByExactLabeledMultiplicities, true);
  assert.equal(proof.numericalOutputsOrFrozenHelpersModified, false);
  assert.equal(BigInt(proof.totalPermutationsExact), BigInt(checked.totalExact));
  assert.equal(BigInt(proof.archivedPrimaryExtremeCountExact),
    BigInt(blocAudit.primary.exactCounting.extremeCountsExact[index]));
  assert.equal(BigInt(proof.archivedIndependentExtremeCountExact), BigInt(checked.countsExact[index]));
  assert.equal(BigInt(proof.independentCounterAtPrimaryObservedCountExact), BigInt(proof.archivedPrimaryExtremeCountExact));
  assert.equal(BigInt(proof.independentCounterAtOwnObservedCountExact), BigInt(proof.archivedIndependentExtremeCountExact));
  assert.equal(BigInt(proof.boundaryMultiplicityDifferenceExact),
    BigInt(proof.archivedIndependentExtremeCountExact) - BigInt(proof.archivedPrimaryExtremeCountExact));
  assert.equal(proof.boundaryProbabilityMass,
    exactProbability(proof.boundaryMultiplicityDifferenceExact, proof.totalPermutationsExact));
  assert.equal(proof.primaryP, exactProbability(proof.archivedPrimaryExtremeCountExact, proof.totalPermutationsExact));
  assert.equal(proof.independentP, exactProbability(proof.archivedIndependentExtremeCountExact, proof.totalPermutationsExact));
  assert.equal(proof.commonThresholdP, proof.primaryP);
  assert.equal(proof.seriesBlocks.length, blocAudit.primary.byPollster.length);
  for (const [position, support] of proof.seriesBlocks.entries()) {
    const series = blocAudit.primary.byPollster[position];
    assert.equal(support.pollsterId, series.pollsterId);
    assert.deepEqual(support.timeDays, series.timeDaysFromFirst);
    assert.deepEqual(support.seats, series.groups.find(row => row.group === proof.outcome).seats);
    assert.equal(support.weight, series.weight);
    assert.equal(support.n, series.pollIds.length);
    const histogram = scalarPermutationHistogram(support.timeDays, support.seats);
    const ordered = [...histogram.scores].sort(([a], [b]) => a - b);
    assert.equal(ordered.length, support.uniqueScores);
    assert.equal(BigInt(support.rawPermutationMass), histogram.total);
    assert.deepEqual(ordered.map(([, mass]) => mass), support.exactMultiplicities.map(BigInt));
    const values = Buffer.alloc(8 * ordered.length);
    const scale = 14 * support.weight / histogram.denominator;
    ordered.forEach(([score], i) => {
      const value = score * scale;
      assert.equal(value, pythonHexFloat(support.valuesHex[i]));
      values.writeDoubleLE(value, i * 8);
    });
    assert.equal(crypto.createHash('sha256').update(values).digest('hex'), support.floatValuesSha256);
  }
  verifiedBlocBoundary = proof;
  return proof;
}
const verifiedCurrentBlocBoundaries = new Map();
function reviewedCurrentBlocBoundary(checked, index) {
  const identity = blocAudit.primary.overall[index].group;
  if (verifiedCurrentBlocBoundaries.has(identity)) return verifiedCurrentBlocBoundaries.get(identity);
  assert.match(current.asOf, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(identity, /^[a-z][a-z0-9_]*$/);
  assert.equal(blocAudit.asOf, current.asOf);
  assert.equal(audit.asOf, current.asOf);
  assert.equal(history.asOf, current.asOf);
  const folder = `artifacts/poll-checks/${current.asOf}/`;
  const validation = read(folder + 'strict-validation.json');
  assert.equal(validation.status, 'PASS');
  assert.equal(validation.passed, true);
  assert.equal(validation.asOf, current.asOf);
  // The reviewed21Oct diagnosis preserves both operational floating predicates.
  // Its independent addition count does not match the primary subtraction count
  // at the same statistic; require its four-count proof instead of claiming that.
  const predicateDiagnosis = current.asOf === '2026-10-21' && identity === 'opposition';
  const validatorPath = predicateDiagnosis
    ? 'scripts/validate-strict-trends-2026-10-21-predicate-r1.py'
    : `scripts/validate-strict-trends-${current.asOf}.py`;
  assert.equal(fileSha256(validatorPath), validation.validatorSha256, 'Current validator source is hash-bound');
  const manifest = read(folder + 'before/manifest.json');
  assert.equal(fileSha256(folder + 'before/manifest.json'), validation.checkpointManifestSha256);
  const path = folder + (predicateDiagnosis
    ? 'numeric-boundaries/bloc-opposition-predicate-r1.json'
    : `numeric-boundaries/bloc-${identity}.json`);
  assert.equal(fileSha256(path), validation.boundaryReviewHashes[path], 'Use only the current validated boundary receipt');
  const proof = read(path);
  assert.equal(proof.status, 'PASS');
  assert.equal(proof.asOf, current.asOf);
  assert.equal(proof.kind, 'bloc');
  assert.equal(proof.identity, identity);
  assert.deepEqual(proof.inputHashes, validation.inputHashes);
  for (const [file, hash] of Object.entries(proof.inputHashes)) assert.equal(fileSha256(file), hash, file);
  for (const family of ['candidateHashes', 'sourceEvidenceHashes', 'numericLineageHashes']) {
    assert.ok(Object.keys(validation[family]).length > 0, family);
    for (const [file, hash] of Object.entries(validation[family])) assert.equal(fileSha256(file), hash, file);
  }
  for (const [file, hash] of Object.entries({
    'artifacts/strict-post-close/compressed_searchsorted_exact.py': '22918f50bec91553d715600f1949f45a8140779eaf81b956fdcf623f98b6c1a1',
    'artifacts/strict-post-close/independent-compressed-counts.py': '8a725d5bfca3a0f40a8f6e72f038e76877ec88e0d444b8fbf07686da3f1b924d',
    'scripts/exact_scalar_marginals_2026_10_20.py': 'ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035',
  })) {
    assert.equal(fileSha256(file), hash, file);
    assert.equal(manifest.files[file], hash, file);
  }
  for (const [file, hash] of Object.entries(validation.exactArithmeticRepairInputHashes)) {
    assert.equal(fileSha256(file), hash, file);
    assert.equal(manifest.files[file], hash, file);
  }
  assert.equal(checked.groups[index], identity);
  assert.equal(blocAudit.primary.overall[index].slopePerWeek, pythonHexFloat(proof.primaryObservedHex));
  assert.equal(checked.slopes[index], pythonHexFloat(proof.independentObservedHex));
  assert.equal(proof.toleranceUnchanged, 1e-12);
  const total = blocAudit.primary.byPollster.reduce((product, series) => product * factorial(series.pollIds.length), 1n);
  assert.equal(total, expectedCurrentPermutationTotal);
  assert.equal(total, BigInt(proof.totalExact));
  assert.equal(total, BigInt(checked.totalExact));
  assert.equal(total, BigInt(validation.exactPermutations));
  const primary = BigInt(blocAudit.primary.exactCounting.extremeCountsExact[index]);
  const own = BigInt(checked.countsExact[index]);
  assert.notEqual(primary, own, 'This proof branch is only for an actual integer-count disagreement');
  assert.equal(primary, BigInt(proof.primaryExtremeCountExact));
  assert.equal(own, BigInt(proof.independentExtremeCountExact));
  if (predicateDiagnosis) {
    const diagnosisPath = folder + 'numeric-boundaries/opposition-predicate-diagnosis.json';
    const reviewPath = folder + 'numeric-boundaries/opposition-predicate-independent-review.json';
    assert.equal(proof.diagnosisPath, diagnosisPath);
    assert.equal(proof.independentReviewPath, reviewPath);
    assert.equal(fileSha256(diagnosisPath), proof.diagnosisSha256);
    assert.equal(proof.diagnosisSha256, 'c414a4dc5e979f8da467296c038035d7dffb937961fee26945cfb665d78ff74a');
    assert.equal(fileSha256(reviewPath), proof.independentReviewSha256);
    assert.equal(proof.independentReviewSha256, '2fef6af558447f563218c62d2423ecb1cd1244e9e5adf38fabd7c27726a04cce');
    assert.equal(fileSha256(proof.reproducerPath), proof.reproducerSha256);
    assert.equal(proof.reproducerSha256, 'eba421c317aa995007faa76f48bbffdf87cd2607f11a5b35e589a0eb2ee76492');
    assert.equal(proof.baseValidatorSha256, '26508c81b8c6f664105edb69d0a1a7b757b21904081e7fdd3bde1230f8e90a7a');
    assert.equal(fileSha256('scripts/validate-strict-trends-2026-10-21.py'), proof.baseValidatorSha256);
    assert.equal(proof.adapterSha256, validation.validatorSha256);
    const diagnosis = read(diagnosisPath), review = read(reviewPath);
    assert.equal(diagnosis.status, 'PASS');
    assert.equal(review.status, 'PASS');
    assert.equal(diagnosis.asOf, current.asOf);
    assert.equal(review.asOf, current.asOf);
    assert.equal(diagnosis.outcome, identity);
    assert.equal(review.outcome, identity);
    assert.equal(review.diagnosisSha256, proof.diagnosisSha256);
    assert.equal(review.reproducerSha256, proof.reproducerSha256);
    assert.deepEqual(diagnosis.inputHashes, review.inputHashes);
    for (const [file, hash] of Object.entries(diagnosis.inputHashes)) assert.equal(fileSha256(file), hash, file);
    for (const key of ['primaryObservedHex', 'independentObservedHex', 'primaryExtremeCountExact', 'independentExtremeCountExact', 'totalExact']) {
      assert.equal(proof[key], diagnosis[key], key);
      assert.equal(proof[key], review[key], key);
    }
    const observedBits = Buffer.alloc(16);
    observedBits.writeDoubleLE(pythonHexFloat(proof.primaryObservedHex), 0);
    observedBits.writeDoubleLE(pythonHexFloat(proof.independentObservedHex), 8);
    assert.equal(observedBits.readBigUInt64LE(0) - observedBits.readBigUInt64LE(8), 4n);
    assert.equal(review.observedULPDistance, 4);
    assert.equal(Math.abs(pythonHexFloat(proof.primaryObservedHex)) - 1e-12, pythonHexFloat(diagnosis.primaryCutoffHex));
    assert.equal(Math.abs(pythonHexFloat(proof.independentObservedHex)) - 1e-12, pythonHexFloat(diagnosis.independentCutoffHex));
    assert.equal(diagnosis.toleranceUnchanged, 1e-12);
    assert.equal(review.toleranceUnchanged, 1e-12);
    assert.equal(proof.operationalPredicatesDistinct, true);
    assert.equal(proof.primarySubtractionPredicateIntegerMatch, true);
    assert.equal(proof.independentAdditionOwnThresholdIntegerMatch, true);
    assert.equal(proof.commonAdditionThresholdMatchesPrimary, false);
    assert.equal(proof.commonDirectThresholdMatchClaimed, false);
    assert.equal(proof.probabilitiesOrFrozenMethodsModified, false);
    assert.equal(diagnosis.allScalarSupportsAndLabeledMassesEqual, true);
    assert.equal(diagnosis.outputsOrFrozenHelpersModified, false);
    assert.equal(review.pOrQChanged, false);
    assert.equal(review.frozenMethodsChanged, false);
    assert.ok(Object.keys(review.checks).length > 0 && Object.values(review.checks).every(value => value === true));
    const ps = BigInt(proof.primarySubtractionCountExact), ap = BigInt(proof.independentAdditionAtPrimaryCountExact);
    const so = BigInt(proof.primarySubtractionAtIndependentCountExact), ia = BigInt(proof.independentAdditionOwnCountExact);
    assert.equal(ps, primary);
    assert.equal(ia, own);
    assert.notEqual(ap, ps, 'Common-statistic addition and subtraction counts differ in this reviewed case');
    assert.equal(ps, BigInt(diagnosis.twoPointerSubtractionAtPrimaryCountExact));
    assert.equal(ap, BigInt(diagnosis.directAtPrimaryObservedCountExact));
    assert.equal(so, BigInt(diagnosis.twoPointerSubtractionAtOwnCountExact));
    assert.equal(ia, BigInt(diagnosis.directAtOwnObservedCountExact));
    assert.deepEqual(review.countMatrix, {
      primaryObserved: {subtraction: ps.toString(), addition: ap.toString()},
      independentObserved: {subtraction: so.toString(), addition: ia.toString()},
    });
    const decomposition = {
      predicateAtPrimary: (ap - ps).toString(), directObservedShift: (ia - ap).toString(),
      subtractionObservedShift: (so - ps).toString(), predicateAtIndependent: (ia - so).toString(),
      totalDifference: (own - primary).toString(),
    };
    assert.deepEqual(proof.signedCountDecomposition, decomposition);
    assert.deepEqual(diagnosis.signedCountDecomposition, decomposition);
    assert.deepEqual(review.signedCountDecomposition, decomposition);
    assert.equal((ap - ps) + (ia - ap), own - primary);
    assert.equal((so - ps) + (ia - so), own - primary);
    assert.equal(diagnosis.decompositionIsSignedNetCountDifferenceNotPairEnumeration, true);
    const [numerator, denominator] = diagnosis.probabilityDifferenceExactFraction.split('/').map(BigInt);
    assert.equal((own - primary) * denominator, numerator * total);
    assert.equal(diagnosis.unchangedReportedValues.primaryP, blocAudit.primary.overall[index].pValue);
    assert.equal(diagnosis.unchangedReportedValues.primaryQ, blocAudit.primary.overall[index].qValue);
    assert.equal(diagnosis.unchangedReportedValues.independentP, checked.p[index]);
    assert.deepEqual(proof.support, diagnosis.support);
    assert.deepEqual(diagnosis.halfSizes, diagnosis.subtractionHalfSizes);
    assert.equal(diagnosis.rawHalfMasses.reduce((product, mass) => product * BigInt(mass), 1n), total);
  } else {
    assert.equal(proof.commonThresholdExactIntegerMatch, true);
    assert.equal(proof.ownThresholdExactIntegerMatch, true);
    assert.equal(proof.allScalarSupportsAndLabeledMassesEqual, true);
    assert.equal(proof.outputsOrFrozenHelpersModified, false);
    assert.equal(primary, BigInt(proof.commonThresholdCountExact));
    assert.equal(own, BigInt(proof.ownThresholdCountExact));
    assertNearestFloatFromExactRatio(proof.probabilityDifference, own - primary, total);
  }
  assert.equal(proof.support.length, blocAudit.primary.byPollster.length);
  let reconstructedTotal = 1n;
  for (const [position, support] of proof.support.entries()) {
    const series = blocAudit.primary.byPollster[position];
    assert.equal(support.pollsterId, series.pollsterId);
    assert.deepEqual(support.pollIds, series.pollIds);
    assert.deepEqual(support.timeDays, series.timeDaysFromFirst);
    assert.deepEqual(support.seats, series.groups.find(row => row.group === identity).seats);
    assert.equal(support.weight, series.weight);
    const histogram = scalarPermutationHistogram(support.timeDays, support.seats);
    assert.equal(histogram.total, factorial(series.pollIds.length));
    assert.equal(histogram.total, BigInt(support.rawMass));
    reconstructedTotal *= histogram.total;
    const ordered = [...histogram.scores].sort(([a], [b]) => a - b);
    assert.equal(ordered.length, support.uniqueScores);
    const values = Buffer.alloc(8 * ordered.length);
    const scale = 14 * support.weight / histogram.denominator;
    ordered.forEach(([score], i) => values.writeDoubleLE(score * scale, i * 8));
    assert.equal(crypto.createHash('sha256').update(values).digest('hex'), support.valuesSha256);
    const masses = JSON.stringify(ordered.map(([, mass]) => mass.toString()));
    assert.equal(crypto.createHash('sha256').update(masses).digest('hex'), support.multiplicitiesSha256);
  }
  assert.equal(reconstructedTotal, total);
  verifiedCurrentBlocBoundaries.set(identity, proof);
  return proof;
}
function assertBlocIntegerTailAgreement(checked, index) {
  const primary = BigInt(blocAudit.primary.exactCounting.extremeCountsExact[index]);
  const own = BigInt(checked.countsExact[index]);
  if (primary === own) {
    assert.equal(primary, own);
    assert.equal(blocAudit.primary.exactCounting.extremeCounts[index], checked.counts[index]);
    return;
  }
  if (blocAudit.asOf === '2026-10-20') {
    assert.equal(blocAudit.primary.overall[index].group, 'opposition_raam');
    const proof = reviewedBlocBoundary(checked);
    assert.equal(checked.groups[index], proof.outcome);
    assert.equal(primary, BigInt(proof.independentCounterAtPrimaryObservedCountExact));
    assert.equal(own, BigInt(proof.independentCounterAtOwnObservedCountExact));
    return;
  }
  const proof = reviewedCurrentBlocBoundary(checked, index);
  assert.equal(primary, BigInt(proof.primaryExtremeCountExact));
  assert.equal(own, BigInt(proof.independentExtremeCountExact));
}
const eligibleCurrentCohort = audit.cohort.filter(row => row.eligibleStrict);
const currentSeriesSizes = new Map();
for (const row of eligibleCurrentCohort) currentSeriesSizes.set(row.pollsterId,
  (currentSeriesSizes.get(row.pollsterId) ?? 0) + 1);
const expectedCurrentDeltas = eligibleCurrentCohort.length - currentSeriesSizes.size;
const expectedCurrentPermutationTotal = [...currentSeriesSizes.values()].reduce(
  (product, n) => product * factorial(n), 1n);
const expectedCurrentSignPatterns = 2 ** currentSeriesSizes.size;

test('the October 11 exact denominator remains frozen before the two October 12 additions', () => {
  const folder = 'artifacts/poll-checks/2026-10-12-evening/before/';
  for (const filename of ['artifacts/strict-post-close/party-analysis.json', 'artifacts/strict-post-close/analysis.json']) {
    const frozen = read(folder + filename);
    assert.equal(frozen.asOf, '2026-10-11');
    for (const axis of ['primary', 'publicationDateSensitivity']) {
      assert.equal(BigInt(frozen[axis].exactCounting.nPermutationsExact), 36118462464000000n);
      assert.equal(frozen[axis].byPollster.reduce((product, series) => product * factorial(series.pollIds.length), 1n),
        36118462464000000n);
    }
  }
});

test('the October 11 significance verdicts remain frozen rather than imposed on later observations', () => {
  const folder = 'artifacts/poll-checks/2026-10-12-evening/before/';
  const frozen = read(folder + 'data/strict-party-trends.json');
  const frozenBlocs = read(folder + 'artifacts/strict-post-close/analysis.json').primary;
  assert.equal(frozen.asOf, '2026-10-11');
  assert.deepEqual(frozen.rows.filter(row => row.pValue < .05).map(row => row.partyId), ['joint']);
  assert.deepEqual(frozen.rows.filter(row => row.qValue < .05).map(row => row.partyId), ['joint']);
  assert.deepEqual(frozen.rows.filter(row => row.wholeSeriesSignFlipP < .05).map(row => row.partyId), ['joint']);
  assert.ok(frozen.rows.every(row => row.wholeSeriesSignFlipQ > .05));
  assert.deepEqual(frozen.rows.flatMap(row => row.byPollster).filter(row => row.pValue < .05).map(row => [row.pollsterId, row.partyId]),
    [['lazar', 'yashar'], ['tatika', 'likud'], ['next_data', 'rz_zehut']]);
  assert.ok(frozen.rows.flatMap(row => row.byPollster).every(row => row.qValue > .05));
  assert.ok(frozenBlocs.overall.every(row => row.qValue > .05 && row.wholeInstituteSignFlipQ > .05));
  assert.ok(frozenBlocs.byPollster.flatMap(series => series.groups).every(row => row.qValue > .05));
});

test('the October 8 evening strict results remain frozen before the Maariv update', () => {
  assert.equal(october8EveningAudit.asOf, '2026-10-08');
  assert.equal(october8EveningSnapshot.asOf, '2026-10-08');
  assert.equal(october8EveningSnapshot.coverage.pollCount, 38);
  assert.equal(october8EveningSnapshot.coverage.deltaCount, 30);
  assert.equal(october8EveningSnapshot.cohort.length, 42);
  assert.equal(october8EveningSnapshot.methodology.permutations, 6019743744000000);
  assert.deepEqual(october8EveningSnapshot.rows.filter(row => row.qValue < .05).map(row => row.partyId), ['joint']);
  assert.ok(october8EveningSnapshot.rows.every(row => row.wholeSeriesSignFlipQ > .05));
  assert.deepEqual(read('artifacts/strict-post-close/archive-2026-10-08-evening/party-analysis.json'), october8EveningAudit);
});

test('exact permutation counts retain integer precision beyond the JavaScript safe integer limit', () => {
  for (const analysis of [audit, blocAudit]) {
    for (const axis of ['primary', 'publicationDateSensitivity']) {
      const result = analysis[axis], counting = result.exactCounting;
      const total = result.byPollster.reduce((product, series) => product * factorial(series.pollIds.length), 1n);
      assert.equal(total, expectedCurrentPermutationTotal);
      assert.ok(total > BigInt(Number.MAX_SAFE_INTEGER));
      assert.equal(typeof counting.nPermutationsExact, 'string');
      assert.match(counting.nPermutationsExact, /^\d+$/);
      assert.equal(BigInt(counting.nPermutationsExact), total);
      assert.equal(counting.nPermutations, Number(total));
      assert.equal(counting.extremeCountsExact.length, result.overall.length);
      for (const [index, row] of result.overall.entries()) {
        const decimal = counting.extremeCountsExact[index];
        assert.equal(typeof decimal, 'string');
        assert.match(decimal, /^\d+$/);
        const count = BigInt(decimal);
        assert.ok(count >= 0n && count <= total, row.partyId ?? row.group);
        assert.equal(counting.extremeCounts[index], Number(count));
        close(row.pValue, exactProbability(decimal, counting.nPermutationsExact), row.partyId ?? row.group);
        close(counting.pValues[index], row.pValue, row.partyId ?? row.group);
      }
    }
  }
  assert.equal(snapshot.methodology.permutationsExact, audit.primary.exactCounting.nPermutationsExact);
  const checkedBlocs = read('artifacts/strict-post-close/independent-strict-numeric-audit.json');
  assert.equal(BigInt(checkedBlocs.totalExact), BigInt(blocAudit.primary.exactCounting.nPermutationsExact));
  assert.equal(checkedBlocs.countsExact.length, 3);
  for (const [index, decimal] of checkedBlocs.countsExact.entries()) {
    assertBlocIntegerTailAgreement(checkedBlocs, index);
    close(checkedBlocs.p[index], exactProbability(decimal, checkedBlocs.totalExact), blocAudit.primary.overall[index].group);
  }
  assert.equal(BigInt(independent.nPermutationsExact), BigInt(audit.primary.exactCounting.nPermutationsExact));
  assert.equal(independent.overall.length, 17);
  assert.deepEqual(independent.overall.map(row => row.partyId), audit.primary.overall.map(row => row.partyId));
  for (const [index, row] of independent.overall.entries()) {
    assert.equal(BigInt(row.extremeCountExact), BigInt(audit.primary.exactCounting.extremeCountsExact[index]));
    close(row.p, exactProbability(row.extremeCountExact, independent.nPermutationsExact), row.partyId);
  }
});

test('bloc slopes, all institute sign flips, and both BH families reproduce independently', () => {
  assert.equal(blocAudit.asOf, current.asOf);
  assert.equal(blocAudit.asOf, history.asOf);
  assert.equal(blocAudit.asOf, audit.asOf);
  assert.deepEqual(blocAudit.cohort, audit.cohort);
  const primary = blocAudit.primary;
  const checked = read('artifacts/strict-post-close/independent-strict-numeric-audit.json');
  assert.equal(primary.nPolls, eligibleCurrentCohort.length);
  assert.equal(primary.nPollsters, currentSeriesSizes.size);
  assert.equal(primary.nDeltas, expectedCurrentDeltas);
  assert.equal(primary.wholeInstituteSignPatterns, expectedCurrentSignPatterns);
  primary.exactCounting.extremeCountsExact.forEach((_, index) => assertBlocIntegerTailAgreement(checked, index));
  for (const [index, row] of primary.overall.entries()) {
    close(row.slopePerWeek, checked.slopes[index]);
    close(row.pValue, checked.p[index]);
    close(row.pValue, exactProbability(primary.exactCounting.extremeCountsExact[index], primary.exactCounting.nPermutationsExact));
    const series = primary.byPollster.map(institute => ({
      weight: institute.weight,
      ...institute.groups.find(item => item.group === row.group),
      timeDaysFromFirst: institute.timeDaysFromFirst,
    }));
    close(row.slopePerWeek, sum(series.map(item => item.weight * slope(item.timeDaysFromFirst, item.seats))));
    close(row.weightedNetDelta, sum(series.map(item => item.weight * (item.lastSeats - item.firstSeats))));
    let extremes = 0;
    for (let signs = 0; signs < primary.wholeInstituteSignPatterns; signs++) {
      const candidate = sum(series.map((item, index) => item.weight * slope(item.timeDaysFromFirst, item.seats) * ((signs >> index) & 1 ? 1 : -1)));
      if (Math.abs(candidate) >= Math.abs(row.slopePerWeek) - 1e-12) extremes++;
    }
    close(row.wholeInstituteSignFlipP, extremes / primary.wholeInstituteSignPatterns);
    for (const item of series) {
      close(item.pValue, scalarPermutationProbability(item.timeDaysFromFirst, item.seats, item.slopePerWeek));
    }
  }
  bh(primary.overall, 'pValue', 'qValue');
  bh(primary.overall, 'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ');
  bh(primary.byPollster.flatMap(series => series.groups), 'pValue', 'qValue');
});

test('the October 7 strict results remain frozen before the same-observation metadata revision', () => {
  assert.equal(october7BlocAudit.asOf, '2026-10-07');
  assert.equal(october7BlocAudit.primary.nPolls, 34);
  assert.equal(october7BlocAudit.primary.nDeltas, 26);
  assert.equal(october7Audit.primary.nPolls, 34);
  assert.equal(october7Audit.primary.nDeltas, 26);
  const frozen = october7Audit.cohort.find(row => row.pollId === 'history_hamadad_consortium_2026-10-07_current');
  assert.equal(frozen.fieldworkStart, null);
  assert.equal(frozen.fieldworkEnd, null);
  assert.equal(frozen.eligibleStrict, false);
  assert.equal(frozen.sampleSize, 1013);
  assert.equal(frozen.marginOfErrorPct, 2.5);
  assert.equal(frozen.sourceUrl, 'https://13tv.co.il/item/news/politics/politics/survey-905386103/');
});

test('the October 8 morning metadata release retains its original 35-poll statistical verdicts', () => {
  const frozen = read(october8MetadataFolder + 'data/strict-party-trends.json');
  assert.equal(frozen.asOf, '2026-10-07');
  assert.equal(frozen.coverage.pollCount, 35);
  assert.equal(frozen.coverage.deltaCount, 27);
  assert.equal(frozen.methodology.permutations, 48157949952000);
  assert.equal(frozen.methodology.signPatterns, 256);
  assert.equal(frozen.methodology.partyTests, 17);
  assert.deepEqual(frozen.rows.filter(row => row.qValue < .05).map(row => row.partyId).sort(), ['beyachad', 'joint']);
  assert.ok(frozen.rows.every(row => row.wholeSeriesSignFlipQ > .05));
  assert.deepEqual(read('artifacts/strict-post-close/archive-2026-10-08-metadata/party-analysis.json'), october8MetadataAudit);
  const joint = frozen.rows.find(row => row.partyId === 'joint');
  assert.equal(joint.upwardSeries, 6);
  assert.equal(joint.downwardSeries, 0);
  assert.equal(joint.flatSeries, 2);
  close(joint.wholeSeriesSignFlipP, .03125);
  close(joint.wholeSeriesSignFlipQ, .53125);
});

test('the October 6 statistical audit and public bundles remain an immutable hashed baseline', () => {
  const folder = 'artifacts/strict-post-close/archive-2026-10-06';
  const manifest = read(`${folder}/manifest.json`);
  assert.equal(manifest.asOf, '2026-10-06');
  assert.equal(manifest.frozenBefore, '2026-10-07');
  assert.equal(Object.keys(manifest.files).length, 91);
  assert.equal(october6Audit.asOf, '2026-10-06');
  for (const [filename, hash] of Object.entries(manifest.files)) {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(`${folder}/${filename}`)).digest('hex'), hash, filename);
  }
  assert.deepEqual(read(`${folder}/published-party-trends.json`), read(`${folder}/public-trends/party-trends.json`));
  assert.deepEqual(read(`${folder}/public-comparison/strict-trends-comparison.json`),
    read('artifacts/2026-10-06-comparison/strict-trends-comparison.json'));
});

test('the published snapshot is dated, fixed, and an exact copy of the audited party estimates', () => {
  assert.equal(snapshot.schemaVersion, 1);
  assert.equal(snapshot.asOf, current.asOf);
  assert.equal(snapshot.asOf, history.asOf);
  assert.equal(snapshot.asOf, audit.asOf);
  assert.equal(snapshot.weightMode, 'quality');
  assert.equal(snapshot.methodology.fixedSnapshot, true);
  assert.equal(snapshot.methodology.usesCurrentControls, false);
  assert.equal(snapshot.provenance.analysisSha256, crypto.createHash('sha256').update(fs.readFileSync(auditPath)).digest('hex'));
  assert.equal(snapshot.provenance.historySha256, audit.historySha256);
  assert.equal(snapshot.provenance.partiesSha256, audit.partiesSha256);
  assert.equal(snapshot.provenance.historySha256,
    crypto.createHash('sha256').update(fs.readFileSync('data/poll-history.json')).digest('hex'));
  assert.equal(snapshot.provenance.partiesSha256,
    crypto.createHash('sha256').update(fs.readFileSync('data/parties.json')).digest('hex'));
  assert.deepEqual(snapshot.rows.map(({byPollster, ...row}) => row), audit.primary.overall);
  assert.deepEqual(snapshot.rows.map(row => row.partyId), audit.testedPartyIds);
  assert.equal(snapshot.rows.length, 17);
  assert.equal(new Set(snapshot.rows.map(row => row.partyId)).size, 17);
  assert.ok(snapshot.rows.every(row => parties.some(party => party.id === row.partyId && party.ballot !== false)));
  assert.ok(snapshot.rows.every(row => row.partyId !== 'other'));
});

test('the strict cohort uses verified fieldwork after closure and excludes audited unknown-date polls', () => {
  assert.deepEqual(snapshot.coverage, {pollCount: eligibleCurrentCohort.length, seriesCount: currentSeriesSizes.size,
    deltaCount: expectedCurrentDeltas, partyCount: 17,
    from: eligibleCurrentCohort.map(row => row.fieldworkStart).sort()[0],
    to: eligibleCurrentCohort.map(row => row.fieldworkEnd).sort().at(-1), closureDate: '2026-09-08',
    excludedPollCount: audit.cohort.length - eligibleCurrentCohort.length});
  const currentCandidateCount = history.polls.filter(poll => poll.date >= '2026-09-09').length;
  assert.equal(snapshot.cohort.length, currentCandidateCount);
  assert.equal(new Set(snapshot.cohort.map(row => row.pollId)).size, currentCandidateCount);
  assert.deepEqual(new Set(snapshot.cohort.map(row => row.pollId)),
    new Set(history.polls.filter(poll => poll.date >= '2026-09-09').map(poll => poll.id)));
  const included = snapshot.cohort.filter(row => row.eligibleStrict);
  const excluded = snapshot.cohort.filter(row => !row.eligibleStrict);
  assert.equal(included.length, eligibleCurrentCohort.length);
  assert.equal(new Set(included.map(row => row.pollsterId)).size, currentSeriesSizes.size);
  for (const row of included) {
    assert.ok(row.fieldworkStart > snapshot.coverage.closureDate, row.pollId);
    assert.ok(row.fieldworkEnd >= row.fieldworkStart, row.pollId);
    assert.ok(row.fieldworkEnd <= row.publicationDate, row.pollId);
    assert.ok(audit.cohort.some(item => item.pollId === row.pollId && item.eligibleStrict));
  }
  assert.deepEqual(excluded.map(row => row.pollId).sort(), [
    'history_hamadad_consortium_2026-10-19_current',
    'history_hamadad_consortium_2026-10-21_current',
    'history_kantar_2026-09-14_723',
    'history_kantar_2026-10-11_current',
    'history_kantar_2026-10-18_current',
    'history_lazar_2026-10-16_current',
    'history_maagar_mochot_2026-09-10_720',
    'history_maagar_mochot_2026-09-16_current', 'history_maagar_mochot_2026-09-24_current',
    'history_maagar_mochot_2026-10-13_current',
    'history_maagar_mochot_2026-10-22_current',
  ]);
  assert.ok(excluded.every(row => row.fieldworkStart === null && row.fieldworkEnd === null));
  assert.equal(new Set(snapshot.rows.flatMap(row => row.byPollster.flatMap(series => series.pollIds))).size,
    eligibleCurrentCohort.length);
});

test('three verified additions extend the October 1 cohort under unchanged weights', () => {
  assert.equal(october1Audit.asOf, '2026-10-01');
  assert.equal(priorAudit.asOf, '2026-10-02');
  assert.deepEqual(priorAudit.normalizedHistoricalWeights, october1Audit.normalizedHistoricalWeights);
  const prior = new Map(october1Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(priorAudit.cohort.map(row => [row.pollId, row]));
  const additions = ['history_direct_polls_2026-10-01_current', 'history_lazar_2026-10-02_current', 'history_next_data_2026-10-01_current'];
  assert.deepEqual([...current.keys()].filter(id => !prior.has(id)).sort(), additions);
  for (const [id, row] of prior) assert.deepEqual(current.get(id), row, id);
  for (const id of additions) {
    const added = current.get(id);
    assert.equal(added.eligibleStrict, true);
    assert.equal(added.fieldworkEnd, '2026-10-01');
    assert.equal(added.fieldworkStart, added.pollsterId === 'lazar' ? '2026-09-30' : '2026-10-01');
    assert.equal(added.publicationDate, added.pollsterId === 'lazar' ? '2026-10-02' : '2026-10-01');
  }
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    const before = new Map(october1Audit[axis].byPollster.map(row => [row.pollsterId, row.pollIds]));
    const after = new Map(priorAudit[axis].byPollster.map(row => [row.pollsterId, row.pollIds]));
    for (const [pollsterId, ids] of before) assert.deepEqual(after.get(pollsterId),
      [...ids, ...additions.filter(id => current.get(id).pollsterId === pollsterId)]);
    assert.notDeepEqual(priorAudit[axis].overall, october1Audit[axis].overall);
  }
});

test('Kan October 4 stays excluded with null fieldwork and leaves the October 2 strict estimates unchanged', () => {
  assert.equal(priorAudit.asOf, '2026-10-02');
  assert.equal(october4Audit.asOf, '2026-10-04');
  assert.deepEqual(october4Audit.normalizedHistoricalWeights, priorAudit.normalizedHistoricalWeights);
  const prior = new Map(priorAudit.cohort.map(row => [row.pollId, row]));
  const current = new Map(october4Audit.cohort.map(row => [row.pollId, row]));
  assert.deepEqual([...current.keys()].filter(id => !prior.has(id)), ['history_kantar_2026-10-04_current']);
  for (const [id, row] of prior) assert.deepEqual(current.get(id), row, id);
  const added = current.get('history_kantar_2026-10-04_current');
  assert.equal(added.publicationDate, '2026-10-04');
  assert.equal(added.fieldworkStart, null);
  assert.equal(added.fieldworkEnd, null);
  assert.equal(added.eligibleStrict, false);
  assert.equal(added.sampleSize, 554);
  assert.equal(added.sourceUrl, 'https://x.com/kann_news/status/2106805478231552461');
  assert.equal(added.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(added.evidencePath)).digest('hex'));
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    assert.deepEqual(october4Audit[axis], priorAudit[axis]);
    assert.ok(october4Audit[axis].byPollster.every(row => !row.pollIds.includes(added.pollId)));
  }
});

test('N12 October 5 extends only its verified series, retaining all previous fieldwork decisions and weights', () => {
  assert.equal(october5Audit.asOf, '2026-10-05');
  assert.deepEqual(october5Audit.normalizedHistoricalWeights, october4Audit.normalizedHistoricalWeights);
  const prior = new Map(october4Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(october5Audit.cohort.map(row => [row.pollId, row]));
  const addedId = 'history_midgam_geva_2026-10-05_current';
  assert.deepEqual([...current.keys()].filter(id => !prior.has(id)), [addedId]);
  for (const [id, row] of prior) assert.deepEqual(current.get(id), row, id);
  const added = current.get(addedId);
  assert.equal(added.publicationDate, '2026-10-05');
  assert.equal(added.fieldworkStart, '2026-10-05');
  assert.equal(added.fieldworkEnd, '2026-10-05');
  assert.equal(added.eligibleStrict, true);
  assert.equal(added.sampleSize, 501);
  assert.equal(added.sourceUrl, 'https://www.mako.co.il/news-israel-elections/2026/Article-d7459e0cc7c01a1026.htm');
  assert.equal(added.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(added.evidencePath)).digest('hex'));
  assert.match(added.evidence[0].quote, /5\.10\.2026/);
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    const previous = new Map(october4Audit[axis].byPollster.map(row => [row.pollsterId, row.pollIds]));
    for (const series of october5Audit[axis].byPollster) assert.deepEqual(series.pollIds,
      [...previous.get(series.pollsterId), ...(series.pollsterId === 'midgam_geva' ? [addedId] : [])]);
    assert.equal(october5Audit[axis].nPolls, october4Audit[axis].nPolls + 1);
    assert.equal(october5Audit[axis].nDeltas, october4Audit[axis].nDeltas + 1);
    assert.equal(october5Audit[axis].exactCounting.nPermutations, october4Audit[axis].exactCounting.nPermutations * 4);
  }
});

test('original filings newly verify existing Kan and Maagar fieldwork without adding duplicate polls', () => {
  const previous = new Map(october5Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(october6Audit.cohort.map(row => [row.pollId, row]));
  const expected = [
    ['history_kantar_2026-10-04_current', '2026-10-04', 553, '11:30', '16:15'],
    ['history_maagar_mochot_2026-09-29_current', '2026-09-29', 550, '07:00', '12:00'],
  ];
  const revisions = [...previous.keys()].filter(id => JSON.stringify(previous.get(id)) !== JSON.stringify(current.get(id)));
  assert.deepEqual(revisions.sort(), expected.map(row => row[0]));
  for (const [id, fieldwork, sample, from, to] of expected) {
    const before = previous.get(id), after = current.get(id);
    assert.equal(before.eligibleStrict, false);
    assert.equal(before.fieldworkStart, null);
    assert.equal(after.eligibleStrict, true);
    assert.deepEqual(after.previousDecision, before);
    assert.equal(after.fieldworkStart, fieldwork);
    assert.equal(after.fieldworkEnd, fieldwork);
    assert.equal(after.fieldworkStartTime, from);
    assert.equal(after.fieldworkEndTime, to);
    assert.equal(after.sampleSize, sample);
    assert.match(after.sourceUrl, /^https:\/\/www\.gov\.il\/BlobFolder\/.*Survey_\d+\.pdf$/);
    assert.equal(after.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(after.evidencePath)).digest('hex'));
    assert.equal(history.polls.filter(row => row.id === id).length, 1);
  }
});

test('Maagar October 6 joins a two-observation series from explicitly stated original collection dates', () => {
  const previous = new Map(october5Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(october6Audit.cohort.map(row => [row.pollId, row]));
  const newId = 'history_maagar_mochot_2026-10-06_current';
  assert.deepEqual([...current.keys()].filter(id => !previous.has(id)), [newId]);
  const row = current.get(newId);
  assert.equal(row.publicationDate, '2026-10-06');
  assert.equal(row.fieldworkStart, '2026-10-05');
  assert.equal(row.fieldworkEnd, '2026-10-06');
  assert.equal(row.eligibleStrict, true);
  assert.equal(row.sampleSize, 550);
  assert.equal(row.sourceUrl, 'https://www.ch16.co.il/vod/6ac52db1be11035fe627ec5a');
  assert.match(row.evidence[0].quote, /אתמול והיום/);
  assert.equal(row.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(row.evidencePath)).digest('hex'));
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    const series = october6Audit[axis].byPollster.find(row => row.pollsterId === 'maagar_mochot');
    assert.deepEqual(series.pollIds, ['history_maagar_mochot_2026-09-29_current', newId]);
    assert.equal(october6Audit[axis].nPolls, october5Audit[axis].nPolls + 3);
    assert.equal(october6Audit[axis].nDeltas, october5Audit[axis].nDeltas + 2);
    assert.equal(october6Audit[axis].exactCounting.nPermutations, october5Audit[axis].exactCounting.nPermutations * 8);
  }
  const calibration = read('data/calibration.json');
  const rawTotal = snapshot.weights.reduce((sum, row) => sum + calibration.pollsterQuality[row.pollsterId].weight, 0);
  for (const row of snapshot.weights) close(row.weight, calibration.pollsterQuality[row.pollsterId].weight / rawTotal);
});

test('independent exhaustive party audit uses the refreshed history and agrees with published estimates', () => {
  assert.equal(independent.historySha256, audit.historySha256);
  assert.equal(independent.cohortSha256,
    crypto.createHash('sha256').update(fs.readFileSync('artifacts/strict-post-close/analysis.json')).digest('hex'));
  for (const checked of independent.overall) {
    const published = snapshot.rows.find(row => row.partyId === checked.partyId);
    assert.ok(published, checked.partyId);
    close(checked.slopePerWeek, published.slopePerWeek, `${checked.partyId} independent slope`);
    close(checked.netDelta, published.weightedNetDelta, `${checked.partyId} independent delta`);
    close(checked.p, published.pValue, `${checked.partyId} independent p`);
    close(checked.q, published.qValue, `${checked.partyId} independent q`);
  }
});

test('the October 7 C13 observation is revised in place from its original pollster publication', () => {
  const audit = october8MetadataAudit;
  const current = october8MetadataCurrent;
  const history = october8MetadataHistory;
  const sources = october8MetadataSources;
  const id = 'history_hamadad_consortium_2026-10-07_current';
  const row = audit.cohort.find(item => item.pollId === id);
  const frozen = october7Audit.cohort.find(item => item.pollId === id);
  assert.equal(row.publicationDate, '2026-10-07');
  assert.equal(row.fieldworkStart, '2026-10-06');
  assert.equal(row.fieldworkEnd, '2026-10-06');
  assert.equal(row.eligibleStrict, true);
  assert.equal(row.sampleSize, 1263);
  assert.equal(row.marginOfErrorPct, 2.8);
  assert.match(row.sourceUrl, /^https:\/\/themadad\.com\//);
  assert.deepEqual(row.previousDecision, frozen);
  assert.equal(row.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(row.evidencePath)).digest('hex'));
  assert.match(row.evidence[0].quote, /6 באוקטובר 2026/);
  assert.equal(history.polls.filter(poll => poll.id === id).length, 1);
  assert.equal(history.polls.length, 110);
  assert.equal(new Set(history.polls.map(poll => poll.id)).size, 110);
  assert.equal(new Set(history.polls.map(poll => `${poll.pollsterId}|${poll.date}`)).size, 110);
  const poll = history.polls.find(item => item.id === id);
  const active = current.polls.find(item => item.id === 'hamadad_consortium_2026-10-07');
  const oldActive = october8BaselineCurrent.polls.find(item => item.id === active.id);
  assert.deepEqual(active.seats, oldActive.seats);
  assert.deepEqual(active.percentages, oldActive.percentages);
  assert.deepEqual(active.reportedPercentages, oldActive.reportedPercentages);
  assert.deepEqual(active.sourceBlocSeats, oldActive.sourceBlocSeats);
  assert.equal(active.requiresReconstruction, oldActive.requiresReconstruction);
  assert.equal(sum(Object.values(active.seats)), 120);
  assert.equal(active.sampleSize, 1263);
  assert.equal(active.reportedMarginOfErrorPct, 2.8);
  assert.equal(active.marginConfidencePct, 95);
  assert.match(active.reportedMarginOfErrorDescription, /ממוצעת ברמה הארצית/);
  assert.equal(active.reportedBelowThresholdTotalPct, 5.4);
  assert.equal(active.belowThresholdNamedSumPct, 4.8);
  assert.equal(active.belowThresholdUnexplainedDifferencePP, .6);
  assert.deepEqual(active.sourceConflicts.map(conflict => [conflict.field, conflict.broadcastValue, conflict.originalPollsterValue]), [
    ['sampleSize', 1013, 1263], ['reportedMarginOfErrorPct', 2.5, 2.8],
  ]);
  assert.equal(active.previousSourceMetadata.sampleSize, 1013);
  assert.equal(active.previousSourceMetadata.reportedMarginOfErrorPct, 2.5);
  assert.equal(active.previousSourceMetadata.sourceUrl, 'https://13tv.co.il/item/news/politics/politics/survey-905386103/');
  assert.ok(active.secondarySourceUrls.includes(active.previousSourceMetadata.sourceUrl));
  assert.equal(poll.sourcePollId, active.id);
  assert.equal(poll.recordStatus, 'current-reviewed-record');
  for (const baseline of october8BaselineCurrent.polls.filter(item => item.id !== active.id)) {
    assert.deepEqual(current.polls.find(item => item.id === baseline.id), baseline, baseline.id);
  }
  for (const baseline of october8BaselineHistory.polls.filter(item => item.id !== id)) {
    assert.deepEqual(history.polls.find(item => item.id === baseline.id), baseline, baseline.id);
  }
  const source = sources.sources.find(item => item.id === 'hamadad_consortium');
  assert.equal(sources.sources.filter(item => item.id === 'hamadad_consortium').length, 1);
  assert.match(source.url, /^https:\/\/themadad\.com\//);
  assert.ok(source.secondarySourceUrls.includes(active.previousSourceMetadata.sourceUrl));
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    const series = audit[axis].byPollster.find(item => item.pollsterId === 'hamadad_consortium');
    assert.equal(series.pollIds.at(-1), id);
  }
});

test('the original September 30 Rosner filing verifies an existing observation without altering its published mandates', () => {
  // This is the frozen October 8 metadata stage, before later new Rosner polls.
  // Keep its cohort and source mandates paired with that stage's history.
  const audit = october8MetadataAudit;
  const history = october8MetadataHistory;
  const id = 'history_hamadad_consortium_2026-09-30_current';
  const previous = new Map(october6Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(audit.cohort.map(row => [row.pollId, row]));
  const before = previous.get(id), after = current.get(id);
  assert.equal(before.eligibleStrict, false);
  assert.equal(before.fieldworkStart, null);
  assert.equal(after.eligibleStrict, true);
  assert.deepEqual(after.previousDecision, before);
  assert.equal(after.publicationDate, '2026-09-30');
  assert.equal(after.fieldworkStart, '2026-09-29');
  assert.equal(after.fieldworkEnd, '2026-09-30');
  assert.equal(after.fieldworkStartTime, '10:00');
  assert.equal(after.fieldworkEndTime, '09:00');
  assert.equal(after.sampleSize, 1013);
  assert.equal(after.marginOfErrorPct, 3.1);
  assert.equal(after.sourceUrl, 'https://www.gov.il/BlobFolder/dynamiccollectorresultitem/knesset_election94/he/Survey_4182.pdf');
  assert.equal(after.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(after.evidencePath)).digest('hex'));
  const poll = history.polls.find(row => row.id === id);
  assert.equal(history.polls.filter(row => row.id === id).length, 1);
  const original = read('artifacts/sources/2026-10-07-hamadad-update/reviewed-rosner-sep30-original.json');
  assert.equal(sum(Object.values(poll.seats)), 120);
  for (const row of original.tables[0].rows.filter(row => row.partyId && row.seats !== null)) {
    assert.equal(poll.seats[row.partyId] ?? 0, row.seats);
  }
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    const priorSeries = october6Audit[axis].byPollster.find(row => row.pollsterId === 'hamadad_consortium');
    const series = audit[axis].byPollster.find(row => row.pollsterId === 'hamadad_consortium');
    assert.deepEqual(series.pollIds, [...priorSeries.pollIds, id, 'history_hamadad_consortium_2026-10-07_current']);
    close(series.timeDaysFromFirst.at(-2), axis === 'primary' ? 20.5 : 21);
  }
  assert.deepEqual(audit.normalizedHistoricalWeights, october6Audit.normalizedHistoricalWeights);
});

test('NEXT DATA October 7 extends one verified series while missing methodology stays null', () => {
  const audit = october8MetadataAudit;
  const id = 'history_next_data_2026-10-07_current';
  const row = audit.cohort.find(item => item.pollId === id);
  assert.equal(row.publicationDate, '2026-10-07');
  assert.equal(row.fieldworkStart, '2026-10-07');
  assert.equal(row.fieldworkEnd, '2026-10-07');
  assert.equal(row.eligibleStrict, true);
  assert.equal(row.sampleSize, 1100);
  assert.equal(row.marginOfErrorPct, null);
  assert.equal(row.collectionMode, null);
  assert.equal(row.sourceUrl, 'https://www.c14.co.il/article/1728516');
  assert.match(row.sourceParagraph, /נערך היום 7 באוקטובר 2026/);
  assert.equal(row.evidenceSha256, crypto.createHash('sha256').update(fs.readFileSync(row.evidencePath)).digest('hex'));
  for (const evidence of row.evidence) {
    assert.equal(evidence.sha256, crypto.createHash('sha256').update(fs.readFileSync(evidence.file)).digest('hex'));
  }
  assert.equal(history.polls.filter(poll => poll.id === id).length, 1);
  const previous = new Map(october6Audit.cohort.map(row => [row.pollId, row]));
  const current = new Map(audit.cohort.map(row => [row.pollId, row]));
  assert.deepEqual([...current.keys()].filter(id => !previous.has(id)).sort(), [
    'history_hamadad_consortium_2026-10-07_current', id,
  ]);
  assert.deepEqual([...previous.keys()].filter(id => JSON.stringify(previous.get(id)) !== JSON.stringify(current.get(id))),
    ['history_hamadad_consortium_2026-09-30_current']);
  for (const axis of ['primary', 'publicationDateSensitivity']) {
    for (const series of audit[axis].byPollster) {
      const prior = october6Audit[axis].byPollster.find(row => row.pollsterId === series.pollsterId);
      const extra = series.pollsterId === 'hamadad_consortium' ? [
        'history_hamadad_consortium_2026-09-30_current', 'history_hamadad_consortium_2026-10-07_current']
        : series.pollsterId === 'next_data' ? [id] : [];
      assert.deepEqual(series.pollIds, [...prior.pollIds, ...extra]);
    }
    assert.equal(audit[axis].nPolls, october6Audit[axis].nPolls + 3);
    assert.equal(audit[axis].nDeltas, october6Audit[axis].nDeltas + 3);
    assert.equal(audit[axis].exactCounting.nPermutations, october6Audit[axis].exactCounting.nPermutations * 140);
  }
});

test('each published party series matches complete 120-seat source polls and verified midpoint times', () => {
  const historyById = new Map(history.polls.map(poll => [poll.id, poll]));
  const cohortById = new Map(snapshot.cohort.map(poll => [poll.pollId, poll]));
  for (const row of snapshot.rows) {
    assert.equal(row.byPollster.length, currentSeriesSizes.size);
    for (const series of row.byPollster) {
      const auditSeries = audit.primary.byPollster.find(item => item.pollsterId === series.pollsterId);
      const auditedParty = auditSeries.parties.find(item => item.partyId === row.partyId);
      for (const [key, value] of Object.entries(auditedParty)) assert.deepEqual(series[key], value, `${row.partyId} ${series.pollsterId} ${key}`);
      assert.equal(series.nPolls, series.pollIds.length);
      assert.equal(series.nDeltas, series.pollIds.length - 1);
      const midpoints = series.pollIds.map(id => {
        const poll = historyById.get(id), verified = cohortById.get(id);
        assert.ok(poll && verified?.eligibleStrict, id);
        assert.equal(sum(Object.values(poll.seats)), 120, id);
        return (Date.parse(verified.fieldworkStart) + Date.parse(verified.fieldworkEnd)) / (2 * 86400000);
      });
      series.timeDaysFromFirst.forEach((day, index) => close(day, midpoints[index] - midpoints[0]));
      assert.deepEqual(series.seats, series.pollIds.map(id => historyById.get(id).seats[row.partyId] ?? 0));
      assert.deepEqual(series.deltas, series.seats.slice(1).map((value, index) => value - series.seats[index]));
      close(series.slopePerWeek, slope(series.timeDaysFromFirst, series.seats));
      close(series.netDelta, sum(series.deltas));
    }
  }
});

test('fixed historical weights are applied once per series, and full-series summaries reproduce independently', () => {
  close(sum(snapshot.weights.map(row => row.weight)), 1);
  assert.equal(sum(snapshot.weights.map(row => row.nPolls)), eligibleCurrentCohort.length);
  assert.equal(sum(snapshot.weights.map(row => row.nPolls - 1)), expectedCurrentDeltas);
  for (const weight of snapshot.weights) close(weight.weight, audit.normalizedHistoricalWeights[weight.pollsterId]);
  for (const row of snapshot.rows) {
    close(row.weightedNetDelta, sum(row.byPollster.map(series => series.weight * (series.lastSeats - series.firstSeats))));
    close(row.slopePerWeek, sum(row.byPollster.map(series => series.weight * slope(series.timeDaysFromFirst, series.seats))));
    close(row.weightedFirstSeats, sum(row.byPollster.map(series => series.weight * series.firstSeats)));
    close(row.weightedLastSeats, sum(row.byPollster.map(series => series.weight * series.lastSeats)));
    assert.equal(row.upwardSeries + row.downwardSeries + row.flatSeries, currentSeriesSizes.size);
  }
  close(sum(snapshot.rows.map(row => row.weightedFirstSeats)), 120);
  close(sum(snapshot.rows.map(row => row.weightedLastSeats)), 120);
  close(sum(snapshot.rows.map(row => row.weightedNetDelta)), 0);
  close(sum(snapshot.rows.map(row => row.slopePerWeek)), 0);
});

test('individual permutation probabilities, whole-series sensitivity, and BH families reproduce independently', () => {
  // Preserve the labeled n! null while avoiding a dense array of all n! rows.
  // Small independent brute-force oracles include repeats, negatives and constants.
  for (const [times, seats] of [
    [[0, 1, 4], [-2, 0, 3]],
    [[0, .5, 2, 5], [-1, -1, 0, 4]],
    [[0, 1, 3, 6, 8], [0, 0, 0, 4, 4]],
    [[0, .5, 2, 4, 6, 9], [-3, -3, 0, 0, 1, 1]],
    [[0, 2, 7], [0, 0, 0]],
    [[0, .5, 6], [-4, -4, -4]],
  ]) {
    const dense = permutations(seats);
    const histogram = scalarPermutationHistogram(times, seats);
    assert.equal(histogram.total, BigInt(dense.length));
    for (const observed of [0, slope(times, seats), slope(times, [...seats].reverse())]) {
      const extreme = dense.filter(order => Math.abs(slope(times, order)) >= Math.abs(observed) - 1e-12).length;
      close(scalarPermutationProbability(times, seats, observed), extreme / dense.length, 'streamed exact versus labeled brute force');
    }
  }
  const eleven = scalarPermutationHistogram(Array.from({length: 11}, (_, i) => i), [...Array(9).fill(0), 1, 1]);
  assert.equal(eleven.total, 39916800n);
  assert.equal(eleven.assignments, 55n);
  const beyondInt64 = scalarPermutationHistogram(Array.from({length: 21}, (_, i) => i / 2), [...Array(20).fill(0), 1]);
  assert.equal(beyondInt64.total, factorial(21));
  assert.ok(beyondInt64.total > 2n ** 63n - 1n);
  assert.equal(beyondInt64.assignments, 21n);
  assert.equal(BigInt(snapshot.methodology.permutationsExact), expectedCurrentPermutationTotal);
  assert.equal(snapshot.methodology.permutations, Number(expectedCurrentPermutationTotal));
  assert.equal(snapshot.methodology.signPatterns, expectedCurrentSignPatterns);
  assert.equal(snapshot.methodology.partyTests, 17);
  assert.equal(snapshot.methodology.individualTests, 17 * currentSeriesSizes.size);
  for (const [index, row] of snapshot.rows.entries()) {
    close(row.pValue, exactProbability(audit.primary.exactCounting.extremeCountsExact[index], snapshot.methodology.permutationsExact));
    let extremes = 0;
    for (let signs = 0; signs < expectedCurrentSignPatterns; signs++) {
      const testSlope = sum(row.byPollster.map((series, index) => series.weight * series.slopePerWeek * ((signs >> index) & 1 ? 1 : -1)));
      if (Math.abs(testSlope) >= Math.abs(row.slopePerWeek) - 1e-12) extremes++;
    }
    close(row.wholeSeriesSignFlipP, extremes / expectedCurrentSignPatterns);
    for (const series of row.byPollster) {
      close(series.pValue, scalarPermutationProbability(series.timeDaysFromFirst, series.seats, series.slopePerWeek));
    }
  }
  bh(snapshot.rows, 'pValue', 'qValue');
  bh(snapshot.rows, 'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ');
  bh(snapshot.rows.flatMap(row => row.byPollster), 'pValue', 'qValue');
  assert.deepEqual(snapshot.rows.filter(row => row.pValue < .05).map(row => row.partyId),
    independent.overall.filter(row => row.p < .05).map(row => row.partyId));
  assert.deepEqual(snapshot.rows.filter(row => row.qValue < .05).map(row => row.partyId),
    independent.overall.filter(row => row.q < .05).map(row => row.partyId));
  assert.deepEqual(snapshot.rows.filter(row => row.wholeSeriesSignFlipP < .05).map(row => row.partyId),
    independent.overall.filter(row => row.signFlipP < .05).map(row => row.partyId));
  assert.deepEqual(snapshot.rows.filter(row => row.wholeSeriesSignFlipQ < .05).map(row => row.partyId),
    independent.overall.filter(row => row.signFlipQ < .05).map(row => row.partyId));
  assert.deepEqual(snapshot.rows.flatMap(row => row.byPollster).filter(row => row.pValue < .05)
    .map(row => `${row.pollsterId}:${row.partyId}`).sort(),
    independent.byPollster.filter(row => row.p < .05).map(row => `${row.pollsterId}:${row.partyId}`).sort());
  assert.deepEqual(snapshot.rows.flatMap(row => row.byPollster).filter(row => row.qValue < .05)
    .map(row => `${row.pollsterId}:${row.partyId}`).sort(),
    independent.byPollster.filter(row => row.q < .05).map(row => `${row.pollsterId}:${row.partyId}`).sort());
});

test('constant-zero parties stay present with explicit limitations; public source links contain no local paths', () => {
  assert.deepEqual(snapshot.rows.filter(row => row.zeroSeatsThroughout).map(row => row.partyId).sort(), ['gantz', 'haredi_public', 'israel_first', 'noam']);
  for (const row of snapshot.rows.filter(row => row.zeroSeatsThroughout)) {
    assert.equal(row.pValue, 1); assert.equal(row.qValue, 1);
    assert.ok(row.byPollster.every(series => series.seats.every(value => value === 0)));
  }
  assert.match(snapshot.methodology.zeroSeatConvention, /below the threshold/);
  const serialized = JSON.stringify(snapshot);
  assert.doesNotMatch(serialized, /"[A-Za-z]:[\\/]|file:\/\/|Users[\\/]/);
  for (const row of snapshot.cohort) {
    assert.ok(row.sourceUrls.length >= 1, row.pollId);
    for (const url of row.sourceUrls) assert.ok(['http:', 'https:'].includes(new URL(url).protocol));
  }
  for (const source of snapshot.sources) assert.ok(source.title && new URL(source.url).protocol === 'https:');
});


// The official October 10 review corrects one existing fieldwork interval.
// The October 8 metadata assertions above intentionally keep their frozen end date.
test('the October 10 official C13 review corrects the interval without changing any published mandates or national shares', () => {
  // Preserve the completed metadata-only stage before the later Kan addition.
  const october10Folder = 'artifacts/poll-checks/2026-10-11/before/';
  const current = read(october10Folder + 'data/current-polls.json');
  const history = read(october10Folder + 'data/poll-history.json');
  const audit = read(october10Folder + auditPath);
  const folder = 'artifacts/poll-checks/2026-10-10/before/';
  const beforeCurrent = read(folder + 'data/current-polls.json');
  const beforeHistory = read(folder + 'data/poll-history.json');
  const beforeAudit = read(folder + auditPath);
  const activeId = 'hamadad_consortium_2026-10-07';
  const historyId = 'history_hamadad_consortium_2026-10-07_current';
  const active = current.polls.find(row => row.id === activeId);
  const archived = history.polls.find(row => row.id === historyId);
  const prior = beforeCurrent.polls.find(row => row.id === activeId);
  const row = audit.cohort.find(row => row.pollId === historyId);
  assert.equal(current.asOf, '2026-10-10');
  assert.equal(history.asOf, '2026-10-10');
  assert.equal(audit.asOf, '2026-10-10');
  assert.deepEqual(current.polls.map(row => row.id), beforeCurrent.polls.map(row => row.id));
  assert.deepEqual(history.polls.map(row => row.id), beforeHistory.polls.map(row => row.id));
  for (const key of ['seats', 'percentages', 'reportedPercentages', 'sourceBlocSeats', 'requiresReconstruction', 'undecidedPct']) {
    assert.deepEqual(active[key], prior[key], key);
    assert.deepEqual(archived[key], prior[key], key);
  }
  assert.equal(sum(Object.values(active.seats)), 120);
  for (const record of [active, archived, row]) {
    assert.equal(record.fieldworkStart, '2026-10-06');
    assert.equal(record.fieldworkEnd, '2026-10-07');
    assert.equal(record.sampleSize, 1263);
  }
  assert.equal(row.publicationDate, '2026-10-07');
  assert.equal(row.eligibleStrict, true);
  assert.equal(row.marginOfErrorPct, 2.8);
  assert.equal(active.fieldworkStartTime, '09:00');
  assert.equal(active.fieldworkEndTime, '09:00');
  assert.equal(active.reportedMarginOfErrorPct, 2.8);
  assert.match(JSON.stringify(active), /Survey_4193\.pdf/);
  assert.match(JSON.stringify(row), /Survey_4193\.pdf/);
  for (const [partyId, seats] of Object.entries(active.seats)) {
    if (seats > 0) {
      assert.equal(Object.hasOwn(active.percentages, partyId), false, partyId);
      assert.equal(Object.hasOwn(active.reportedPercentages, partyId), false, partyId);
    }
  }
  const priorCohort = new Map(beforeAudit.cohort.map(row => [row.pollId, row]));
  assert.deepEqual(audit.cohort.map(row => row.pollId), beforeAudit.cohort.map(row => row.pollId));
  for (const entry of audit.cohort) {
    assert.equal(entry.eligibleStrict, priorCohort.get(entry.pollId).eligibleStrict, entry.pollId);
    if (entry.pollId !== historyId) assert.deepEqual(entry, priorCohort.get(entry.pollId), entry.pollId);
  }
  assert.deepEqual(audit.normalizedHistoricalWeights, beforeAudit.normalizedHistoricalWeights);
  assert.deepEqual(audit.publicationDateSensitivity.overall, beforeAudit.publicationDateSensitivity.overall);
  const oldTimes = beforeAudit.primary.byPollster.find(row => row.pollsterId === 'hamadad_consortium').timeDaysFromFirst;
  const newTimes = audit.primary.byPollster.find(row => row.pollsterId === 'hamadad_consortium').timeDaysFromFirst;
  assert.deepEqual(newTimes.slice(0, -1), oldTimes.slice(0, -1));
  close(newTimes.at(-1), oldTimes.at(-1) + .5);
});
