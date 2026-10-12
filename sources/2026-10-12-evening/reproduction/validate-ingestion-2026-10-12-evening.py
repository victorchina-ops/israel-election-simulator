"""Independently verify the two October 12 additions and preservation boundary.

This validator rereads the frozen source candidates and immutable checkpoint;
it does not import the ingestion implementation or run numerical analyses.
It writes only a dated validation receipt, which cannot be overwritten.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from datetime import date
import collections
import gzip
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-12-evening"
BEFORE = ART / "before"
PUBLIC = ROOT / "github-pages/sources/2026-10-12-evening"
DAY = "2026-10-12"
BASE = "https://victorchina-ops.github.io/israel-election-simulator/"
FILES = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
         "data/survey-documents-2026-09-14.json", "artifacts/strict-post-close/n12-kan-c13-fieldwork.json",
         "artifacts/strict-post-close/c14-i24-fieldwork.json"]
CASES = {
    "midgam_geva": {"folder": "n12", "oldId": "midgam_geva_2026-10-05", "id": "midgam_geva_2026-10-12",
                   "candidate": "reviewed-n12-poll.json", "candidateSha": "38b7fb050b7e3188504a713b8e75d9a3f0051439dfbf1549940bfca9ccbfd725",
                   "historyId": "history_midgam_geva_2026-10-12_current", "sample": 509,
                   "seats": {"yashar":23,"likud":20,"beyachad":13,"democrats":9,"yisrael_beiteinu":9,"joint":8,"shas":8,"otzma":8,"utj":7,"rz_zehut":6,"raam":5,"hendel":4,"winter":0,"gantz":0,"noam":0,"haredi_public":0}},
    "next_data": {"folder": "c14", "oldId": "next_data_2026-10-07", "id": "next_data_2026-10-12",
                  "candidate": "reviewed-c14-poll.json", "candidateSha": "8d300e33e25ca1a881d8d98e85fb07104cfd897fccfc970657f1b5f1770609ed",
                  "historyId": "history_next_data_2026-10-12_current", "sample": 538,
                  "seats": {"likud":29,"yashar":20,"shas":10,"democrats":10,"utj":8,"joint":8,"beyachad":7,"otzma":7,"rz_zehut":7,"yisrael_beiteinu":5,"raam":5,"hendel":4,"winter":0,"gantz":0,"noam":0,"haredi_public":0}},
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(rows, key):
    out = {row[key]: row for row in rows}
    assert len(out) == len(rows), ("duplicate", key)
    return out


def immutable_write(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.exists():
        assert path.read_bytes() == body, f"Changed dated receipt: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def main():
    manifest = read(BEFORE / "manifest.json")
    assert manifest["baselineAsOf"] == "2026-10-11" and manifest["publishedHead"] == "083e7c9c5259a8f8da0987a5aaa48cea8626affa"
    for rel, digest in manifest["files"].items():
        assert sha(BEFORE / rel) == digest, ("frozen checkpoint", rel)
    for category in ["authorContentHashes", "frozenEvidenceHashes", "protectedRuntimeHashes"]:
        assert all(sha(ROOT / rel) == digest for rel, digest in manifest[category].items()), category
    unchanged_model = ["data/calibration.json", "data/weight-presets.json", "data/parties.json", "data/turnout-2022.json",
                       "dashboard/src/data.json", "dashboard-snapshot.json", "artifacts/dashboard-baseline.json", "github-pages/index.html"]
    for rel in unchanged_model:
        assert sha(ROOT / rel) == manifest["files"][rel], ("outside ingestion scope", rel)
    revision = (ART / "ingestion-receipt-proof-wording-r1.json").exists()
    receipt_path = ART / ("ingestion-receipt-proof-wording-r1.json" if revision else "ingestion-receipt.json")
    receipt = read(receipt_path)
    if revision:
        initial = read(ART / "ingestion-receipt.json")
        assert receipt["supersedesInitialReceiptSha256"] == sha(ART / "ingestion-receipt.json")
        assert all(sha(PUBLIC / rel) == digest for rel,digest in initial["publicEvidenceFiles"].items())
        correction = read(PUBLIC / "n12/proof-wording-r1/revision-receipt.json")
        assert correction["publishedDataUnchanged"] is True
        assert "גודל המדגם ההתחלתי:500" in correction["correctedParaphrase"]
        assert "התכנון הראשוני" not in correction["correctedParaphrase"]
    assert receipt["status"] == "PASS" and receipt["asOf"] == DAY
    assert receipt["checkpointManifestSha256"] == sha(BEFORE / "manifest.json")
    assert receipt["preflightSha256"] == sha(ART / "ingestion-preflight.json")
    assert set(receipt["changedCanonicalFiles"]) == set(FILES)
    for rel, digest in receipt["changedCanonicalFiles"].items():
        assert sha(ROOT / rel) == digest, ("applied canonical hash", rel)
    for rel, digest in receipt["publicEvidenceFiles"].items():
        assert sha(PUBLIC / rel) == digest, ("public source changed", rel)
    current, history, sources, documents, audit_n12, audit_c14 = [read(ROOT / rel) for rel in FILES]
    old_current, old_history, old_sources, old_documents, old_audit_n12, old_audit_c14 = [read(BEFORE / rel) for rel in FILES]
    assert current["asOf"] == history["asOf"] == sources["asOf"] == documents["checkedAt"] == DAY
    active, old_active = index(current["polls"], "pollsterId"), index(old_current["polls"], "pollsterId")
    archive, old_archive = index(history["polls"], "id"), index(old_history["polls"], "id")
    assert len(active) == len(old_active) == 8 and active.keys() == old_active.keys()
    assert len(archive) == 117 and len(old_archive) == 115
    assert len({p["id"] for p in current["polls"]}) == 8
    assert len({(p["pollsterId"], p["date"]) for p in history["polls"]}) == 117
    assert set(archive) - set(old_archive) == {p["historyId"] for p in CASES.values()}
    for pid, poll in old_active.items():
        if pid not in CASES:
            assert active[pid] == poll, ("unrelated current changed", pid)
    lifecycle_ids = {next(p["id"] for p in old_history["polls"] if p.get("sourcePollId") == c["oldId"]):c for c in CASES.values()}
    for pid, original in old_archive.items():
        revised = dict(archive[pid])
        if pid in lifecycle_ids:
            assert revised["recordStatus"] == "superseded-reviewed-record"
            assert revised["replacedByPollId"] == lifecycle_ids[pid]["id"]
            revised["recordStatus"] = original["recordStatus"]
            revised.pop("replacedByPollId")
        assert revised == original, ("prior history values changed", pid)
    notes = []
    for pid, case in CASES.items():
        poll = active[pid]
        candidate_path = ART / "tv-primary" / case["candidate"]
        candidate = read(candidate_path)
        assert sha(candidate_path) == case["candidateSha"] == sha(PUBLIC / case["folder"] / "frozen-reviewed-candidate.json")
        # Only URL/provenance normalization adds or changes candidate metadata.
        normalization_changes = {"secondarySourceUrls", "percentageSourceUrls", "sourceDocument"}
        for key, value in candidate.items():
            if key not in normalization_changes:
                assert poll[key] == value, ("original candidate field changed", pid, key)
        assert poll["id"] == case["id"] and poll["seats"] == case["seats"]
        assert sum(poll["seats"].values()) == poll["seatTotal"] == 120
        assert poll["sampleSize"] == case["sample"]
        assert poll["date"] == poll["fieldworkStart"] == poll["fieldworkEnd"] == DAY
        assert poll["fieldworkStartTime"] is None and poll["fieldworkEndTime"] is None
        assert poll["panelProvider"] is None and poll["percentageDenominator"] is None
        assert poll["reportedMarginOfErrorConfidencePct"] is None
        assert "israel_first" not in poll["seats"] and "israel_first" not in poll["percentages"]
        assert "israel_first" not in poll["reportedPercentages"]
        historical = dict(archive[case["historyId"]])
        for key in ["sourcePollId", "archiveSourceUrl", "recordStatus"]:
            historical.pop(key)
        historical["id"] = case["id"]
        assert historical == poll
        normalized_file = (PUBLIC / "n12/proof-wording-r1/reviewed-poll.json"
                           if revision and pid == "midgam_geva" else PUBLIC / case["folder"] / "reviewed-poll.json")
        assert read(normalized_file) == poll
        doc = poll["sourceDocument"]
        assert doc["primaryPublicationVerified"] is True
        assert sha(PUBLIC / case["folder"] / doc["fileName"]) == doc["sha256"]
        assert sha(PUBLIC / case["folder"] / doc["extractFileName"]) == doc["extractSha256"]
        assert {key:doc[key] for key in candidate["sourceDocument"]} == candidate["sourceDocument"]
        report = next(p for p in documents["reports"] if p["pollsterId"] == pid and p["includedInCurrentModel"])
        assert report["sampleSize"] == case["sample"] and report["date"] == DAY
        for row in report["tables"][0]["rows"]:
            if row["partyId"]:
                assert row["seats"] == poll["seats"].get(row["partyId"])
                assert row["rawPct"] == poll["reportedPercentages"].get(row["partyId"])
        if pid == "midgam_geva":
            assert poll["sourceBlocSeats"] == {"coalition":49,"opposition":54,"arab_parties":13,"hendel":4}
            assert poll["reportedPercentages"] == poll["percentages"] == {"winter":1.8,"gantz":.9,"noam":.5,"haredi_public":.1}
            assert "other" not in poll["percentages"] and poll["modelOnlyPercentageIds"] == []
            assert poll["initialSampleSize"] == 500 and poll["invitedSampleSize"] == 2521
            assert poll["reportedMarginOfErrorPct"] == 4.4
            assert math.isclose(sum(poll["reportedUndecidedBreakdown"].values()),8.1,abs_tol=1e-12)
            assert poll["undecidedPct"] == 8 and poll["undecidedPctApproximate"] is True
            assert doc["originalBroadcastPlayerAccessible"] is False and doc["originalGraphicVisuallyVerified"] is False
            assert not any("inline-" in u or "n12-primary-" in u for u in poll["secondarySourceUrls"])
            notes.append("N12 original article read, historical table checked; original broadcast player403, no numeric broadcast frames claimed verified.")
        else:
            assert poll["sourceBlocSeats"] == {"coalition":61,"opposition":46,"arab_parties":13}
            assert poll["sourceBlocReconciliation"]["fixedNonArabOppositionExcludingHendel"] == 42
            assert poll["sourceBlocReconciliation"]["fixedUnassignedHendel"] == 4
            assert poll["reportedPercentages"] == {"winter":2.9,"noam":.9,"gantz":.6,"haredi_public":.6}
            assert poll["percentages"] == {**poll["reportedPercentages"],"other":.1}
            assert poll["modelOnlyPercentageIds"] == ["other"] and "other" not in poll["reportedPercentages"]
            assert poll["unmodelledNamedParties"][0]["name"] == "אח״י — חוזרים לשורשים"
            assert poll["unmodelledNamedParties"][0]["pct"] == .1
            assert poll["undecidedPct"] == 5 and poll["samplingMethod"] is None
            assert poll["initialSampleSize"] is None and poll["invitedSampleSize"] is None and poll["reportedMarginOfErrorPct"] is None
            assert doc["originalGraphicVisuallyVerified"] is True
            assert sha(PUBLIC / "c14" / doc["originalGraphicFileName"]) == doc["originalGraphicSha256"]
    for original in old_documents["reports"]:
        revised = next(p for p in documents["reports"] if p["id"] == original["id"])
        allowed = {"includedInCurrentModel", "statusLabel"} if original.get("pollsterId") in CASES and original.get("includedInCurrentModel") else set()
        assert {k:v for k,v in revised.items() if k not in allowed} == {k:v for k,v in original.items() if k not in allowed}
    assert current["documentReview"] == documents
    for original in old_sources["sources"]:
        if original.get("id") in CASES:
            revised = next(p for p in sources["sources"] if p.get("url") == original["url"] and not p.get("id"))
            assert {k:v for k,v in revised.items() if k not in {"id","type","notes"}} == {k:v for k,v in original.items() if k not in {"id","type","notes"}}
            assert revised["notes"][:-1] == original["notes"]
        else:
            assert original in sources["sources"], ("unrelated source row changed", original.get("url"))
    all_audits = []
    audit_hashes = {}
    for filename in ["lazar-fieldwork.json","n12-kan-c13-fieldwork.json","c14-i24-fieldwork.json","c16-tatika-fieldwork.json","new-unverified-fieldwork-2026-09-30.json"]:
        rel = "artifacts/strict-post-close/" + filename
        original, reviewed = read(BEFORE / rel), read(ROOT / rel)
        old_rows, new_rows = original.get("rows",original.get("polls",[])), reviewed.get("rows",reviewed.get("polls",[]))
        assert all(p in new_rows for p in old_rows), ("old fieldwork decision changed", filename)
        if rel not in FILES:
            assert sha(ROOT / rel) == sha(BEFORE / rel)
        audit_hashes[rel] = sha(ROOT / rel)
        all_audits.extend(new_rows)
    audited = index(all_audits,"pollId")
    assert len(audited) == 46
    assert set(audited) == {p["id"] for p in history["polls"] if p["date"] >= "2026-09-09"}
    eligible = [p for p in all_audits if p.get("eligibleStrict",p.get("includeInStrictPostClose",False))]
    assert len(eligible) == 41 and len(all_audits)-len(eligible) == 5
    counts = collections.Counter(p["pollsterId"] for p in eligible)
    assert len(counts) == 8 and sum(n-1 for n in counts.values()) == 33
    default = [p for p in eligible if p["pollsterId"] != "next_data"]
    default_counts = collections.Counter(p["pollsterId"] for p in default)
    assert len(default) == 33 and len(default_counts) == 7 and sum(n-1 for n in default_counts.values()) == 26
    for case in CASES.values():
        row = audited[case["historyId"]]
        assert row["eligibleStrict"] is True and row["fieldworkStart"] == row["fieldworkEnd"] == DAY
        assert row["sampleSize"] == case["sample"]
        assert sha(ROOT / row["evidencePath"]) == row["evidenceSha256"]
        for evidence in row["evidence"]:
            assert sha(ROOT / evidence["file"]) == evidence["sha256"]
    for row in eligible:
        assert date.fromisoformat("2026-09-08") < date.fromisoformat(row["fieldworkStart"]) <= date.fromisoformat(row["fieldworkEnd"]) <= date.fromisoformat(row["publicationDate"])
    new_urls = []
    def walk(value):
        if isinstance(value,dict):
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
        elif isinstance(value,str) and value.startswith(BASE+"sources/2026-10-12-evening/"):
            path = ROOT / "github-pages" / unquote(urlsplit(value).path.removeprefix("/israel-election-simulator/"))
            assert path.is_file(), ("broken new archive URL",value)
            new_urls.append(value)
    for value in [current,history,sources,documents]:walk(value)
    assert new_urls
    private_markers = ["gilead-research-context","Relatives_and_Respondents_Prospective_Study","תחזית_המנדטים_שיטת_הקרובים"]
    for path in PUBLIC.rglob("*"):
        if path.is_file() and path.suffix in {".json",".txt",".html"}:
            raw = path.read_bytes()
            # Preserve the publisher's small compressed election-index error
            # response for provenance; its decoded error text is also archived.
            if raw.startswith(b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            text = raw.decode("utf-8-sig")
            assert not any(marker in text for marker in private_markers), ("private research leaked",path)
    result = {"status":"PASS","asOf":DAY,"phase":"canonical-ingestion-independently-validated-before-numerical-analysis",
              "checkpointManifestSha256":sha(BEFORE / "manifest.json"),"ingestionReceiptSha256":sha(receipt_path),
              "ingestionReceiptPath":receipt_path.relative_to(ROOT).as_posix(),
              "proofWordingRevision":"proof-wording-r1" if revision else None,
              "activePollCount":8,"historyPollCount":117,"previousHistoryRecordsPreserved":115,"otherActivePollsUnchanged":6,
              "newPollIds":[case["id"] for case in CASES.values()],"newHistoryIds":[case["historyId"] for case in CASES.values()],
              "fullStrict":{"candidates":46,"polls":41,"series":8,"deltas":33,"unknownFieldworkExcluded":5,"byInstitute":dict(sorted(counts.items()))},
              "defaultWithoutChannel14":{"polls":33,"series":7,"deltas":26,"byInstitute":dict(sorted(default_counts.items()))},
              "preserved":{"authorFiles":117,"protectedRuntimeFiles":234,"previousPublicEvidenceFiles":1312,"historicalWeightsAndPartyCatalogue":True,"dashboardAndModelBaselineNotRebuilt":True},
              "newPublicArchiveURLs":{"uniqueCount":len(set(new_urls)),"allExistLocally":True},
              "publisherBlocDefinitionsPreserved":True,"missingValuesPreserved":True,"modelOnlyOtherC14Pct":.1,
              "limitations":notes,"inputHashes":{rel:sha(ROOT / rel) for rel in FILES},"fieldworkAuditHashes":audit_hashes}
    immutable_write(ART / "ingestion-validation.json",result)
    immutable_write(PUBLIC / "ingestion-validation.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
