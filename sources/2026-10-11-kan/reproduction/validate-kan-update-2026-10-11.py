"""Validate the October 11 Kan update against frozen inputs and independent audits.

The newly published observation enters the forecast/history but is excluded from
strict trends until its fieldwork interval is verified. No statistical result is
reused merely by removing a row: freshly generated canonical/independent outputs
must agree and must reproduce the unchanged eligible cohort's prior numbers.
"""
from __future__ import annotations

from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-11"
CHECKPOINT = ROOT / "artifacts/poll-checks/2026-10-11/before"
STRICT = ROOT / "artifacts/strict-post-close"
RECEIPT = ROOT / "artifacts/poll-checks/2026-10-11/strict-validation.json"
OLD_CURRENT_ID = "kantar_2026-10-08"
NEW_CURRENT_ID = "kantar_2026-10-11"
OLD_HISTORY_ID = "history_kantar_2026-10-08_current"
NEW_HISTORY_ID = "history_kantar_2026-10-11_current"
EXPECTED_SEATS = {
    "yashar": 22, "likud": 20, "beyachad": 12, "democrats": 8,
    "yisrael_beiteinu": 8, "utj": 8, "joint": 8, "shas": 7,
    "otzma": 9, "rz_zehut": 5, "raam": 5, "winter": 4, "hendel": 4,
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected, label):
    assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12), (label, actual, expected)


def index(rows, key):
    result = {row[key]: row for row in rows}
    assert len(result) == len(rows), ("duplicate", key)
    return result


def bh(rows, pkey, qkey):
    ordered = sorted(rows, key=lambda row: row[pkey])
    running = 1.0
    for rank in range(len(ordered), 0, -1):
        row = ordered[rank - 1]
        running = min(running, row[pkey] * len(ordered) / rank, 1.0)
        close(row[qkey], running, ("BH", pkey, row.get("partyId", row.get("group"))))


def midpoint(row):
    return (date.fromisoformat(row["fieldworkStart"]).toordinal()
            + date.fromisoformat(row["fieldworkEnd"]).toordinal()) / 2


def sign_flip(row, series, values_key, identity_key, pkey):
    contributions = [entry["weight"] * next(value["slopePerWeek"] for value in entry[values_key]
                    if value[identity_key] == row[identity_key]) for entry in series]
    extreme = sum(abs(sum(sign * value for sign, value in zip(signs, contributions)))
                  >= abs(row["slopePerWeek"]) - 1e-12
                  for signs in itertools.product([-1, 1], repeat=len(contributions)))
    close(row[pkey], extreme / (2 ** len(contributions)), ("sign flip", row[identity_key]))


