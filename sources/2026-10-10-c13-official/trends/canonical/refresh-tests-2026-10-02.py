"""Advance only the current strict snapshot assertions; preserve older dated tests."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'tests/strict-party-publication.test.mjs'
text=p.read_text(encoding='utf-8-sig')
text=text.replace('archive-2026-09-30/party-analysis.json','archive-2026-10-01/party-analysis.json')
text=text.replace("assert.equal(snapshot.asOf, '2026-10-01');", "assert.equal(snapshot.asOf, '2026-10-02');")
text=text.replace('pollCount: 25, seriesCount: 7, deltaCount: 18','pollCount: 28, seriesCount: 7, deltaCount: 21')
text=text.replace('snapshot.cohort.length, 31','snapshot.cohort.length, 34')
text=text.replace('size, 31','size, 34')
text=text.replace('included.length, 25','included.length, 28')
text=text.replace('size, 25','size, 28')
start=text.index("test('one verified Tatika poll")
end=text.index("test('independent exhaustive",start)
text=text[:start]+'''test('three verified additions extend the October 1 cohort under unchanged weights', () => {
  assert.equal(priorAudit.asOf, '2026-10-01');
  assert.equal(audit.asOf, '2026-10-02');
  assert.deepEqual(audit.normalizedHistoricalWeights, priorAudit.normalizedHistoricalWeights);
  const prior = new Map(priorAudit.cohort.map(row => [row.pollId, row]));
  const current = new Map(audit.cohort.map(row => [row.pollId, row]));
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
    const before = new Map(priorAudit[axis].byPollster.map(row => [row.pollsterId, row.pollIds]));
    const after = new Map(audit[axis].byPollster.map(row => [row.pollsterId, row.pollIds]));
    for (const [pollsterId, ids] of before) assert.deepEqual(after.get(pollsterId),
      [...ids, ...additions.filter(id => current.get(id).pollsterId === pollsterId)]);
    assert.notDeepEqual(audit[axis].overall, priorAudit[axis].overall);
  }
});

'''+text[end:]
text=text.replace('row.nPolls)), 25','row.nPolls)), 28')
text=text.replace('row.nPolls - 1)), 18','row.nPolls - 1)), 21')
text=text.replace('89579520','10749542400')
p.write_text(text,encoding='utf-8')
print('Updated current strict dates/cohort assertions; numeric significance assertions await audited calculation.')
