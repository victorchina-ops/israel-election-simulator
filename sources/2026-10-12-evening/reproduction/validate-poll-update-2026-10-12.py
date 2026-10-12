"""Validate the October 12 N12/C14 update against frozen data and independent audits.

Both newly verified observations enter the forecast/history and strict fieldwork
cohort. Validate fresh exact tails, slopes, weighted changes, BH families and
whole-institute sign flips while preserving prior raw records and source code.
"""
from __future__ import annotations

from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-12"
CHECKPOINT = ROOT / "artifacts/poll-checks/2026-10-12-evening/before"
STRICT = ROOT / "artifacts/strict-post-close"
RECEIPT = ROOT / "artifacts/poll-checks/2026-10-12-evening/strict-validation.json"
EXPECTED = {
    "midgam_geva": {
        "oldId": "midgam_geva_2026-10-05", "id": "midgam_geva_2026-10-12", "sampleSize": 509,
        "candidate": "reviewed-n12-poll.json",
        "seats": {"yashar":23,"likud":20,"beyachad":13,"democrats":9,"yisrael_beiteinu":9,
                  "utj":7,"joint":8,"shas":8,"otzma":8,"rz_zehut":6,"raam":5,"hendel":4},
        "reportedPercentages": {"winter":1.8,"gantz":.9,"noam":.5,"haredi_public":.1},
    },
    "next_data": {
        "oldId": "next_data_2026-10-07", "id": "next_data_2026-10-12", "sampleSize": 538,
        "candidate": "reviewed-c14-poll.json",
        "seats": {"likud":29,"yashar":20,"shas":10,"democrats":10,"utj":8,"joint":8,
                  "rz_zehut":7,"otzma":7,"beyachad":7,"yisrael_beiteinu":5,"raam":5,"hendel":4},
        "reportedPercentages": {"winter":2.9,"noam":.9,"gantz":.6,"haredi_public":.6},
    },
}
PRIMARY = ROOT / "artifacts/poll-checks/2026-10-12-evening/tv-primary"



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
    manifest = read(CHECKPOINT / "manifest.json")
    checkpoint_hashes = {path.relative_to(CHECKPOINT).as_posix(): sha(path)
                         for path in CHECKPOINT.rglob("*") if path.is_file()}
    for relative, expected in manifest["files"].items():
        assert sha(CHECKPOINT / relative) == expected, ("checkpoint manifest mismatch", relative)
    frozen_evidence_hashes = manifest["frozenEvidenceHashes"]
    for relative, expected in frozen_evidence_hashes.items():
        assert (ROOT / relative).is_file() and sha(ROOT / relative) == expected, ("previous frozen evidence changed", relative)
    preserved_code_hashes = {}
    for family in ["authorContentHashes", "protectedRuntimeHashes"]:
        for relative, expected in manifest[family].items():
            assert sha(ROOT / relative) == expected, ("authored content/protected runtime changed", relative)
            preserved_code_hashes[relative] = expected
    for relative, expected in manifest["files"].items():
        if relative.endswith((".py", ".mjs", ".jsx", ".js", ".css")) and relative != "dashboard/snapshot.mjs":
            assert sha(ROOT / relative) == expected, ("prior source code changed", relative)
            preserved_code_hashes[relative] = expected
    threshold_path = "dashboard/src/content/dashboard/threshold-page.css"
    assert sha(ROOT / threshold_path) == manifest["authorContentHashSource"]["thresholdStylesheetSha256"]
    input_hashes = {relative: sha(ROOT / relative) for relative in paths}
    current, history, snapshot, calibration, parties, bloc, party, bi, pi = [read(ROOT / relative) for relative in paths]
    before_current, before_history, before_snapshot = [read(CHECKPOINT / relative) for relative in paths[:3]]
    before_bloc = read(CHECKPOINT / paths[5])
    assert current["asOf"] == history["asOf"] == snapshot["asOf"] == bloc["asOf"] == party["asOf"] == DAY
    assert before_current["asOf"] == before_history["asOf"] == before_snapshot["asOf"] == manifest["baselineAsOf"]
    assert calibration == read(CHECKPOINT / paths[3]), "historical weights/calibration changed"
    assert parties == read(CHECKPOINT / paths[4]), "party catalogue changed"

    old_current, new_current = index(before_current["polls"], "id"), index(current["polls"], "id")
    old_history, new_history = index(before_history["polls"], "id"), index(history["polls"], "id")
    old_ids = {spec["oldId"] for spec in EXPECTED.values()}
    new_ids = {spec["id"] for spec in EXPECTED.values()}
    new_history_ids = {f"history_{poll_id}_current" for poll_id in new_ids}
    lifecycle = {f"history_{spec['oldId']}_current": spec["id"] for spec in EXPECTED.values()}
    assert len(old_current) == len(new_current) == manifest["activePollCount"] == 8
    assert len(old_history) == manifest["historyPollCount"] == 115
    assert len(new_history) == len(old_history) + len(EXPECTED) == 117
    assert set(old_current) - set(new_current) == old_ids
    assert set(new_current) - set(old_current) == new_ids
    assert set(new_history) - set(old_history) == new_history_ids
    assert not set(old_history) - set(new_history), "historical observation removed"
    for poll_id, old in old_current.items():
        if poll_id not in old_ids:
            assert new_current[poll_id] == old, ("unrelated active observation changed", poll_id)
    for poll_id, old in old_history.items():
        if poll_id in lifecycle:
            assert old["recordStatus"] == "current-reviewed-record"
            expected = dict(old, recordStatus="superseded-reviewed-record", replacedByPollId=lifecycle[poll_id])
            assert new_history[poll_id] == expected, ("superseded record changed beyond lifecycle metadata", poll_id)
        else:
            assert new_history[poll_id] == old, ("prior historical observation changed", poll_id)
    assert len({row["pollsterId"] for row in new_current.values()}) == len(new_current)
    for row in list(new_current.values()) + list(new_history.values()):
        assert sum(row["seats"].values()) == 120, row["id"]
        assert all(isinstance(value, int) and value >= 0 for value in row["seats"].values()), row["id"]

    source_hashes = {}
    candidate_hashes = {}
    candidates = {}
    for pollster_id, spec in EXPECTED.items():
        candidate_path = PRIMARY / spec["candidate"]
        candidate = read(candidate_path)
        candidates[pollster_id] = candidate
        candidate_hashes[candidate_path.relative_to(ROOT).as_posix()] = sha(candidate_path)
        assert candidate["id"] == spec["id"] and candidate["fieldworkVerified"]
        assert candidate["sourceTier"] == "original-publisher"
        doc = candidate["sourceDocument"]
        assert doc["primaryPublicationVerified"] and doc["publicationCrossChecked"]
        for filename_key, hash_key in [("fileName", "sha256"), ("extractFileName", "extractSha256"),
                                       ("originalGraphicFileName", "originalGraphicSha256")]:
            if doc.get(filename_key):
                source_path = PRIMARY / doc[filename_key]
                assert source_path.is_file() and sha(source_path) == doc[hash_key], ("primary evidence hash mismatch", source_path)
                source_hashes[source_path.relative_to(ROOT).as_posix()] = sha(source_path)
        active = new_current[spec["id"]]
        archived = new_history[f"history_{spec['id']}_current"]
        for row in [active, archived]:
            assert row["date"] == DAY and row["pollsterId"] == pollster_id
            assert row["fieldworkStart"] == row["fieldworkEnd"] == DAY
            assert row["fieldworkStartTime"] is None and row["fieldworkEndTime"] is None
            assert row["sampleSize"] == spec["sampleSize"] == candidate["sampleSize"]
            assert {key: value for key, value in row["seats"].items() if value > 0} == spec["seats"]
            assert row["reportedPercentages"] == spec["reportedPercentages"] == candidate["reportedPercentages"]
            assert "israel_first" not in row["reportedPercentages"] and "other" not in row["reportedPercentages"]
            for party_id in spec["seats"]:
                assert party_id not in row["reportedPercentages"], ("unpublished passing-party vote share", party_id)
            for key in ["sourceUrl", "publishedAt", "updatedAt", "samplingMethod", "initialSampleSize",
                        "invitedSampleSize", "reportedMarginOfErrorPct", "sourceBlocSeats", "sourceBlocDefinitions"]:
                assert row.get(key) == candidate.get(key), ("candidate metadata differs", pollster_id, key)
            assert row["percentageDenominator"] is None and row["panelProvider"] is None
            assert row["requiresReconstruction"], "model vote-share reconstruction mislabeled as published"
        assert archived["sourcePollId"] == active["id"]
        for key in set(active) | set(archived):
            if key not in {"id", "recordStatus", "sourcePollId", "archiveSourceUrl"}:
                assert active.get(key) == archived.get(key), ("current/history mismatch", key)
    n12, c14 = (new_current[EXPECTED[key]["id"]] for key in ["midgam_geva", "next_data"])
    close(n12["undecidedPct"], 8, "N12 approximate undecided")
    assert n12["undecidedPctApproximate"] and not n12["undecidedDenominatorVerified"]
    close(n12["derivedUndecidedComponentSumPct"], sum(n12["reportedUndecidedBreakdown"].values()), "N12 undecided components")
    close(n12["derivedUndecidedComponentSumPct"], 8.1, "N12 separately derived undecided sum")
    close(c14["undecidedPct"], 5, "C14 undecided")
    assert not c14["undecidedDenominatorVerified"]
    assert c14["sourceBlocSeats"] == {"coalition":61, "opposition":46, "arab_parties":13}
    assert c14["sourceBlocReconciliation"]["publishedLeftIncludesHendel"]
    assert c14["sourceBlocReconciliation"]["fixedNonArabOppositionExcludingHendel"] == 42
    assert c14["sourceBlocReconciliation"]["fixedUnassignedHendel"] == c14["seats"]["hendel"] == 4
    assert c14["modelOnlyPercentageIds"] == ["other"]
    assert c14["unmodelledNamedParties"] == candidates["next_data"]["unmodelledNamedParties"]
    close(c14["unmodelledNamedParties"][0]["pct"], .1, "named extra list share")

    assert bloc["cohort"] == party["cohort"]
    old_cohort, new_cohort = index(before_bloc["cohort"], "pollId"), index(bloc["cohort"], "pollId")
    assert len(old_cohort) == 44 and len(new_cohort) == len(old_cohort) + len(EXPECTED) == 46
    assert set(new_cohort) - set(old_cohort) == new_history_ids
    assert not set(old_cohort) - set(new_cohort)
    for poll_id, old in old_cohort.items():
        assert new_cohort[poll_id] == old, ("prior cohort record changed", poll_id)
    for pollster_id, spec in EXPECTED.items():
        row = new_cohort[f"history_{spec['id']}_current"]
        assert row["eligibleStrict"] and row["publicationDate"] == row["fieldworkStart"] == row["fieldworkEnd"] == DAY
        assert row["sampleSize"] == spec["sampleSize"]
        found = set()
        for evidence in row.get("evidence", []):
            if evidence.get("file") and evidence.get("sha256"):
                path = ROOT / evidence["file"]
                assert path.is_file() and sha(path) == evidence["sha256"], ("cohort source evidence hash mismatch", path)
                source_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
                found.add(sha(path))
        if row.get("evidencePath") and row.get("evidenceSha256"):
            path = ROOT / row["evidencePath"]
            assert path.is_file() and sha(path) == row["evidenceSha256"]
            source_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
            found.add(sha(path))
        assert candidates[pollster_id]["sourceDocument"]["sha256"] in found, "strict fieldwork lacks original publisher evidence"
    eligible = [row for row in new_cohort.values() if row["eligibleStrict"]]
    excluded = [row for row in new_cohort.values() if not row["eligibleStrict"]]
    assert {key for key, row in new_cohort.items() if row["eligibleStrict"]} == {
        key for key, row in old_cohort.items() if row["eligibleStrict"]} | new_history_ids
    for row in eligible:
        assert bloc["closure"]["firstEligibleFieldworkDate"] <= row["fieldworkStart"] <= row["fieldworkEnd"] <= row["publicationDate"]
    assert len(excluded) == 5
    assert all(row.get("fieldworkStart") is None or row.get("fieldworkEnd") is None for row in excluded)
    kan = new_cohort["history_kantar_2026-10-11_current"]
    assert not kan["eligibleStrict"] and kan["fieldworkStart"] is None and kan["fieldworkEnd"] is None

    coverage = snapshot["coverage"]
    n_series = len(bloc["primary"]["byPollster"])
    n_parties = len(party["testedPartyIds"])
    n_groups = len(bloc["primary"]["overall"])
    n_polls = len(eligible)
    n_deltas = sum(len(series["pollIds"])-1 for series in bloc["primary"]["byPollster"])
    assert (n_polls, n_series, n_deltas, n_parties, len(excluded)) == (41,8,33,17,5)
    assert coverage["pollCount"] == n_polls and coverage["seriesCount"] == n_series
    assert coverage["deltaCount"] == n_deltas and coverage["partyCount"] == n_parties and coverage["excludedPollCount"] == len(excluded)
    assert n_groups == 3 and n_deltas == n_polls - n_series
    for key, value in before_snapshot["coverage"].items():
        if key in {"pollCount", "deltaCount"}:
            expected_value = value + len(EXPECTED)
        elif key == "to":
            expected_value = max(row["fieldworkEnd"] for row in eligible)
        else:
            expected_value = value
        assert coverage[key] == expected_value, ("unexpected coverage", key)
    assert len(snapshot["rows"]) == len({row["partyId"] for row in snapshot["rows"]}) == n_parties
    assert snapshot["weightMode"] == before_snapshot["weightMode"] == "quality"
    assert snapshot["methodology"]["fixedSnapshot"] and not snapshot["methodology"]["usesCurrentControls"]
    assert [{key:value for key,value in row.items() if key != "nPolls"} for row in snapshot["weights"]] == [
        {key:value for key,value in row.items() if key != "nPolls"} for row in before_snapshot["weights"]]
    before_weights = index(before_snapshot["weights"], "pollsterId")
    for row in snapshot["weights"]:
        assert row["nPolls"] == before_weights[row["pollsterId"]]["nPolls"] + (1 if row["pollsterId"] in EXPECTED else 0)
    assert [{key:value for key,value in row.items() if key != "byPollster"} for row in snapshot["rows"]] == party["primary"]["overall"]
    labels = {row["pollsterId"]: row["label"] for row in snapshot["weights"]}
    for row in snapshot["rows"]:
        expected_details = []
        for series in party["primary"]["byPollster"]:
            entry = next(value for value in series["parties"] if value["partyId"] == row["partyId"])
            expected_details.append({**entry, "label": labels[series["pollsterId"]],
                                     "pollIds": series["pollIds"], "dates": series["publicationDates"],
                                     "timeDaysFromFirst": series["timeDaysFromFirst"]})
        assert row["byPollster"] == expected_details, ("snapshot individual rows differ from canonical audit", row["partyId"])
    snapshot_cohort = index(snapshot["cohort"], "pollId")
    assert set(snapshot_cohort) == set(new_cohort)
    for poll_id, entry in snapshot_cohort.items():
        original = new_cohort[poll_id]
        for key in ["pollsterId", "publicationDate", "fieldworkStart", "fieldworkEnd", "eligibleStrict"]:
            assert entry[key] == original[key], ("snapshot cohort metadata differs", poll_id, key)
        if original.get("sourceUrl", "").startswith(("http://", "https://")):
            assert original["sourceUrl"] in entry["sourceUrls"], ("snapshot missing original source URL", poll_id)
    assert snapshot["provenance"]["historySha256"] == bloc["historySha256"] == party["historySha256"] == input_hashes[paths[1]]
    assert snapshot["provenance"]["analysisSha256"] == input_hashes[paths[6]]
    assert snapshot["provenance"]["partiesSha256"] == party["partiesSha256"] == input_hashes[paths[4]]
    assert party["baseAnalysisSha256"] == input_hashes[paths[5]]
    assert bloc["normalizedHistoricalWeights"] == party["normalizedHistoricalWeights"] == before_bloc["normalizedHistoricalWeights"]
    close(sum(bloc["normalizedHistoricalWeights"].values()),1,"normalized weights")

    exact = math.prod(math.factorial(len(series["pollIds"])) for series in bloc["primary"]["byPollster"])
    assert int(snapshot["methodology"]["permutationsExact"]) == exact
    assert snapshot["methodology"]["partyTests"] == n_parties
    assert snapshot["methodology"]["individualTests"] == n_parties * n_series
    assert snapshot["methodology"]["signPatterns"] == 2 ** n_series
    assert int(bi["totalExact"]) == int(pi["nPermutationsExact"]) == exact
    assert bi["cohortPolls"] == pi["nPolls"] == n_polls
    assert bi["cohortPollsters"] == pi["nSeries"] == n_series
    assert pi["nParties"] == n_parties and pi["nIndividualTests"] == n_parties * n_series
    assert pi["historySha256"] == input_hashes[paths[1]] and pi["cohortSha256"] == input_hashes[paths[5]]
    for doc in [bloc, party]:
        for axis in ["primary", "publicationDateSensitivity"]:
            result = doc[axis]
            assert result["nPolls"] == n_polls and result["nDeltas"] == n_deltas
            assert int(result["exactCounting"]["nPermutationsExact"]) == exact
            for row,number,count in zip(result["overall"],result["exactCounting"]["pValues"],result["exactCounting"]["extremeCountsExact"]):
                close(number,int(count)/exact,("exact probability",axis))
                close(row["pValue"],number,("overall p linked to exact counter",axis))
            for series in result["byPollster"]:
                assert series["weight"] == bloc["normalizedHistoricalWeights"][series["pollsterId"]]
                times = [midpoint(new_cohort[poll_id]) if axis == "primary" else date.fromisoformat(new_cohort[poll_id]["publicationDate"]).toordinal()
                         for poll_id in series["pollIds"]]
                assert series["timeDaysFromFirst"] == [value-times[0] for value in times]
                assert all(new_cohort[poll_id]["eligibleStrict"] for poll_id in series["pollIds"])
                assert series.get("publicationDates", series.get("dates")) == [new_cohort[poll_id]["publicationDate"] for poll_id in series["pollIds"]]
                values_key, id_key = ("groups", "group") if doc is bloc else ("parties", "partyId")
                relative_days = [value-times[0] for value in times]
                centered = [value - sum(relative_days)/len(relative_days) for value in relative_days]
                denominator = sum(value*value for value in centered)
                assert denominator > 0
                coefficients = [7*value/denominator for value in centered]
                for value in series[values_key]:
                    identity = value[id_key]
                    expected_seats = [sum(new_history[poll_id]["seats"].get(party_id,0) for party_id in bloc["groups"][identity])
                                      if doc is bloc else new_history[poll_id]["seats"].get(identity,0)
                                      for poll_id in series["pollIds"]]
                    assert value["seats"] == expected_seats, ("series not drawn from canonical observations",axis,series["pollsterId"],identity)
                    slope = sum(coefficient*seat for coefficient,seat in zip(coefficients,expected_seats))
                    close(value["slopePerWeek"],slope,("independent raw-input OLS",axis,series["pollsterId"],identity))
                    assert value["netDelta"] == expected_seats[-1]-expected_seats[0]
                    if axis == "publicationDateSensitivity":
                        if len(set(expected_seats)) == 1:
                            expected_p = 1.0
                        else:
                            extreme = sum(abs(sum(coefficient*seat for coefficient,seat in zip(coefficients,permutation))) >= abs(slope)-1e-12
                                          for permutation in itertools.permutations(expected_seats))
                            expected_p = extreme/math.factorial(len(expected_seats))
                        close(value["pValue"],expected_p,("independent publication-axis individual p",series["pollsterId"],identity))
            for value in result["overall"]:
                weighted_slope = sum(series["weight"]*next(row["slopePerWeek"] for row in series[values_key] if row[id_key] == value[id_key])
                                     for series in result["byPollster"])
                close(value["slopePerWeek"],weighted_slope,("independent weighted OLS",axis,value[id_key]))

    assert [int(value) for value in bloc["primary"]["exactCounting"]["extremeCountsExact"]] == [int(value) for value in bi["countsExact"]]
    for i,row in enumerate(bloc["primary"]["overall"]):
        assert row["group"] == bi["groups"][i]
        close(row["slopePerWeek"],bi["slopes"][i],("independent bloc slope",row["group"]))
        close(row["pValue"],bi["p"][i],("independent bloc p",row["group"]))
    independent_bloc_series = index(bi["individual"],"pollsterId")
    for series in bloc["primary"]["byPollster"]:
        independent = independent_bloc_series[series["pollsterId"]]
        for i,row in enumerate(series["groups"]):
            close(row["slopePerWeek"],independent["slope"][i],("independent individual bloc slope",series["pollsterId"],row["group"]))
            close(row["pValue"],independent["p"][i],("independent individual bloc p",series["pollsterId"],row["group"]))
    independent_parties = index(pi["overall"],"partyId")
    for i,row in enumerate(party["primary"]["overall"]):
        other = independent_parties[row["partyId"]]
        assert int(party["primary"]["exactCounting"]["extremeCountsExact"][i]) == int(other["extremeCountExact"])
        for key,alias in [("slopePerWeek","slopePerWeek"),("weightedNetDelta","netDelta"),("pValue","p"),
                          ("qValue","q"),("wholeSeriesSignFlipP","signFlipP"),("wholeSeriesSignFlipQ","signFlipQ")]:
            close(row[key],other[alias],("independent party",row["partyId"],key))
    individual_parties = {(row["pollsterId"],row["partyId"]):row for row in pi["byPollster"]}
    assert len(individual_parties) == n_parties * n_series
    for series in party["primary"]["byPollster"]:
        for row in series["parties"]:
            other = individual_parties[(series["pollsterId"],row["partyId"])]
            for key,alias in [("slopePerWeek","slopePerWeek"),("netDelta","delta"),("pValue","p"),("qValue","q")]:
                close(row[key],other[alias],("independent individual party",series["pollsterId"],row["partyId"],key))
            assert row["seats"] == other["series"]
    for axis in ["primary", "publicationDateSensitivity"]:
        for doc,values_key,id_key,pkey,qkey in [
            (bloc,"groups","group","wholeInstituteSignFlipP","wholeInstituteSignFlipQ"),
            (party,"parties","partyId","wholeSeriesSignFlipP","wholeSeriesSignFlipQ")]:
            result=doc[axis]
            bh(result["overall"],"pValue","qValue")
            bh(result["overall"],pkey,qkey)
            bh([row for series in result["byPollster"] for row in series[values_key]],"pValue","qValue")
            for row in result["overall"]:
                sign_flip(row,result["byPollster"],values_key,id_key,pkey)
                weighted_delta=sum(series["weight"]*next(value["netDelta"] for value in series[values_key] if value[id_key]==row[id_key])
                                   for series in result["byPollster"])
                close(row["weightedNetDelta"],weighted_delta,("weighted endpoint change",axis,row[id_key]))
    assert all(sha(ROOT / relative) == value for relative,value in input_hashes.items()), "inputs changed during validation"
    assert all(sha(ROOT / relative) == value for relative,value in candidate_hashes.items()), "reviewed candidates changed"
    assert all(sha(ROOT / relative) == value for relative,value in source_hashes.items()), "source evidence changed"
    assert all(sha(CHECKPOINT / relative) == value for relative,value in checkpoint_hashes.items()), "immutable checkpoint changed"
    assert all(sha(ROOT / relative) == value for relative,value in preserved_code_hashes.items()), "preserved code changed"
    assert all(sha(ROOT / relative) == value for relative,value in frozen_evidence_hashes.items()), "prior frozen evidence changed during validation"

    report = {
        "passed":True,"status":"PASS","asOf":DAY,"runId":"evening","newPollCount":len(EXPECTED),
        "activePolls":len(new_current),"historyPolls":len(new_history),"candidatePolls":len(new_cohort),
        "polls":n_polls,"series":n_series,"deltas":n_deltas,"parties":n_parties,
        "individualTests":n_parties*n_series,"individualBlocTests":n_groups*n_series,
        "exactPermutations":str(exact),"excludedPollCount":len(excluded),
        "removedActivePollIds":sorted(old_ids),"addedActivePollIds":sorted(new_ids),"addedHistoryPollIds":sorted(new_history_ids),
        "newPollsIncludedInForecast":True,"newPollsIncludedInStrictTrends":True,"newStrictEligiblePollIds":sorted(new_history_ids),
        "priorUnknownFieldworkCohortUnchanged":True,"kanOct11FieldworkStillUnknown":True,
        "allPriorHistoricalObservationsPreserved":True,"allOtherActiveObservationsPreserved":True,
        "priorHistoryMetadataExceptions":[{"pollId":key,"recordStatus":"superseded-reviewed-record","replacedByPollId":value,"allOtherFieldsUnchanged":True} for key,value in sorted(lifecycle.items())],
        "historicalWeightsAndCatalogueUnchanged":True,"allPriorStrictCohortRowsUnchanged":True,
        "preservedAuthoredAndProtectedCode":True,"thresholdStylesheetSha256":sha(ROOT/threshold_path),
        "allPriorFrozenEvidencePreserved":True,"priorFrozenEvidenceCount":len(frozen_evidence_hashes),
        "snapshotIndividualRowsAndCohortMatchAudit":True,
        "independentAgreement":"Exact bloc/party tails, slopes, p/q, changes, individual tests, BH and whole-institute sign flips verified within 1e-12.",
        "bhFamilySizes":{"parties":n_parties,"blocs":n_groups,"individualParties":n_parties*n_series,"individualBlocs":n_groups*n_series},
        "correctedPartyFindings":[row["partyId"] for row in party["primary"]["overall"] if row["qValue"]<.05],
        "correctedBlocFindings":[row["group"] for row in bloc["primary"]["overall"] if row["qValue"]<.05],
        "correctedPartySensitivityFindings":[row["partyId"] for row in party["primary"]["overall"] if row["wholeSeriesSignFlipQ"]<.05],
        "correctedBlocSensitivityFindings":[row["group"] for row in bloc["primary"]["overall"] if row["wholeInstituteSignFlipQ"]<.05],
        "c14PublishedLeftIncludesHendel":True,"passingPartyPercentagesRemainUnpublished":True,
        "sourceEvidenceSha256Verified":True,"sourceEvidenceHashes":source_hashes,"candidateHashes":candidate_hashes,
        "inputHashes":input_hashes,"checkpointHashes":checkpoint_hashes,"preservedCodeHashes":preserved_code_hashes,
        "validatorSha256":sha(Path(__file__)),"checkpoint":CHECKPOINT.relative_to(ROOT).as_posix(),
    }
    immutable_write(RECEIPT,report)
    (STRICT/"party-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:report[key] for key in ["status","asOf","newPollCount","polls","series","deltas","parties","exactPermutations","correctedPartyFindings","correctedBlocFindings"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
