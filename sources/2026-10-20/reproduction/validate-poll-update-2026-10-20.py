"""Validate the October 20 four-publisher update against frozen observations and audits.

Channel13 19October enters the forecast/history with unknown fieldwork excluded
from strict trends. N12/Channel14/Lazar have independently verified19Octoberfieldwork.
Validate exact tails, slopes, endpoint changes, BH families and institute sign flips
without changing earlier raw records, fieldwork decisions or protected source code.
"""
from __future__ import annotations

from datetime import date
import hashlib
import itertools
import json
import math
import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-20"
CHECKPOINT = ROOT / "artifacts/poll-checks/2026-10-20/before"
STRICT = ROOT / "artifacts/strict-post-close"
RECEIPT = ROOT / "artifacts/poll-checks/2026-10-20/strict-validation.json"
SOURCE_ROOT = ROOT / "artifacts/poll-checks/2026-10-20"
EXPECTED = {
    "midgam_geva": {
        "oldId": "midgam_geva_2026-10-12",
        "id": "midgam_geva_2026-10-19",
        "date": "2026-10-19",
        "sampleSize": 507,
        "fieldworkStart": "2026-10-19",
        "fieldworkEnd": "2026-10-19",
        "seats": {
            "yashar": 24,
            "likud": 21,
            "beyachad": 14,
            "democrats": 9,
            "yisrael_beiteinu": 8,
            "utj": 7,
            "joint": 9,
            "shas": 8,
            "otzma": 8,
            "rz_zehut": 7,
            "raam": 5
        },
        "reportedPercentages": {
            "winter": 2.8,
            "hendel": 2.1,
            "gantz": 1.4,
            "haredi_public": 0.2
        }
    },
    "hamadad_consortium": {
        "oldId": "hamadad_consortium_2026-10-14",
        "id": "hamadad_consortium_2026-10-19",
        "date": "2026-10-19",
        "sampleSize": 1016,
        "fieldworkStart": None,
        "fieldworkEnd": None,
        "seats": {
            "yashar": 20,
            "likud": 18,
            "beyachad": 14,
            "democrats": 9,
            "yisrael_beiteinu": 8,
            "utj": 7,
            "joint": 9,
            "shas": 7,
            "otzma": 7,
            "rz_zehut": 7,
            "raam": 6,
            "winter": 4,
            "hendel": 4
        },
        "reportedPercentages": {
            "haredi_public": 1.0
        }
    },
    "next_data": {
        "oldId": "next_data_2026-10-18",
        "id": "next_data_2026-10-19",
        "date": "2026-10-19",
        "sampleSize": 454,
        "fieldworkStart": "2026-10-19",
        "fieldworkEnd": "2026-10-19",
        "seats": {
            "likud": 30,
            "yashar": 19,
            "beyachad": 10,
            "democrats": 10,
            "shas": 10,
            "utj": 8,
            "rz_zehut": 7,
            "otzma": 7,
            "yisrael_beiteinu": 6,
            "joint": 8,
            "raam": 5
        },
        "reportedPercentages": {
            "hendel": 2.6,
            "winter": 2.2,
            "noam": 1.5,
            "haredi_public": 0.3
        }
    },
    "lazar": {
        "oldId": "lazar_2026-10-16",
        "id": "lazar_2026-10-20",
        "date": "2026-10-20",
        "sampleSize": 601,
        "fieldworkStart": "2026-10-19",
        "fieldworkEnd": "2026-10-19",
        "seats": {
            "yashar": 23,
            "likud": 19,
            "beyachad": 14,
            "democrats": 9,
            "yisrael_beiteinu": 8,
            "shas": 8,
            "utj": 7,
            "otzma": 8,
            "rz_zehut": 6,
            "joint": 8,
            "raam": 6,
            "hendel": 4
        },
        "reportedPercentages": {
            "winter": 2.9
        }
    }
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
    manifest = read(CHECKPOINT / "manifest.json")
    checkpoint_hashes = {path.relative_to(CHECKPOINT).as_posix(): sha(path)
                         for path in CHECKPOINT.rglob("*") if path.is_file()}
    for relative, expected in manifest["files"].items():
        assert sha(CHECKPOINT / relative) == expected, ("checkpoint manifest mismatch", relative)
    frozen_evidence_hashes = manifest["frozenEvidenceHashes"]
    for relative, expected in frozen_evidence_hashes.items():
        assert (ROOT / relative).is_file() and sha(ROOT / relative) == expected, ("previous frozen evidence changed", relative)
    plan_path = SOURCE_ROOT / "source-plan.json"
    plan = read(plan_path)
    assert plan["asOf"] == DAY and plan["publicCopyrightScopeReviewed"]
    plan_specs = {row["pollsterId"]:row for row in plan["polls"]}
    assert set(plan_specs) == set(EXPECTED)
    repair_input_hashes = {plan_path.relative_to(ROOT).as_posix():sha(plan_path)}
    # The newly reviewed enumeration backend changes storage, not the registered test.
    backend = ROOT/'scripts/exact_scalar_marginals_2026_10_20.py'
    wrapper = ROOT/'scripts/run-exact-trends-2026-10-20.py'
    scalar_proof_hashes = {
        'scalar-review/toy-equivalence.json':'13ac3bbdaa181f81bb9c0470524401eb10095616bbe618a9e312cd7bb055e13a',
        'scalar-review/archive19-equivalence.json':'0964a717fb92c33366a39d1e0f3107cd6cbf173ea4f62420bc3aa53d059b624a',
    }
    assert sha(backend)=='ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035'
    assert sha(wrapper)=='05c5f67926a5b5bb936e24266d0d9eb5d92753cc9f98f046a68ad6c4e7d9f85a'
    for relative,digest in scalar_proof_hashes.items():
        proof_path=SOURCE_ROOT/relative
        assert sha(proof_path)==digest
        proof=read(proof_path)
        assert proof['status']=='PASS' and proof['asOf']==DAY and proof['backendSha256']==sha(backend)
        if 'archive19' in relative:
            assert proof['checkpointManifestSha256']==sha(CHECKPOINT/'manifest.json')
            assert proof['wrapperSha256']==sha(wrapper)
            assert proof['allPrimaryAndPublicationAxisResultsAgree'] and proof['exactCombinedTailIntegersAgree']
            assert proof['independentDPTailsAgreeWithFrozenReference'] and proof['cohortAndWeightsAndEffectsUnchanged']
        else:
            assert proof['meanExactlyZero'] and proof['allMassesEqualFactorial'] and proof['noMonteCarlo']
            assert proof['largeMass']['pythonIntegerProductsAndTails'] and proof['largeMass']['primaryAndIndependentAndManualAgree']
        repair_input_hashes[proof_path.relative_to(ROOT).as_posix()]=digest
    independent_backend_path=SOURCE_ROOT/'scalar-review/independent-backend-review.json'
    assert sha(independent_backend_path)=='63991734402d20a1c19fada4389432b2bb64ef98bca4dac01853fc301a3a4cf7'
    independent_backend=read(independent_backend_path)
    assert independent_backend['status']=='PASS' and independent_backend['asOf']==DAY
    assert independent_backend['backendSha256']==sha(backend) and independent_backend['wrapperSha256']==sha(wrapper)
    assert independent_backend['archive19ExactTailIntegerStringsAgree'] and independent_backend['archive19CohortWeightsEffectsAgree']
    assert independent_backend['singleBlockBeyondInt64']['objectMassArrayVerified']
    repair_input_hashes[independent_backend_path.relative_to(ROOT).as_posix()]=sha(independent_backend_path)
    derive_review_path=SOURCE_ROOT/'scalar-review/derive-change-review-r2.json'
    assert sha(derive_review_path)=='5634a1f19b3762c2f2826a4090a48415a6671076ff72e85c10a43f9e046a9161'
    derive_review=read(derive_review_path)
    assert derive_review['status']=='REVIEWED-SCOPED-UPGRADE' and derive_review['asOf']==DAY
    assert derive_review['path']=='scripts/derive-strict-trends-without-channel14.py'
    assert derive_review['beforeSha256']==manifest['files'][derive_review['path']]==sha(CHECKPOINT/derive_review['path'])
    assert derive_review['afterSha256']=='552278e86c4c0070383cce0091b1bc75e73a75dc42f37e7c00348989d4e46847'==sha(ROOT/derive_review['path'])
    assert derive_review['nullStatisticToleranceWeightsCohortBHAndSignFlipsUnchanged']
    for relative,digest in derive_review['proofHashes'].items():
        assert sha(ROOT/relative)==digest
    for relative,digest in derive_review['preservedFrozenFiles'].items():
        assert sha(ROOT/relative)==sha(CHECKPOINT/relative)==digest
    repair_input_hashes[derive_review_path.relative_to(ROOT).as_posix()]=sha(derive_review_path)
    reviewed_source_code_exceptions={derive_review['path']:derive_review['afterSha256']}
    sys.path.insert(0,str(ROOT/'scripts'))
    from exact_scalar_marginals_2026_10_20 import score_blocks, individual_pvalues
    for new_exact in [backend,wrapper]:
        repair_input_hashes[new_exact.relative_to(ROOT).as_posix()] = sha(new_exact)
    for stage in ['bloc','party','independent-bloc','independent-party']:
        lineage_path = SOURCE_ROOT/'numeric-lineage'/(stage+'-enumeration-lineage.json')
        lineage = read(lineage_path)
        assert lineage['status']=='PASS' and lineage['asOf']==DAY and lineage['stage']==stage
        assert lineage['wrapperSha256']==sha(wrapper) and lineage['scalarBackendSha256']==sha(backend)
        assert lineage['nullUnchanged'] and lineage['outcomeMarginalExactness'] and not lineage['monteCarlo']
        assert lineage['inputHistorySha256']==sha(ROOT/'data/poll-history.json')
        assert lineage['outputSha256']==sha(STRICT/lineage['outputFile'])
        repair_input_hashes[lineage_path.relative_to(ROOT).as_posix()] = sha(lineage_path)
    for relative, expected in manifest["reviewedExactHelpers"].items():
        assert sha(ROOT / relative) == expected == sha(CHECKPOINT / relative)
        repair_input_hashes[relative] = expected
    preserved_code_hashes = {}
    for family in ["authorContentHashes", "protectedRuntimeHashes", "frozenConditionalAndArtisticHashes"]:
        for relative, expected in manifest[family].items():
            assert sha(ROOT / relative) == expected, ("authored content/protected runtime changed", relative)
            preserved_code_hashes[relative] = expected
    for relative, expected in manifest["files"].items():
        if relative.endswith((".py", ".mjs", ".jsx", ".js", ".css")) and relative != "dashboard/snapshot.mjs":
            reviewed_expected = reviewed_source_code_exceptions.get(relative,expected)
            assert sha(ROOT / relative) == reviewed_expected, ("prior source code changed", relative)
            preserved_code_hashes[relative] = reviewed_expected
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
    assert len(old_history) == manifest["historyPollCount"] == 128
    assert len(new_history) == len(old_history) + len(plan_specs) == 132
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
    eligible_new_ids = set()
    for pollster_id, spec in EXPECTED.items():
        candidate_path = ROOT / plan_specs[pollster_id]["candidatePath"]
        source_dir = candidate_path.parent
        candidate = read(candidate_path)
        candidates[pollster_id] = candidate
        candidate_hashes[candidate_path.relative_to(ROOT).as_posix()] = sha(candidate_path)
        assert candidate["id"] == spec["id"]
        assert candidate["date"] == spec["date"]
        assert sha(candidate_path) == plan_specs[pollster_id]["candidateSha256"]
        assert candidate["seats"] == plan_specs[pollster_id]["expectedSeats"]
        assert candidate["reportedPercentages"] == plan_specs[pollster_id]["expectedReportedPercentages"]
        verified = bool(candidate.get("fieldworkVerified"))
        assert verified == (spec["fieldworkEnd"] is not None)
        if verified:
            eligible_new_ids.add(f"history_{spec['id']}_current")
            assert candidate["sourceTier"] == "original-publisher"
        doc = candidate["sourceDocument"]
        if verified:
            assert doc["primaryPublicationVerified"] and doc["publicationCrossChecked"]
        for filename_key, hash_key in [("fileName", "sha256"), ("extractFileName", "extractSha256"),
                                       ("originalGraphicFileName", "originalGraphicSha256"),
                                       ("historyFileName", "historySha256")]:
            if doc.get(filename_key):
                source_path = source_dir / doc[filename_key]
                assert source_path.is_file() and sha(source_path) == doc[hash_key], ("source evidence hash mismatch", source_path)
                source_hashes[source_path.relative_to(ROOT).as_posix()] = sha(source_path)
        for graphic in doc.get("originalGraphicFiles", []) + doc.get("reviewedGraphics", []):
            source_path = source_dir / graphic.get("file", graphic.get("fileName"))
            assert source_path.is_file() and sha(source_path) == graphic["sha256"]
            source_hashes[source_path.relative_to(ROOT).as_posix()] = sha(source_path)
        active = new_current[spec["id"]]
        archived = new_history[f"history_{spec['id']}_current"]
        for row in [active, archived]:
            assert row["sourceTier"] == candidate["sourceTier"]
            assert row["date"] == spec["date"] and row["pollsterId"] == pollster_id
            assert row.get("fieldworkStart") == spec["fieldworkStart"] and row.get("fieldworkEnd") == spec["fieldworkEnd"]
            assert row.get("fieldworkStartTime") is None and row.get("fieldworkEndTime") is None
            assert row["sampleSize"] == spec["sampleSize"] == candidate["sampleSize"]
            assert {key: value for key, value in row["seats"].items() if value > 0} == spec["seats"]
            assert row["reportedPercentages"] == spec["reportedPercentages"] == candidate["reportedPercentages"]
            assert "israel_first" not in row["reportedPercentages"] and "other" not in row["reportedPercentages"]
            for party_id in spec["seats"]:
                assert party_id not in row["reportedPercentages"], ("unpublished passing-party vote share", party_id)
            for key in ["sourceUrl", "publishedAt", "updatedAt", "samplingMethod", "initialSampleSize",
                        "invitedSampleSize", "reportedMarginOfErrorPct", "reportedMarginOfErrorConfidencePct",
                        "sourceBlocSeats", "sourceBlocDefinitions", "panelProvider", "publishedBounds",
                        "unmodelledNamedParties", "sampleSizeQualifier", "sampleSizeLowerBoundExclusive",
                        "requestedParticipationCount", "requestedParticipationSourceLabel",
                        "fixedBlocSeatsForAudit", "fixedBlocDefinitionForAudit",
                        "sourceHistoryBlocSeats", "sourceHistoryBlocDefinitions"]:
                assert row.get(key) == candidate.get(key), ("candidate metadata differs", pollster_id, key)
            assert row.get("percentageDenominator") == candidate.get("percentageDenominator")
            assert row.get("undecidedPct") == candidate.get("undecidedPct")
            assert row.get("undecidedDenominatorVerified") == candidate.get("undecidedDenominatorVerified")
            assert row["requiresReconstruction"], "model vote-share reconstruction mislabeled as published"
        assert archived["sourcePollId"] == active["id"]
        for key in set(active) | set(archived):
            if key not in {"id", "recordStatus", "sourcePollId", "archiveSourceUrl"}:
                assert active.get(key) == archived.get(key), ("current/history mismatch", key)
    assert len(eligible_new_ids) == 3
    for pollster_id, spec in EXPECTED.items():
        row = new_current[spec["id"]]
        assert sum(row["sourceBlocSeats"].values()) == 120
        assert row["sourceBlocSeats"] == plan_specs[pollster_id]["expectedSourceBlocSeats"]
        assert row["requiresReconstruction"] is True
        assert row.get("modelOnlyPercentageIds",[]) == candidates[pollster_id].get("modelOnlyPercentageIds",[])
    # Keep every earlier provenance decision and published bound; no inheritance.
    kan_new = new_current['kantar_2026-10-18']
    assert kan_new == old_current[kan_new['id']] and kan_new['sampleSize'] == 547
    assert not kan_new['fieldworkVerified'] and kan_new['fieldworkStart'] is None
    old_kan = new_history['history_kantar_2026-10-11_current']
    assert old_kan['fieldworkStart'] is None and old_kan['fieldworkEnd'] is None
    assert new_history['history_kantar_2026-10-15_current']['sourceTier'] == 'original-publisher'
    prior_i24 = new_history['history_direct_polls_2026-10-13_current']
    assert len(prior_i24['publishedBounds']) == 4
    i24 = new_current['direct_polls_2026-10-18']
    assert i24 == old_current[i24['id']]
    assert i24['reportedMarginOfErrorPct'] == 4.2 and i24['reportedMarginOfErrorConfidencePct'] == 95
    assert set(i24.get('publishedBounds', {})).isdisjoint(i24['reportedPercentages'])
    c16 = new_current['maagar_mochot_2026-10-13']
    assert c16 == old_current[c16['id']] and c16['sampleSize'] is None
    assert c16['sampleSizeLowerBoundExclusive'] == 2000 and c16['fieldworkStart'] is None and c16['fieldworkEnd'] is None
    prior_c13 = new_history['history_hamadad_consortium_2026-10-07_current']
    assert prior_c13['sampleSize'] == 1263 and prior_c13['fieldworkStart'] == '2026-10-06' and prior_c13['fieldworkEnd'] == '2026-10-07'
    c13 = new_current[EXPECTED['hamadad_consortium']['id']]
    assert c13['seats']['likud'] == 18 and c13['seats']['utj'] == 7
    assert c13['sourceDiscrepancies'][0]['articleProse'] == 17
    assert c13['reportedPercentages'] == {'haredi_public':1.0} and 'gantz' not in c13['reportedPercentages']
    assert c13['fieldworkStart'] is None and c13['fieldworkEnd'] is None
    assert c13['percentageSourceUrls']['haredi_public'].startswith('https://x.com/IsraelPolls/status/')
    c14 = new_current[EXPECTED['next_data']['id']]
    assert 'gantz' not in c14['seats'] and 'gantz' not in c14['reportedPercentages']
    assert c14['modelOnlyPercentageIds'] == ['other'] and c14['percentages']['other'] == .5
    n12 = new_current[EXPECTED['midgam_geva']['id']]
    assert (n12['initialSampleSize'],n12['sampleSize'],n12['invitedSampleSize']) == (500,507,2502)
    walla = new_current[EXPECTED['lazar']['id']]
    assert walla['date'] == '2026-10-20' and walla['fieldworkEnd'] == '2026-10-19'
    assert walla['panelProvider'] == 'Panel4All' and walla['reportedPercentages'] == {'winter':2.9}

    assert bloc["cohort"] == party["cohort"]
    old_cohort, new_cohort = index(before_bloc["cohort"], "pollId"), index(bloc["cohort"], "pollId")
    assert len(old_cohort) == len(before_bloc["cohort"])
    assert len(new_cohort) == len(old_cohort) + len(plan_specs)
    assert set(new_cohort) - set(old_cohort) == new_history_ids
    assert not set(old_cohort) - set(new_cohort)
    for poll_id, old in old_cohort.items():
        assert new_cohort[poll_id] == old, ("prior cohort record changed", poll_id)
    for pollster_id, spec in EXPECTED.items():
        row = new_cohort[f"history_{spec['id']}_current"]
        assert row["eligibleStrict"] == (spec["fieldworkEnd"] is not None)
        assert row["publicationDate"] == spec["date"] and row["fieldworkStart"] == spec["fieldworkStart"] and row["fieldworkEnd"] == spec["fieldworkEnd"]
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
        if row["eligibleStrict"]:
            doc = candidates[pollster_id]["sourceDocument"]
            expected_evidence = plan_specs[pollster_id]["fieldworkEvidence"]
            assert expected_evidence, "new strict observation lacks reviewed original date evidence"
            for evidence in expected_evidence:
                assert evidence["sha256"] in found
                matching = [entry for entry in row.get("evidence", []) if entry.get("sha256") == evidence["sha256"]]
                assert matching and any(entry.get("quote") == evidence["quote"] for entry in matching)
                path = ROOT / evidence["file"]
                assert sha(path) == evidence["sha256"]
                # Public proof may paraphrase the date while an explicit, separately
                # hashed original reader receipt preserves the exact source wording.
                # Without that reviewed pointer, the quote must remain in the proof.
                original_receipt = evidence.get("quoteVerifiedInLocalOriginalReceipt")
                quote_path = path
                if original_receipt is not None:
                    assert set(original_receipt) == {"file", "sha256"}
                    quote_path = (ROOT / original_receipt["file"]).resolve()
                    assert quote_path.is_relative_to(ROOT.resolve()) and quote_path.is_file()
                    assert sha(quote_path) == original_receipt["sha256"]
                    source_hashes[quote_path.relative_to(ROOT).as_posix()] = original_receipt["sha256"]
                assert evidence["quote"] in quote_path.read_text(encoding="utf-8-sig")
                assert evidence["sourceUrl"] == candidates[pollster_id].get("fieldworkSourceUrl", candidates[pollster_id]["sourceUrl"])
    eligible = [row for row in new_cohort.values() if row["eligibleStrict"]]
    excluded = [row for row in new_cohort.values() if not row["eligibleStrict"]]
    assert {key for key, row in new_cohort.items() if row["eligibleStrict"]} == {
        key for key, row in old_cohort.items() if row["eligibleStrict"]} | eligible_new_ids
    for row in eligible:
        assert bloc["closure"]["firstEligibleFieldworkDate"] <= row["fieldworkStart"] <= row["fieldworkEnd"] <= row["publicationDate"]
    assert len(excluded) == len([row for row in old_cohort.values() if not row["eligibleStrict"]]) + len(new_history_ids - eligible_new_ids)
    assert all(row.get("fieldworkStart") is None or row.get("fieldworkEnd") is None for row in excluded)
    kan = new_cohort["history_kantar_2026-10-11_current"]
    assert not kan["eligibleStrict"] and kan["fieldworkStart"] is None and kan["fieldworkEnd"] is None

    coverage = snapshot["coverage"]
    n_series = len(bloc["primary"]["byPollster"])
    n_parties = len(party["testedPartyIds"])
    n_groups = len(bloc["primary"]["overall"])
    n_polls = len(eligible)
    n_deltas = sum(len(series["pollIds"])-1 for series in bloc["primary"]["byPollster"])
    old_eligible = [row for row in old_cohort.values() if row["eligibleStrict"]]
    assert n_polls == len(old_eligible) + len(eligible_new_ids)
    assert n_series == len(before_bloc["primary"]["byPollster"])
    assert n_deltas == before_bloc["primary"]["nDeltas"] + len(eligible_new_ids)
    assert n_parties == before_snapshot["coverage"]["partyCount"]
    assert coverage["pollCount"] == n_polls and coverage["seriesCount"] == n_series
    assert coverage["deltaCount"] == n_deltas and coverage["partyCount"] == n_parties and coverage["excludedPollCount"] == len(excluded)
    assert n_groups == 3 and n_deltas == n_polls - n_series
    for key, value in before_snapshot["coverage"].items():
        if key in {"pollCount", "deltaCount"}:
            expected_value = value + len(eligible_new_ids)
        elif key == "excludedPollCount":
            expected_value = value + len(new_history_ids - eligible_new_ids)
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
        assert row["nPolls"] == before_weights[row["pollsterId"]]["nPolls"] + (1 if row["pollsterId"] in {new_cohort[key]["pollsterId"] for key in eligible_new_ids} else 0)
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
    assert exact > 2**63-1, "Exact universe must remain arbitrary-precision counted"
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
                        # Independently use labeled-choice DP instead of materializing n! orders.
                        # The observed OLS slope above is still recomputed from raw canonical rows.
                        blocks = score_blocks(relative_days, expected_seats, method='dp')
                        expected_p = float(individual_pvalues(blocks, [slope], tolerance=1e-12)[0])
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
    assert all(sha(ROOT / relative) == value for relative,value in repair_input_hashes.items()), "reviewed exact arithmetic repair changed during validation"
    assert all(sha(ROOT / relative) == value for relative,value in candidate_hashes.items()), "reviewed candidates changed"
    assert all(sha(ROOT / relative) == value for relative,value in source_hashes.items()), "source evidence changed"
    assert all(sha(CHECKPOINT / relative) == value for relative,value in checkpoint_hashes.items()), "immutable checkpoint changed"
    assert all(sha(ROOT / relative) == value for relative,value in preserved_code_hashes.items()), "preserved code changed"
    assert all(sha(ROOT / relative) == value for relative,value in frozen_evidence_hashes.items()), "prior frozen evidence changed during validation"

    report = {
        "passed":True,"status":"PASS","asOf":DAY,"runId":"reviewed","newPollCount":len(EXPECTED),
        "activePolls":len(new_current),"historyPolls":len(new_history),"candidatePolls":len(new_cohort),
        "polls":n_polls,"series":n_series,"deltas":n_deltas,"parties":n_parties,
        "individualTests":n_parties*n_series,"individualBlocTests":n_groups*n_series,
        "exactPermutations":str(exact),"excludedPollCount":len(excluded),
        "removedActivePollIds":sorted(old_ids),"addedActivePollIds":sorted(new_ids),"addedHistoryPollIds":sorted(new_history_ids),
        "newPollsIncludedInForecast":True,"newPollsIncludedInStrictTrends":len(eligible_new_ids)==len(new_history_ids),
        "newStrictEligiblePollIds":sorted(eligible_new_ids),"newStrictExcludedPollIds":sorted(new_history_ids-eligible_new_ids),
        "newStrictEligiblePollCount":len(eligible_new_ids),"c16Oct13FieldworkStillUnknown":True,
        "c16ExactSampleSizeStillUnknown":True,"i24CensoredPercentagesPreservedAsBounds":True,
        "priorUnknownFieldworkCohortUnchanged":True,"kanOct11FieldworkStillUnknown":True,
        "kanOct18FieldworkStillUnknown":True, "c14AndI24Oct18VerifiedStrictEligible":True,
        "c13Oct19FieldworkStillUnknown":True,"n12C14AndLazarOct19VerifiedStrictEligible":True,
        "c13PrimaryGraphicProseConflictPreserved":True,"secondaryPercentageProvenancePreserved":True,
        "memorySafeExactEnumerationWithIndependentDP":True,
        "allPriorHistoricalObservationsPreserved":True,"allOtherActiveObservationsPreserved":True,
        "priorHistoryMetadataExceptions":[{"pollId":key,"recordStatus":"superseded-reviewed-record","replacedByPollId":value,"allOtherFieldsUnchanged":True} for key,value in sorted(lifecycle.items())],
        "historicalWeightsAndCatalogueUnchanged":True,"allPriorStrictCohortRowsUnchanged":True,
        "preservedAuthoredAndProtectedCode":True,"thresholdStylesheetSha256":sha(ROOT/threshold_path),
        "allPriorFrozenEvidencePreserved":True,"priorFrozenEvidenceCount":len(frozen_evidence_hashes),
        "preservedAuthorContentCount":len(manifest["authorContentHashes"]),
        "preservedProtectedRuntimeCount":len(manifest["protectedRuntimeHashes"]),
        "preservedConditionalAndArtisticCount":len(manifest["frozenConditionalAndArtisticHashes"]),
        "snapshotIndividualRowsAndCohortMatchAudit":True,
        "independentAgreement":"Primary fieldwork-axis exact bloc/party tails and individual tests agree with fresh independent audits; both axes independently recompute raw-input OLS, weighted changes, BH, sign flips and exact-count p linkage; publication-axis individual p values independently recomputed using exact labeled-choice DP with Python-integer tail masses. Agreement within 1e-12.",
        "bhFamilySizes":{"parties":n_parties,"blocs":n_groups,"individualParties":n_parties*n_series,"individualBlocs":n_groups*n_series},
        "correctedPartyFindings":[row["partyId"] for row in party["primary"]["overall"] if row["qValue"]<.05],
        "correctedBlocFindings":[row["group"] for row in bloc["primary"]["overall"] if row["qValue"]<.05],
        "correctedPartySensitivityFindings":[row["partyId"] for row in party["primary"]["overall"] if row["wholeSeriesSignFlipQ"]<.05],
        "correctedBlocSensitivityFindings":[row["group"] for row in bloc["primary"]["overall"] if row["wholeInstituteSignFlipQ"]<.05],
        "newSourceBlocsReconciledWithoutDoubleCounting":True,"passingPartyPercentagesRemainUnpublished":True,
        "sourceEvidenceSha256Verified":True,"sourceEvidenceHashes":source_hashes,"candidateHashes":candidate_hashes,
        "inputHashes":input_hashes,"checkpointHashes":checkpoint_hashes,"preservedCodeHashes":preserved_code_hashes,
        "reviewedExactHelpersUnchanged":True,"exactArithmeticRepairInputHashes":repair_input_hashes,
        "priorSourceTierNormalizationPreserved":True,
        "priorSourceCodePreservedWithoutExceptions":False,
        "priorSourceCodePreservedExceptReviewedEnumerationUpgrade":True,
        "reviewedSourceCodeExceptions":reviewed_source_code_exceptions,
        "validatorSha256":sha(Path(__file__)),"checkpoint":CHECKPOINT.relative_to(ROOT).as_posix(),
    }
    immutable_write(RECEIPT,report)
    (STRICT/"party-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:report[key] for key in ["status","asOf","newPollCount","polls","series","deltas","parties","exactPermutations","correctedPartyFindings","correctedBlocFindings"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
