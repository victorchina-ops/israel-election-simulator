import fs from 'node:fs';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

// Read-only binding of both replays to the final website and the frozen source
// plan. Tatika publication15Oct and fieldwork14–15Oct; morning release immutable.
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const root = 'artifacts/poll-checks/2026-10-15-zman/';
const report = read(root + 'model-comparison.json');
const replay = read(root + 'model-comparison.after-replay.json');
const baseline = read('artifacts/dashboard-baseline.json');
const snapshot = read('dashboard/src/data.json');
const plan = read(root + 'source-plan.json');
const ingestion = read(root + 'ingestion-validation.json');
const checkpoint = read(root + 'before/manifest.json');
const cfg = Object.fromEntries(snapshot.queries.model_configuration.rows.map(r => [r.key, r.value]));
const inputs = Object.fromEntries(snapshot.queries.model_input.rows.map(r => [r.key, r.value]));
const digest = p => createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert.equal(plan.status, 'reviewed');
assert.equal(plan.asOf, '2026-10-15');
assert.equal(ingestion.status, 'PASS');
assert.deepEqual(plan.polls.map(p => p.pollsterId).sort(), ['tatika']);
assert.deepEqual(replay.config, cfg);
assert.deepEqual(replay.config, baseline.config);
assert.deepEqual(replay.input, inputs);
const stable = ({ generatedAt, ...rest }) => rest;
assert.deepEqual(stable(replay.result), stable(baseline.result));
assert.equal(report.status, 'passed');
assert.equal(report.onlyControlDateDiffers, true);
assert.equal(snapshot.dataAsOf, '2026-10-15');
assert.equal(cfg.weightMode, 'quality');
for (const key of ['includeChannel14', 'signalNoiseEnabled', 'pollCorrelationEnabled']) assert.equal(cfg[key], false);
assert.equal(snapshot.features.chatGPT, false);
assert.deepEqual(report.pollChanges.filter(p => p.changed).map(p => p.pollsterId).sort(), plan.polls.map(p => p.pollsterId).sort());
const expectedIds = plan.polls.map(p => read(p.candidatePath).id).sort();
assert.deepEqual(report.pollChanges.filter(p => p.changed).flatMap(p => p.afterIds).sort(), expectedIds);
for (const phase of ['before', 'after']) {
  const r = read(root + `model-comparison.${phase}-replay.json`);
  const selectedCount = r.input.current.polls.filter(p => p.pollsterId !== 'next_data').length;
  assert.equal(r.result.pollWeights.length, selectedCount);
  assert.ok(r.result.pollWeights.every(p => p.pollsterId !== 'next_data'));
  assert.equal(r.result.checks.eachWorld120, true);
  assert.equal(r.input.current.asOf, phase === 'before' ? checkpoint.baselineAsOf : plan.asOf);
  assert.equal(r.input.current.polls.length, ingestion.activePollCount);
}
assert.equal(inputs.history.polls.length, ingestion.historyPollCount);
assert.equal(inputs.current.polls.length, ingestion.activePollCount);
for (const poll of inputs.current.polls) assert.equal(Object.values(poll.seats).reduce((a, b) => a + b, 0), 120);
const output = {
  status: 'PASS', asOf: plan.asOf, currentReplayExactlyMatchesWebsiteBaseline: true,
  bothReplaysExcludeChannel14: true, activeSelectedInstitutes: replay.result.pollWeights.length,
  sameControlsExceptAsOf: true, allSimulatedWorldsHave120Seats: true,
  changedPollsters: plan.polls.map(p => p.pollsterId).sort(), newObservationIds: expectedIds,
  publicationDates: [...new Set(plan.polls.map(p => read(p.candidatePath).date))].sort(),
  activePolls: ingestion.activePollCount, historyPolls: ingestion.historyPollCount,
  comparisonSha256: digest(root + 'model-comparison.json'),
  snapshotSha256: digest('dashboard/src/data.json'),
  baselineSha256: digest('artifacts/dashboard-baseline.json'),
  sourcePlanSha256: digest(root + 'source-plan.json'),
  validationScope: 'Explicit flags and actual selected weights are bound to the website defaults; both snapshots replayed with the unchanged current model. This is not a significance test.'
};
const file = root + 'model-comparison-validation.json';
assert.ok(!fs.existsSync(file), 'Preserve the dated validation receipt.');
fs.writeFileSync(file, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output));
