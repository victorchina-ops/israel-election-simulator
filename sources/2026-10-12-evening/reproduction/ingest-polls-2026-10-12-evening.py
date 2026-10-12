"""Ingest two reviewed October 12 observations after an immutable preflight.

Only four canonical survey files and their two fieldwork audits change. Original
reports, missing values, publisher bloc definitions and the UI baseline survive.
This importer never runs numerical analyses, assembles the dashboard or publishes.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY, BASELINE = "2026-10-12", "2026-10-11"
ART = ROOT / "artifacts/poll-checks/2026-10-12-evening"
CHECKPOINT = ART / "before"
TV, SOCIAL = ART / "tv-primary", ART / "israelpolls"
PUBLIC = ROOT / "github-pages/sources/2026-10-12-evening"
PUBLIC_BASE = "https://victorchina-ops.github.io/israel-election-simulator/sources/2026-10-12-evening/"
MUTABLE = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
           "data/survey-documents-2026-09-14.json",
           "artifacts/strict-post-close/n12-kan-c13-fieldwork.json",
           "artifacts/strict-post-close/c14-i24-fieldwork.json"]
COMMON_TV = ["network-receipts.json", "graphic-receipts.json", "build_reviewed_candidates.py",
             "verification-summary.json", "remaining-tv-network-receipts.json"]
COMMON_SOCIAL = ["source-summary.json", "initial-receipts.json", "post-receipts.json", "history-receipts.json"]
SPECS = [
    {"folder": "n12", "candidate": "reviewed-n12-poll.json",
     "candidateSha256": "38b7fb050b7e3188504a713b8e75d9a3f0051439dfbf1549940bfca9ccbfd725",
     "id": "midgam_geva_2026-10-12", "pollsterId": "midgam_geva",
     "oldId": "midgam_geva_2026-10-05", "oldDate": "2026-10-05",
     "historyId": "history_midgam_geva_2026-10-12_current", "audit": MUTABLE[4], "auditRows": "rows",
     "seats": {"yashar": 23, "likud": 20, "beyachad": 13, "democrats": 9,
               "yisrael_beiteinu": 9, "utj": 7, "joint": 8, "shas": 8, "otzma": 8,
               "rz_zehut": 6, "raam": 5, "winter": 0, "hendel": 4, "gantz": 0,
               "haredi_public": 0, "noam": 0},
     "reported": {"winter": 1.8, "gantz": .9, "noam": .5, "haredi_public": .1},
     "sample": 509, "blocs": {"coalition": 49, "opposition": 54, "arab_parties": 13, "hendel": 4},
     "tvFiles": ["n12-article.html", "n12-article.txt", "n12-article-links.json",
                 "n12-home.html", "n12-home.txt", "n12-politics.html", "n12-politics.txt",
                 "n12-elections.html", "n12-elections.txt", "n12-broadcast-access-receipts.json"],
     "socialFiles": ["c12-post.html", "c12-post.txt", "c12-post-links.json",
                     "c12-history-post.html", "c12-history-post.txt", "c12-history-post-links.json",
                     "c12-history.png"],
     "fieldworkQuote": "מועד איסוף הנתונים: 12.10.2026; 509 משיבים בפועל; 500 התכנון הראשוני; 2,521 מוזמנים; אינטרנט וטלפון; דגימת שכבות ובתוך השכבות דגימה אקראית.",
     "locator": "n12-article.txt lines108–123, original article methodology"},
    {"folder": "c14", "candidate": "reviewed-c14-poll.json",
     "candidateSha256": "8d300e33e25ca1a881d8d98e85fb07104cfd897fccfc970657f1b5f1770609ed",
     "id": "next_data_2026-10-12", "pollsterId": "next_data",
     "oldId": "next_data_2026-10-07", "oldDate": "2026-10-07",
     "historyId": "history_next_data_2026-10-12_current", "audit": MUTABLE[5], "auditRows": "polls",
     "seats": {"likud": 29, "yashar": 20, "shas": 10, "democrats": 10,
               "utj": 8, "joint": 8, "rz_zehut": 7, "otzma": 7, "beyachad": 7,
               "yisrael_beiteinu": 5, "raam": 5, "hendel": 4, "winter": 0,
               "noam": 0, "gantz": 0, "haredi_public": 0},
     "reported": {"winter": 2.9, "noam": .9, "gantz": .6, "haredi_public": .6},
     "sample": 538, "blocs": {"coalition": 61, "opposition": 46, "arab_parties": 13},
     "tvFiles": ["c14-article.html", "c14-article.txt", "c14-article-links.json",
                 "c14-primary-4.jpeg", "c14-primary-5.jpeg", "c14-home.html", "c14-home.txt",
                 "c14-politics.html", "c14-politics.txt", "c14-elections.html", "c14-elections.txt",
                 "c14-mandates.html", "c14-mandates.txt", "c14-winter.html", "c14-winter.txt",
                 "c14-undecided.html", "c14-undecided.txt"],
     "socialFiles": ["c14-post.html", "c14-post.txt", "c14-post-links.json", "c14-graphic.jpg"],
     "fieldworkQuote": "הסקר בוצע באמצעות חברת NEXT DATA בהשתתפות 538 בוגרים מכלל האוכלוסייה, ונערך היום, 12 באוקטובר 2026. ניתוח הנתונים: שלמה פילבר.",
     "locator": "c14-article.txt line53, original article methodology"},
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def immutable_write(path, value):
    body = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == body, f"Dated evidence differs: {path}"
    else:
        path.write_bytes(body)


def frozen_check():
    manifest = read(CHECKPOINT / "manifest.json")
    assert manifest["baselineAsOf"] == BASELINE and manifest["updateDate"] == DAY
    assert manifest["activePollCount"] == 8 and manifest["historyPollCount"] == 115
    for rel, digest in manifest["files"].items():
        assert sha(CHECKPOINT / rel) == digest, f"Checkpoint changed: {rel}"
    for category in ["authorContentHashes", "frozenEvidenceHashes", "protectedRuntimeHashes"]:
        for rel, digest in manifest[category].items():
            assert sha(ROOT / rel) == digest, f"Preserved author/runtime/evidence changed: {rel}"
    for rel in ["data/calibration.json", "data/weight-presets.json", "data/parties.json", "data/turnout-2022.json"]:
        assert sha(ROOT / rel) == manifest["files"][rel], rel
    return manifest


def source_files(spec):
    files = [(TV / name, name) for name in [*spec["tvFiles"], *COMMON_TV]]
    files += [(SOCIAL / name, name) for name in [*spec["socialFiles"], *COMMON_SOCIAL]]
    files += [(TV / spec["candidate"], "frozen-reviewed-candidate.json")]
    assert len({name for source, name in files}) == len(files)
    return files


def candidate_check(spec):
    path = TV / spec["candidate"]
    assert sha(path) == spec["candidateSha256"], "Reviewed candidate changed"
    proof = TV / "verification-summary.json"
    assert sha(proof) == "531a01a48c449ec379b2a0dae849738a40d7ccb03e354c424159cf17045bee51"
    verification = read(proof)
    assert verification["candidateHashes"][spec["folder"]] == spec["candidateSha256"]
    for item in verification["files"]:
        assert sha(TV / item["sourceFile"]) == item["sha256"], item["sourceFile"]
    poll = read(path)
    assert (poll["id"], poll["pollsterId"], poll["replacesPollId"]) == (spec["id"], spec["pollsterId"], spec["oldId"])
    assert poll["date"] == poll["fieldworkStart"] == poll["fieldworkEnd"] == DAY
    assert poll["fieldworkVerified"] is True
    assert poll["seats"] == spec["seats"] and poll["seatTotal"] == sum(poll["seats"].values()) == 120
    assert poll["sourceBlocSeats"] == spec["blocs"] and sum(spec["blocs"].values()) == 120
    assert poll["reportedPercentages"] == spec["reported"] and poll["sampleSize"] == spec["sample"]
    assert "israel_first" not in poll["seats"] and "israel_first" not in poll["percentages"]
    assert poll["sourceDocument"]["primaryPublicationVerified"] is True
    document = poll["sourceDocument"]
    assert sha(TV / document["fileName"]) == document["sha256"]
    assert sha(TV / document["extractFileName"]) == document["extractSha256"]
    if spec["folder"] == "n12":
        assert poll["percentages"] == spec["reported"] and "other" not in poll["percentages"]
        assert poll["initialSampleSize"] == 500 and poll["invitedSampleSize"] == 2521
        assert poll["reportedMarginOfErrorPct"] == 4.4 and poll["panelProvider"] is None
        assert poll["undecidedPct"] == 8.0 and poll["derivedUndecidedComponentSumPct"] == 8.1
        assert document["originalBroadcastPlayerAccessible"] is False
        assert document["originalGraphicVisuallyVerified"] is False
    else:
        assert poll["percentages"] == {**spec["reported"], "other": .1}
        assert poll["modelOnlyPercentageIds"] == ["other"] and "other" not in poll["reportedPercentages"]
        assert poll["unmodelledNamedParties"][0]["pct"] == .1
        assert poll["undecidedPct"] == 5.0 and poll["samplingMethod"] is None
        assert poll["sourceBlocReconciliation"]["publishedLeftIncludesHendel"] is True
        assert poll["sourceBlocReconciliation"]["fixedNonArabOppositionExcludingHendel"] == 42
        assert document["originalGraphicVisuallyVerified"] is True
        assert sha(TV / document["originalGraphicFileName"]) == document["originalGraphicSha256"]
    assert all(source.is_file() for source, name in source_files(spec))
    return poll, {name: sha(source) for source, name in source_files(spec)}


def normalized(spec, candidate):
    poll = copy.deepcopy(candidate)
    base = PUBLIC_BASE + spec["folder"] + "/"
    poll["secondarySourceUrls"] = list(dict.fromkeys([
        *[u for u in poll["secondarySourceUrls"] if not u.startswith(PUBLIC_BASE)],
        *[base + name for source, name in source_files(spec)],
        base + "reviewed-poll.json", base + "source-extract.txt",
    ]))
    poll["validationSourceUrl"] = base + "reviewed-poll.json"
    poll["fieldworkSourceUrl"] = poll["sourceUrl"]
    poll["sourceDocument"]["archiveUrl"] = base + poll["sourceDocument"]["fileName"]
    poll["sourceDocument"]["extractArchiveUrl"] = base + poll["sourceDocument"]["extractFileName"]
    if poll["sourceDocument"].get("originalGraphicFileName"):
        poll["sourceDocument"]["originalGraphicArchiveUrl"] = base + poll["sourceDocument"]["originalGraphicFileName"]
    social = next(p for p in read(SOCIAL / "source-summary.json")["newDistinctPolls"]
                  if p["pollsterId"] == spec["pollsterId"])
    poll["sourceRepostPublishedAtUtc"] = social["postTimeUtc"]
    poll["sourceRepostPublishedAtIsrael"] = social["postTimeIsrael"]
    if social.get("historyPostTimeUtc"):
        poll["sourceHistoryRepostPublishedAtUtc"] = social["historyPostTimeUtc"]
        poll["sourceHistoryRepostPublishedAtIsrael"] = social["historyPostTimeIsrael"]
    poll["unpublishedPercentagePartyIds"] = [p["id"] for p in read(ROOT / "data/parties.json")
                                            if p["id"] not in poll["reportedPercentages"]]
    if spec["folder"] == "c14":
        poll["percentageSourceUrls"]["other"] = poll["sourceUrl"]
    return poll


def extract_text(spec, poll):
    return (f"Published observation {poll['id']}, publication and explicitly documented fieldwork {DAY}.\n"
            f"Original source: {poll['sourceUrl']}\n"
            f"Original article and methodology successfully read; n{poll['sampleSize']}.\n"
            + "Published mandate vector: " + json.dumps(poll["seats"], ensure_ascii=False) + "\n"
            + "Published national percentages: " + json.dumps(poll["reportedPercentages"], ensure_ascii=False) + "\n"
            + "Publisher bloc definition: " + json.dumps(poll["sourceBlocSeats"], ensure_ascii=False) + "\n"
            + "Named unmodelled lists: " + json.dumps(poll["unmodelledNamedParties"], ensure_ascii=False) + "\n"
            + "Model-only percentage IDs: " + json.dumps(poll["modelOnlyPercentageIds"]) + "\n"
            + "Other missing percentages and israel_first mandate remain absent, never zero-filled.\n"
            + ("N12 original broadcast player unavailable403; article and IsraelPolls history were reviewed, not broadcast frames.\n"
               if spec["folder"] == "n12" else "Original C14 mandate graphic visually verified; published opposition46 includes Hendel4, fixed opposition42 excludes it.\n")
            + "Fieldwork proof: " + spec["fieldworkQuote"] + "\n")


def preflight():
    manifest = frozen_check()
    for rel in MUTABLE:
        assert sha(ROOT / rel) == manifest["files"][rel], f"Canonical baseline changed: {rel}"
    current, history = [read(ROOT / f"data/{name}.json") for name in ["current-polls", "poll-history"]]
    assert current["asOf"] == history["asOf"] == BASELINE
    assert len(current["polls"]) == 8 and len(history["polls"]) == 115
    assert len({p["id"] for p in history["polls"]}) == len({(p["pollsterId"], p["date"]) for p in history["polls"]}) == 115
    source_hashes = {}
    for spec in SPECS:
        candidate, source_hashes[spec["folder"]] = candidate_check(spec)
        assert [p["id"] for p in current["polls"] if p["pollsterId"] == spec["pollsterId"]] == [spec["oldId"]]
        assert sum(p.get("sourcePollId") == spec["oldId"] for p in history["polls"]) == 1
        assert not any(p["pollsterId"] == spec["pollsterId"] and p["date"] == DAY for p in history["polls"])
    assert not PUBLIC.exists(), "Never replace dated public evidence"
    return {"status": "PASS", "phase": "preflight", "asOf": DAY, "baselineAsOf": BASELINE,
            "candidateIds": [spec["id"] for spec in SPECS], "expectedActiveCount": 8,
            "expectedHistoryCount": 117, "expectedStrictCandidateCount": 46,
            "expectedStrictEligibleCount": 41, "expectedStrictWithoutChannel14Count": 33,
            "checkpointManifestSha256": sha(CHECKPOINT / "manifest.json"),
            "inputHashes": {rel: sha(ROOT / rel) for rel in MUTABLE}, "sourceHashes": source_hashes,
            "sourceSummarySha256": sha(SOCIAL / "source-summary.json"),
            "publicRelativePath": PUBLIC.relative_to(ROOT / "github-pages").as_posix()}


def report_for(poll):
    rows = [{"party": p["name"], "partyId": p["id"], "seats": poll["seats"].get(p["id"]),
             "rawPct": poll["reportedPercentages"].get(p["id"])}
            for p in read(ROOT / "data/parties.json") if p.get("ballot") is not False]
    rows += [{"party": p["name"], "partyId": None, "seats": p["seats"], "rawPct": p["pct"]}
             for p in poll["unmodelledNamedParties"]]
    return {"id": poll["pollsterId"] + "-" + DAY, "pollsterId": poll["pollsterId"],
            "fileName": poll["sourceDocument"]["fileName"], "publisher": poll["publisher"],
            "pollster": poll["pollster"], "date": DAY,
            **{key: copy.deepcopy(poll.get(key)) for key in ["dateKind", "fieldworkStart", "fieldworkEnd",
                "fieldworkStartTime", "fieldworkEndTime", "sampleSize", "initialSampleSize", "invitedSampleSize",
                "sampleSizeSourceUrl", "samplingMethod", "population", "panelProvider", "reportedMarginOfErrorPct",
                "reportedMarginOfErrorConfidencePct", "publicationTime", "publishedAt", "undecidedPct",
                "sourceRepostPublishedAtIsrael"]},
            "includedInCurrentModel": True, "statusLabel": "הסקר הפעיל — מועדי האיסוף אומתו בפרסום המקורי",
            "summary": " ".join(poll["notes"]), "sourceUrl": poll["sourceDocument"]["archiveUrl"],
            "primarySourceUrl": poll["sourceUrl"], "sourceTier": poll["sourceTier"],
            "sourceKind": poll["sourceDocument"]["kind"], "sourceSha256": poll["sourceDocument"]["sha256"],
            "tables": [{"label": "המנדטים והאחוזים שפורסמו — תא ריק הוא נתון חסר", "page": 1,
                        "columns": [{"key": "party", "label": "מפלגה", "type": "text"},
                                    {"key": "seats", "label": "מנדטים", "type": "seats"},
                                    {"key": "rawPct", "label": "אחוז שפורסם", "type": "percent"}], "rows": rows}]}


def proposed_files():
    values = {rel: read(ROOT / rel) for rel in MUTABLE}
    current, history, sources, review = [values[rel] for rel in MUTABLE[:4]]
    polls = []
    for spec in SPECS:
        candidate, _ = candidate_check(spec)
        poll = normalized(spec, candidate)
        polls.append(poll)
        current["polls"] = [poll if p["pollsterId"] == spec["pollsterId"] else p for p in current["polls"]]
        old = next(p for p in history["polls"] if p.get("sourcePollId") == spec["oldId"])
        old.update(recordStatus="superseded-reviewed-record", replacedByPollId=spec["id"])
        row = copy.deepcopy(poll)
        row.update(id=spec["historyId"], sourcePollId=spec["id"], archiveSourceUrl=poll["validationSourceUrl"],
                   recordStatus="current-reviewed-record")
        history["polls"].append(row)
        group = [p for p in history["polls"] if p["pollsterId"] == spec["pollsterId"]]
        coverage = next(p for p in history["coverage"] if p["pollsterId"] == spec["pollsterId"])
        coverage.update(pollCount=len(group), firstDate=min(p["date"] for p in group), lastDate=DAY,
                        primarySourceUrl=poll["sourceUrl"], validationSourceUrl=poll["validationSourceUrl"],
                        validationNote="המנדטים, אחוזי החסימה ומועד האיסוף ב־12.10 אומתו בפרסום המקורי; נתונים שלא פורסמו נשארו חסרים.")
        history["supplementalSourceUrls"] = list(dict.fromkeys([*history.get("supplementalSourceUrls", []),
                                                               poll["sourceUrl"], *poll["secondarySourceUrls"]]))
        old_reports = [p for p in review["reports"] if p.get("pollsterId") == spec["pollsterId"] and p.get("includedInCurrentModel")]
        assert len(old_reports) == 1 and old_reports[0]["date"] == spec["oldDate"]
        old_reports[0].update(includedInCurrentModel=False, statusLabel="הוחלף בסקר 12.10; נשמר בהיסטוריה")
        review["reports"].insert(0, report_for(poll))
        old_sources = [p for p in sources["sources"] if p.get("id") == spec["pollsterId"]]
        assert len(old_sources) == 1
        old_sources[0].pop("id")
        old_sources[0]["type"] = "historical-poll-source"
        old_sources[0].setdefault("notes", []).append("הוחלף בסקר 12.10.2026; נשמר בהיסטוריה.")
        sources["sources"].append({"id": spec["pollsterId"], "title": poll["publisher"] + " / " + poll["pollster"] + " — 12.10.2026",
                                   "url": poll["sourceUrl"], "type": "original-publisher", "accessedAt": DAY,
                                   "status": "reviewed-original-publisher-fieldwork-verified", "secondarySourceUrls": poll["secondarySourceUrls"], "notes": poll["notes"]})
        audit = values[spec["audit"]]
        proof_name = poll["sourceDocument"]["fileName"]
        audited = {"pollId": spec["historyId"], "sourcePollId": spec["id"], "pollsterId": spec["pollsterId"],
                   "publisher": poll["publisher"], "publicationDate": DAY, "fieldworkStart": DAY, "fieldworkEnd": DAY,
                   "eligibleStrict": True, "includeInStrictPostClose": True, "crossesClosureDate": False,
                   "status": "verified-after-closure", "sampleSize": poll["sampleSize"],
                   "collectionMode": poll["samplingMethod"], "marginOfErrorPct": poll["reportedMarginOfErrorPct"],
                   "sourceUrl": poll["sourceUrl"], "evidencePath": (TV / proof_name).relative_to(ROOT).as_posix(),
                   "evidenceSha256": sha(TV / proof_name), "evidenceParagraph": spec["fieldworkQuote"],
                   "methodologyLocator": spec["locator"], "certainty": "verified-explicit-original-publisher-fieldwork-dates",
                   "reason": "Original publisher explicitly documents collection on October12, wholly after September8 closure; no publication/repost-date substitution.",
                   "evidence": [{"file": (TV / proof_name).relative_to(ROOT).as_posix(), "url": poll["sourceUrl"],
                                 "kind": "original-publisher-web-article", "quote": spec["fieldworkQuote"],
                                 "locator": spec["locator"], "sha256": sha(TV / proof_name)}]}
        assert spec["historyId"] not in {p["pollId"] for p in audit[spec["auditRows"]]}
        audit[spec["auditRows"]].append(audited)
        if spec["auditRows"] == "rows":
            audit["auditedAt"] = DAY
            audit["counts"] = {"records": len(audit["rows"]), "verifiedEligible": sum(p["eligibleStrict"] for p in audit["rows"]),
                               "unknown": sum(not p["eligibleStrict"] for p in audit["rows"])}
        else:
            audit["checkedAt"] = audit["auditDate"] = DAY
            audit["includedCount"] = sum(p.get("eligibleStrict", p.get("includeInStrictPostClose", False)) for p in audit["polls"])
            audit["excludedCount"] = len(audit["polls"]) - audit["includedCount"]
    history["polls"].sort(key=lambda p: (p["date"], p["pollsterId"], p["id"]))
    note = "נוספו סקרי חדשות 12 וחדשות 14 מ־12.10.2026: שמונה מכונים פעילים ו־117 סקרים בהיסטוריה. מועדי האיסוף של שניהם אומתו במקורות המקוריים; ערוץ 14 נשאר מחוץ לשקלול ברירת המחדל."
    current.update(asOf=DAY, version="2026-10-12.evening-n12-c14-v1", metadataUpdatedAt=DAY, updateNote=note)
    current.setdefault("notes", []).append(note)
    review.update(checkedAt=DAY, summary=note)
    current["documentReview"] = copy.deepcopy(review)
    history["asOf"] = sources["asOf"] = DAY
    history["metadataUpdatedAt"] = DAY
    history.setdefault("notes", []).append(note)
    sources["latestSourceCheck"] = {"checkedAt": DAY, "sources": [p["sourceUrl"] for p in polls],
        "note": note, "sourceScanReceiptUrl": PUBLIC_BASE + "n12/source-summary.json",
        "primaryPublisherReceiptUrl": PUBLIC_BASE + "n12/network-receipts.json",
        "limitations": ["Original N12 article read successfully; original N12 broadcast player returned403, so broadcast frames were not verified.",
                        "N12 election index returned an error page; direct home/politics/original article were read.",
                        "Compiled To120 noon fieldwork conflict remains unverified and is not used to change historical records."],
        "previousCheckRetainedInCheckpoint": "artifacts/poll-checks/2026-10-12-evening/before/data/sources.json"}
    return values, polls


def apply():
    checks = preflight()
    assert read(ART / "ingestion-preflight.json") == checks, "Run --check on unchanged candidates and inputs"
    values, polls = proposed_files()
    assert len(values[MUTABLE[0]]["polls"]) == 8 and len(values[MUTABLE[1]]["polls"]) == 117
    for spec, poll in zip(SPECS, polls):
        folder = PUBLIC / spec["folder"]
        folder.mkdir(parents=True)
        for source, name in source_files(spec):
            shutil.copy2(source, folder / name)
            assert sha(folder / name) == checks["sourceHashes"][spec["folder"]][name]
        immutable_write(folder / "reviewed-poll.json", poll)
        immutable_write(folder / "ingested-poll.json", poll)
        (folder / "source-extract.txt").write_bytes(extract_text(spec, poll).encode("utf-8"))
    for rel, value in values.items():
        (ROOT / rel).write_bytes(encoded(value))
    frozen_check()
    receipt = {"status": "PASS", "phase": "applied-awaiting-independent-review", "asOf": DAY,
               "baselineAsOf": BASELINE, "candidateIds": checks["candidateIds"],
               "newHistoryIds": [spec["historyId"] for spec in SPECS], "activePollCount": 8, "historyPollCount": 117,
               "strictCandidateCount": 46, "strictEligibleCount": 41, "strictWithoutChannel14Count": 33,
               "checkpointManifestSha256": checks["checkpointManifestSha256"],
               "preflightSha256": sha(ART / "ingestion-preflight.json"), "sourceHashes": checks["sourceHashes"],
               "changedCanonicalFiles": {rel: sha(ROOT / rel) for rel in MUTABLE},
               "publicEvidenceFiles": {p.relative_to(PUBLIC).as_posix(): sha(p) for p in sorted(PUBLIC.rglob("*")) if p.is_file()},
               "rawMissingnessRetained": True, "historicalWeightsUnchanged": True,
               "noNumericalTrendsOrDashboardBuilt": True, "channel14PublishedLeft46Retained": True,
               "n12OriginalBroadcastFramesClaimedVerified": False}
    immutable_write(ART / "ingestion-receipt.json", receipt)
    immutable_write(PUBLIC / "ingestion-receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ["status", "phase", "candidateIds", "activePollCount", "historyPollCount", "strictEligibleCount"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.check:
        result = preflight()
        immutable_write(ART / "ingestion-preflight.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        apply()


if __name__ == "__main__":
    main()