def immutable_write(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.exists():
        assert path.read_bytes() == body, f"Dated receipt differs; preserve it and use a distinct reviewed run: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def main():
    paths = [
        "data/current-polls.json", "data/poll-history.json", "data/strict-party-trends.json",
        "data/calibration.json", "data/parties.json", "artifacts/strict-post-close/analysis.json",
        "artifacts/strict-post-close/party-analysis.json",
        "artifacts/strict-post-close/independent-strict-numeric-audit.json",
        "artifacts/strict-post-close/party-independent.json",
    ]
    for relative in paths:
        assert (ROOT / relative).is_file(), relative
        assert (CHECKPOINT / relative).is_file(), ("missing checkpoint", relative)
    checkpoint_hashes = {path.relative_to(CHECKPOINT).as_posix(): sha(path)
                         for path in CHECKPOINT.rglob("*") if path.is_file()}
    for relative, expected in read(CHECKPOINT / "manifest.json")["files"].items():
        assert sha(CHECKPOINT / relative) == expected, ("checkpoint manifest mismatch", relative)
    input_hashes = {relative: sha(ROOT / relative) for relative in paths}
    current, history, snapshot, calibration, parties, bloc, party, bi, pi = [read(ROOT / relative) for relative in paths]
    before_current, before_history, before_snapshot = [read(CHECKPOINT / relative) for relative in paths[:3]]
    before_bloc, before_party = [read(CHECKPOINT / relative) for relative in paths[5:7]]
    assert current["asOf"] == history["asOf"] == snapshot["asOf"] == bloc["asOf"] == party["asOf"] == DAY
    assert before_current["asOf"] == before_history["asOf"] == before_snapshot["asOf"] == "2026-10-10"
    assert calibration == read(CHECKPOINT / paths[3]), "historical weights/calibration changed"
    assert parties == read(CHECKPOINT / paths[4]), "party catalogue changed"

    old_current, new_current = index(before_current["polls"], "id"), index(current["polls"], "id")
    old_history, new_history = index(before_history["polls"], "id"), index(history["polls"], "id")
    assert len(old_current) == len(new_current) == 8
    assert len(old_history) == 114 and len(new_history) == 115
    assert set(old_current) - set(new_current) == {OLD_CURRENT_ID}
    assert set(new_current) - set(old_current) == {NEW_CURRENT_ID}
    assert set(new_history) - set(old_history) == {NEW_HISTORY_ID}
    assert not set(old_history) - set(new_history), "historical observation removed"
    for poll_id, old in old_current.items():
        if poll_id != OLD_CURRENT_ID:
            assert new_current[poll_id] == old, ("unrelated active observation changed", poll_id)
    for poll_id, old in old_history.items():
        if poll_id == OLD_HISTORY_ID:
            assert old["recordStatus"] == "current-reviewed-record"
            expected = dict(old)
            expected["recordStatus"] = "superseded-reviewed-record"
            expected["replacedByPollId"] = NEW_CURRENT_ID
            assert new_history[poll_id] == expected, ("superseded observation changed beyond lifecycle metadata", poll_id)
        else:
            assert new_history[poll_id] == old, ("prior historical observation changed", poll_id)
    assert len({row["pollsterId"] for row in new_current.values()}) == 8
    for row in list(new_current.values()) + list(new_history.values()):
        assert sum(row["seats"].values()) == 120, row["id"]
        assert all(isinstance(value, int) and value >= 0 for value in row["seats"].values()), row["id"]

    active, archived = new_current[NEW_CURRENT_ID], new_history[NEW_HISTORY_ID]
    for row in [active, archived]:
        assert row["date"] == DAY and row["pollsterId"] == "kantar"
        assert row.get("fieldworkStart") is None and row.get("fieldworkEnd") is None, "unverified fieldwork fabricated"
        assert row["sampleSize"] == 554
        assert {key: value for key, value in row["seats"].items() if value > 0} == EXPECTED_SEATS
        for party_id, seats in EXPECTED_SEATS.items():
            assert party_id not in row.get("reportedPercentages", {}), ("unpublished national vote share", party_id)
        assert row.get("sourceUrl"), "missing source provenance"
    assert archived["sourcePollId"] == active["id"]
    for key in set(active) | set(archived):
        if key not in {"id", "recordStatus", "sourcePollId", "archiveSourceUrl"}:
            assert active.get(key) == archived.get(key), ("current/history mismatch", key)

    assert bloc["cohort"] == party["cohort"]
    old_cohort, new_cohort = index(before_bloc["cohort"], "pollId"), index(bloc["cohort"], "pollId")
    assert len(old_cohort) == 43 and len(new_cohort) == 44
    assert set(new_cohort) - set(old_cohort) == {NEW_HISTORY_ID}
    assert not set(old_cohort) - set(new_cohort)
    for poll_id, old in old_cohort.items():
        assert new_cohort[poll_id] == old, ("prior cohort record changed", poll_id)
    new_row = new_cohort[NEW_HISTORY_ID]
    assert new_row["publicationDate"] == DAY and not new_row["eligibleStrict"]
    assert new_row.get("fieldworkStart") is None and new_row.get("fieldworkEnd") is None
    assert new_row["sampleSize"] == 554
    assert {key for key, row in old_cohort.items() if row["eligibleStrict"]} == {
        key for key, row in new_cohort.items() if row["eligibleStrict"]}
    eligible = [row for row in new_cohort.values() if row["eligibleStrict"]]
    for row in eligible:
        assert bloc["closure"]["firstEligibleFieldworkDate"] <= row["fieldworkStart"] <= row["fieldworkEnd"] <= row["publicationDate"]

    evidence_hashes = {}
    for evidence in new_row.get("evidence", []):
        if evidence.get("file") and evidence.get("sha256"):
            path = ROOT / evidence["file"]
            assert path.is_file() and sha(path) == evidence["sha256"], ("source evidence hash mismatch", path)
            evidence_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
    if new_row.get("evidencePath") and new_row.get("evidenceSha256"):
        path = ROOT / new_row["evidencePath"]
        assert path.is_file() and sha(path) == new_row["evidenceSha256"]
        evidence_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
    assert evidence_hashes, "new observation missing hashed source evidence"

    coverage = snapshot["coverage"]
    assert (coverage["pollCount"], coverage["seriesCount"], coverage["deltaCount"], coverage["partyCount"],
            coverage["excludedPollCount"]) == (39, 8, 31, 17, 5)
    assert len(eligible) == 39 and sum(not row["eligibleStrict"] for row in new_cohort.values()) == 5
    assert all(row.get("fieldworkStart") is None or row.get("fieldworkEnd") is None
               for row in new_cohort.values() if not row["eligibleStrict"])
    for key, value in before_snapshot["coverage"].items():
        assert coverage[key] == (value + 1 if key == "excludedPollCount" else value), ("unexpected coverage change", key)
    assert len(party["testedPartyIds"]) == len(snapshot["rows"]) == 17
    assert len({row["partyId"] for row in snapshot["rows"]}) == 17
    assert snapshot["weightMode"] == before_snapshot["weightMode"] == "quality"
    assert snapshot["methodology"]["fixedSnapshot"] and not snapshot["methodology"]["usesCurrentControls"]
    assert snapshot["weights"] == before_snapshot["weights"]
    assert snapshot["rows"] == before_snapshot["rows"], "strict snapshot numerical rows changed despite unchanged cohort"
    assert [{key: value for key, value in row.items() if key != "byPollster"} for row in snapshot["rows"]] == party["primary"]["overall"]
    assert snapshot["provenance"]["historySha256"] == bloc["historySha256"] == party["historySha256"] == input_hashes[paths[1]]
    assert snapshot["provenance"]["analysisSha256"] == input_hashes[paths[6]]
    assert snapshot["provenance"]["partiesSha256"] == party["partiesSha256"] == input_hashes[paths[4]]
    assert party["baseAnalysisSha256"] == input_hashes[paths[5]]
    assert bloc["normalizedHistoricalWeights"] == party["normalizedHistoricalWeights"] == before_bloc["normalizedHistoricalWeights"]
    close(sum(bloc["normalizedHistoricalWeights"].values()), 1, "normalized weights")

    exact = math.prod(math.factorial(len(series["pollIds"])) for series in bloc["primary"]["byPollster"])
    assert int(bi["totalExact"]) == int(pi["nPermutationsExact"]) == exact
    assert bi["cohortPolls"] == pi["nPolls"] == coverage["pollCount"]
    assert bi["cohortPollsters"] == pi["nSeries"] == coverage["seriesCount"]
    assert pi["nParties"] == coverage["partyCount"]
    assert pi["nIndividualTests"] == coverage["partyCount"] * coverage["seriesCount"]
    assert pi["historySha256"] == input_hashes[paths[1]] and pi["cohortSha256"] == input_hashes[paths[5]]
    for doc, old in [(bloc, before_bloc), (party, before_party)]:
        for axis in ["primary", "publicationDateSensitivity"]:
            result = doc[axis]
            assert result == old[axis], ("strict numerical output changed despite unchanged eligible cohort", axis)
            assert result["nPolls"] == 39 and result["nDeltas"] == 31
            assert int(result["exactCounting"]["nPermutationsExact"]) == exact
            for number, count in zip(result["exactCounting"]["pValues"], result["exactCounting"]["extremeCountsExact"]):
                close(number, int(count) / exact, ("exact probability", axis))
            for series in result["byPollster"]:
                if axis == "primary":
                    times = [midpoint(new_cohort[poll_id]) for poll_id in series["pollIds"]]
                    assert series["timeDaysFromFirst"] == [value - times[0] for value in times]

    # Reconstruct BH and whole-institute sign-flip tails independently.
    assert [int(value) for value in bloc["primary"]["exactCounting"]["extremeCountsExact"]] == [int(value) for value in bi["countsExact"]]
    for i, row in enumerate(bloc["primary"]["overall"]):
        assert row["group"] == bi["groups"][i]
        close(row["slopePerWeek"], bi["slopes"][i], ("independent bloc slope", row["group"]))
        close(row["pValue"], bi["p"][i], ("independent bloc p", row["group"]))
        sign_flip(row, bloc["primary"]["byPollster"], "groups", "group", "wholeInstituteSignFlipP")
    independent_bloc_series = index(bi["individual"], "pollsterId")
    for series in bloc["primary"]["byPollster"]:
        independent = independent_bloc_series[series["pollsterId"]]
        for i, row in enumerate(series["groups"]):
            close(row["slopePerWeek"], independent["slope"][i], ("independent individual bloc slope", series["pollsterId"], row["group"]))
            close(row["pValue"], independent["p"][i], ("independent individual bloc p", series["pollsterId"], row["group"]))
    independent_parties = index(pi["overall"], "partyId")
    for i, row in enumerate(party["primary"]["overall"]):
        other = independent_parties[row["partyId"]]
        assert int(party["primary"]["exactCounting"]["extremeCountsExact"][i]) == int(other["extremeCountExact"])
        for key, alias in [("slopePerWeek", "slopePerWeek"), ("weightedNetDelta", "netDelta"), ("pValue", "p"),
                           ("qValue", "q"), ("wholeSeriesSignFlipP", "signFlipP"), ("wholeSeriesSignFlipQ", "signFlipQ")]:
            close(row[key], other[alias], ("independent party", row["partyId"], key))
        sign_flip(row, party["primary"]["byPollster"], "parties", "partyId", "wholeSeriesSignFlipP")
    individual_parties = {(row["pollsterId"], row["partyId"]): row for row in pi["byPollster"]}
    assert len(individual_parties) == pi["nIndividualTests"]
    for series in party["primary"]["byPollster"]:
        for row in series["parties"]:
            other = individual_parties[(series["pollsterId"], row["partyId"])]
            for key, alias in [("slopePerWeek", "slopePerWeek"), ("netDelta", "delta"), ("pValue", "p"), ("qValue", "q")]:
                close(row[key], other[alias], ("independent individual party", series["pollsterId"], row["partyId"], key))
            assert row["seats"] == other["series"]
    for axis in ["primary", "publicationDateSensitivity"]:
        bh(bloc[axis]["overall"], "pValue", "qValue")
        bh(bloc[axis]["overall"], "wholeInstituteSignFlipP", "wholeInstituteSignFlipQ")
        bh([row for series in bloc[axis]["byPollster"] for row in series["groups"]], "pValue", "qValue")
        bh(party[axis]["overall"], "pValue", "qValue")
        bh(party[axis]["overall"], "wholeSeriesSignFlipP", "wholeSeriesSignFlipQ")
        bh([row for series in party[axis]["byPollster"] for row in series["parties"]], "pValue", "qValue")
    assert all(sha(ROOT / relative) == value for relative, value in input_hashes.items()), "inputs changed during validation"
    assert all(sha(CHECKPOINT / relative) == value for relative, value in checkpoint_hashes.items()), "immutable checkpoint changed"

    report = {
        "passed": True, "status": "PASS", "asOf": DAY, "newPollCount": 1,
        "activePolls": len(new_current), "historyPolls": len(new_history),
        "candidatePolls": len(new_cohort), "polls": coverage["pollCount"], "series": coverage["seriesCount"],
        "deltas": coverage["deltaCount"], "parties": coverage["partyCount"], "individualTests": pi["nIndividualTests"],
        "exactPermutations": str(exact), "excludedPollCount": coverage["excludedPollCount"],
        "removedActivePollIds": [OLD_CURRENT_ID], "addedActivePollIds": [NEW_CURRENT_ID], "addedHistoryPollIds": [NEW_HISTORY_ID],
        "newPollIncludedInForecast": True, "newPollIncludedInStrictTrends": False,
        "strictExclusionReason": "Publication verified; original fieldwork interval not yet verified and remains null.",
        "allPriorHistoricalObservationsPreserved": True, "allOtherActiveObservationsPreserved": True,
        "priorHistoryMetadataException": {"pollId": OLD_HISTORY_ID, "recordStatus": "superseded-reviewed-record",
                                          "replacedByPollId": NEW_CURRENT_ID, "allOtherFieldsUnchanged": True},
        "sameEligibleCohortAndHistoricalWeights": True, "primaryAndPublicationAxisNumericalOutputsUnchanged": True,
        "independentAgreement": "Exact bloc/party tail counts, slopes, deltas, p/q, individual tests and sign-flip sensitivity agree within1e-12.",
        "correctedPartyFindings": [row["partyId"] for row in party["primary"]["overall"] if row["qValue"] < .05],
        "correctedBlocFindings": [row["group"] for row in bloc["primary"]["overall"] if row["qValue"] < .05],
        "correctedPartySensitivityFindings": [row["partyId"] for row in party["primary"]["overall"] if row["wholeSeriesSignFlipQ"] < .05],
        "correctedBlocSensitivityFindings": [row["group"] for row in bloc["primary"]["overall"] if row["wholeInstituteSignFlipQ"] < .05],
        "sourceEvidenceSha256Verified": True, "sourceEvidenceHashes": evidence_hashes,
        "inputHashes": input_hashes, "checkpointHashes": checkpoint_hashes,
        "validatorSha256": sha(Path(__file__)), "checkpoint": CHECKPOINT.relative_to(ROOT).as_posix(),
    }
    immutable_write(RECEIPT, report)
    (STRICT / "party-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["status", "asOf", "newPollCount", "polls", "series", "deltas", "parties",
                                                "exactPermutations", "correctedPartyFindings", "correctedBlocFindings"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
