"""Compare the October 1 verified Tatika addition with the frozen September 30 audit."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEFORE = HERE / "archive-2026-09-30"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compare_report(filename, id_key, fields):
    old = read(BEFORE / filename)
    new = read(HERE / filename)
    assert old["asOf"] == "2026-09-30" and new["asOf"] == "2026-10-01"
    assert old["normalizedHistoricalWeights"] == new["normalizedHistoricalWeights"]
    old_cohort = {row["pollId"]: row for row in old["cohort"]}
    new_cohort = {row["pollId"]: row for row in new["cohort"]}
    added = set(new_cohort) - set(old_cohort)
    assert len(added) == 1 and set(old_cohort) <= set(new_cohort)
    poll_id = added.pop()
    poll = new_cohort[poll_id]
    assert poll["pollsterId"] == "tatika" and poll["publicationDate"] == "2026-10-01"
    assert poll["fieldworkStart"] == "2026-09-30" and poll["fieldworkEnd"] == "2026-10-01"
    assert poll["eligibleStrict"] is True
    assert {key: new_cohort[key] for key in old_cohort} == old_cohort
    assert len([row for row in new_cohort.values() if row["eligibleStrict"]]) == len(
        [row for row in old_cohort.values() if row["eligibleStrict"]]
    ) + 1

    axes = {}
    for axis in ("primary", "publicationDateSensitivity"):
        a, b = old[axis], new[axis]
        assert b["nPolls"] == a["nPolls"] + 1
        assert b["nDeltas"] == a["nDeltas"] + 1
        series_key = "nPollsters" if "nPollsters" in a else "nSeries"
        assert b[series_key] == a[series_key]
        old_series = {row["pollsterId"]: row for row in a["byPollster"]}
        new_series = {row["pollsterId"]: row for row in b["byPollster"]}
        assert set(old_series) == set(new_series)
        for institute in old_series:
            old_ids = old_series[institute]["pollIds"]
            new_ids = new_series[institute]["pollIds"]
            assert new_ids == old_ids + ([poll_id] if institute == "tatika" else [])
        old_rows = {row[id_key]: row for row in a["overall"]}
        new_rows = {row[id_key]: row for row in b["overall"]}
        assert set(old_rows) == set(new_rows)
        axes[axis] = {
            "counts": {
                "beforePolls": a["nPolls"], "afterPolls": b["nPolls"],
                "beforeDeltas": a["nDeltas"], "afterDeltas": b["nDeltas"],
                "beforePermutations": a["exactCounting"]["nPermutations"],
                "afterPermutations": b["exactCounting"]["nPermutations"],
            },
            "results": [
                {id_key: key, **{
                    field: {
                        "before": old_rows[key][field],
                        "after": new_rows[key][field],
                        "change": new_rows[key][field] - old_rows[key][field],
                    } for field in fields
                }} for key in old_rows
            ],
        }
    return {"addedPoll": poll, "axes": axes}


bloc = compare_report("analysis.json", "group", (
    "weightedNetDelta", "slopePerWeek", "pValue", "qValue",
    "wholeInstituteSignFlipP", "wholeInstituteSignFlipQ",
))
party = compare_report("party-analysis.json", "partyId", (
    "weightedNetDelta", "slopePerWeek", "pValue", "qValue",
    "wholeSeriesSignFlipP", "wholeSeriesSignFlipQ",
))
assert bloc["addedPoll"] == party["addedPoll"]
report = {
    "baseline": "2026-09-30", "updated": "2026-10-01",
    "design": "Same strict fieldwork rule, party and bloc definitions, and historical-quality weights; the sole eligible addition is one verified Tatika poll.",
    "addedPoll": bloc["addedPoll"], "blocs": bloc["axes"], "parties": party["axes"],
}
(HERE / "comparison-2026-10-01.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "addedPollId": report["addedPoll"]["pollId"],
    "pollCounts": report["blocs"]["primary"]["counts"],
}, ensure_ascii=False))
