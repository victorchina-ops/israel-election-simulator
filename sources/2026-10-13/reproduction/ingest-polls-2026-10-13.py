"""Scoped October 13 poll ingestion; requires a frozen reviewed source plan.

Prepare/review source-plan.json first, pinning candidate hashes and an explicit
safe public-file allowlist. --check is read-only apart from its dated receipt.
--apply changes four survey files and three fieldwork audits only; it never
changes weights, party catalogue, authored UI, model code or numerical outputs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY, BASELINE = "2026-10-13", "2026-10-12"
ART = ROOT / "artifacts/poll-checks/2026-10-13"
BEFORE = ART / "before"
PLAN = ART / "source-plan.json"
PUBLIC = ROOT / "github-pages/sources/2026-10-13"
PUBLIC_BASE = "https://victorchina-ops.github.io/israel-election-simulator/sources/2026-10-13/"
MUTABLE = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
           "data/survey-documents-2026-09-14.json", "artifacts/strict-post-close/c14-i24-fieldwork.json",
           "artifacts/strict-post-close/c16-tatika-fieldwork.json", "artifacts/strict-post-close/lazar-fieldwork.json"]
EXPECTED = {
    "direct_polls": {"folder": "i24", "oldId": "direct_polls_2026-10-08", "oldDate": "2026-10-08", "audit": MUTABLE[4]},
    "maagar_mochot": {"folder": "c16", "oldId": "maagar_mochot_2026-10-06", "oldDate": "2026-10-06", "audit": MUTABLE[5]},
    "lazar": {"folder": "walla", "oldId": "lazar_2026-10-09", "oldDate": "2026-10-09", "audit": MUTABLE[6]},
}


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
        assert path.read_bytes() == body, f"Changed dated evidence: {path}"
    else:
        path.write_bytes(body)


def frozen_check():
    manifest = read(BEFORE / "manifest.json")
    assert manifest["baselineAsOf"] == BASELINE and manifest["updateDate"] == DAY
    assert manifest["activePollCount"] == 8 and manifest["historyPollCount"] == 117
    for rel, digest in manifest["files"].items():
        assert sha(BEFORE / rel) == digest, f"Checkpoint changed: {rel}"
    for category in ["authorContentHashes", "frozenEvidenceHashes", "protectedRuntimeHashes", "frozenConditionalAndArtisticHashes"]:
        for rel, digest in manifest[category].items():
            assert sha(ROOT / rel) == digest, f"Preserved author/runtime/evidence changed: {rel}"
    for path in (ROOT / "data").glob("*.json"):
        rel = path.relative_to(ROOT).as_posix()
        if rel not in MUTABLE:
            assert sha(path) == manifest["files"][rel], f"Unrelated model/weight/catalogue data changed: {rel}"
    return manifest


def strict_eligible(poll):
    start, end = poll.get("fieldworkStart"), poll.get("fieldworkEnd")
    if poll.get("fieldworkVerified") is not True:
        return False
    assert start and end and "2026-09-09" <= start <= end <= poll["date"]
    return True


def plan_check():
    plan = read(PLAN)
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY
    specs = plan["polls"]
    assert len(specs) == 3 and {s["pollsterId"] for s in specs} == set(EXPECTED)
    for spec in specs:
        expected = EXPECTED[spec["pollsterId"]]
        assert spec["folder"] == expected["folder"]
        path = ROOT / spec["candidatePath"]
        assert path.resolve().is_relative_to(ART.resolve())
        assert sha(path) == spec["candidateSha256"]
        poll = read(path)
        assert poll["pollsterId"] == spec["pollsterId"]
        assert poll["id"] == spec["pollsterId"] + "_" + DAY
        assert poll["date"] == DAY and poll["replacesPollId"] == expected["oldId"]
        assert poll["seats"] == spec["expectedSeats"]
        assert sum(poll["seats"].values()) == poll["seatTotal"] == 120
        assert all(isinstance(v, int) and v >= 0 for v in poll["seats"].values())
        assert poll["reportedPercentages"] == spec["expectedReportedPercentages"]
        assert poll["sourceBlocSeats"] == spec["expectedSourceBlocSeats"]
        assert sum(poll["sourceBlocSeats"].values()) == 120
        assert strict_eligible(poll) is spec["strictEligible"]
        if poll.get("sampleSize") is not None:
            assert isinstance(poll["sampleSize"], int) and poll["sampleSize"] > 0
        if spec["pollsterId"] == "maagar_mochot":
            assert poll["sampleSize"] is None, "Do not replace >2000 by an exact n"
            assert poll.get("sampleSizeLowerBoundExclusive") == 2000
        assert set(poll.get("modelOnlyPercentageIds", [])).isdisjoint(poll["reportedPercentages"])
        for bound_party in poll.get("publishedBounds", {}):
            assert bound_party not in poll["reportedPercentages"], "Censored bounds are not exact published values"
        names = set()
        for evidence in spec["publicFiles"]:
            source = ROOT / evidence["sourcePath"]
            name = evidence["publicName"]
            assert source.resolve().is_relative_to(ART.resolve())
            assert Path(name).name == name and name not in names
            names.add(name)
            assert sha(source) == evidence["sha256"], evidence["sourcePath"]
        assert "frozen-reviewed-candidate.json" in names
        copied_candidate = next(e for e in spec["publicFiles"] if e["publicName"] == "frozen-reviewed-candidate.json")
        assert copied_candidate["sha256"] == spec["candidateSha256"]
        assert poll["sourceDocument"]["fileName"] in names
        assert poll["sourceDocument"]["extractFileName"] in names
        if spec["strictEligible"]:
            assert spec.get("fieldworkEvidence"), "Verified fieldwork needs original evidence"
        for evidence in spec.get("fieldworkEvidence", []):
            assert sha(ROOT / evidence["file"]) == evidence["sha256"]
    return plan


def normalized(spec, candidate):
    poll = copy.deepcopy(candidate)
    base = PUBLIC_BASE + spec["folder"] + "/"
    poll["secondarySourceUrls"] = list(dict.fromkeys([
        *[u for u in poll.get("secondarySourceUrls", []) if not u.startswith(PUBLIC_BASE)],
        *[base + e["publicName"] for e in spec["publicFiles"]], base + "reviewed-poll.json", base + "source-extract.txt",
    ]))
    poll["validationSourceUrl"] = base + "reviewed-poll.json"
    poll["sourceDocument"]["archiveUrl"] = base + poll["sourceDocument"]["fileName"]
    poll["sourceDocument"]["extractArchiveUrl"] = base + poll["sourceDocument"]["extractFileName"]
    if poll["sourceDocument"].get("originalGraphicFileName"):
        poll["sourceDocument"]["originalGraphicArchiveUrl"] = base + poll["sourceDocument"]["originalGraphicFileName"]
    if poll["sourceDocument"].get("originalGraphicFiles"):
        poll["sourceDocument"]["originalGraphicArchiveUrls"] = [base + p["file"]
                                                              for p in poll["sourceDocument"]["originalGraphicFiles"]]
    poll["unpublishedPercentagePartyIds"] = [p["id"] for p in read(ROOT / "data/parties.json")
                                            if p["id"] not in poll["reportedPercentages"]]
    return poll


def extract_text(spec, poll):
    return (f"Reviewed published observation {poll['id']}; publication {poll['date']}.\n"
            f"Source tier: {poll['sourceTier']}; original source: {poll['sourceUrl']}.\n"
            + "Published mandates: " + json.dumps(poll["seats"], ensure_ascii=False) + "\n"
            + "Exact published percentages: " + json.dumps(poll["reportedPercentages"], ensure_ascii=False) + "\n"
            + "Published bounds, never treated as exact percentages: " + json.dumps(poll.get("publishedBounds", {}), ensure_ascii=False) + "\n"
            + "Published source blocs: " + json.dumps(poll["sourceBlocSeats"], ensure_ascii=False) + "\n"
            + "Sample size exact/exclusive-lower-bound: " + str(poll.get("sampleSize")) + "/" + str(poll.get("sampleSizeLowerBoundExclusive")) + "\n"
            + "Verified strict fieldwork eligibility: " + str(spec["strictEligible"]) + "; dates "
            + str(poll.get("fieldworkStart")) + " to " + str(poll.get("fieldworkEnd")) + "\n"
            + "Missing data are not zero and not inherited from an earlier survey.\n"
            + "Model-only percentages: " + json.dumps(poll.get("modelOnlyPercentageIds", [])) + "\n"
            + "Source review notes:\n" + "\n".join(poll.get("notes", [])) + "\n")


def preflight():
    manifest, plan = frozen_check(), plan_check()
    for rel in MUTABLE:
        assert sha(ROOT / rel) == manifest["files"][rel], f"Canonical baseline changed: {rel}"
    current, history = [read(ROOT / f"data/{n}.json") for n in ["current-polls", "poll-history"]]
    assert current["asOf"] == history["asOf"] == BASELINE
    assert len(current["polls"]) == len({p["pollsterId"] for p in current["polls"]}) == 8
    assert len(history["polls"]) == len({p["id"] for p in history["polls"]}) == 117
    assert len({(p["pollsterId"], p["date"]) for p in history["polls"]}) == 117
    for spec in plan["polls"]:
        expected = EXPECTED[spec["pollsterId"]]
        assert [p["id"] for p in current["polls"] if p["pollsterId"] == spec["pollsterId"]] == [expected["oldId"]]
        assert not any(p["pollsterId"] == spec["pollsterId"] and p["date"] == DAY for p in history["polls"])
        assert sum(p.get("sourcePollId") == expected["oldId"] for p in history["polls"]) == 1
    assert not PUBLIC.exists(), "Never overwrite a dated source release"
    eligible_added = sum(s["strictEligible"] for s in plan["polls"])
    return {"status": "PASS", "phase": "preflight", "asOf": DAY, "baselineAsOf": BASELINE,
            "checkpointManifestSha256": sha(BEFORE / "manifest.json"), "sourcePlanSha256": sha(PLAN),
            "candidateHashes": {s["pollsterId"]: s["candidateSha256"] for s in plan["polls"]},
            "expectedActiveCount": 8, "expectedHistoryCount": 120, "expectedStrictCandidates": 49,
            "expectedStrictEligible": 41 + eligible_added, "expectedStrictWithoutChannel14": 33 + eligible_added,
            "inputHashes": {rel: sha(ROOT / rel) for rel in MUTABLE}}


def report_for(poll):
    def bound_label(bound):
        if not bound:
            return None
        if bound.get("maxExclusive") and bound.get("max") is not None:
            return "פחות מ־" + str(bound["max"]) + "%"
        return json.dumps(bound, ensure_ascii=False)

    rows = [{"party": p["name"], "partyId": p["id"], "seats": poll["seats"].get(p["id"]),
             "rawPct": poll["reportedPercentages"].get(p["id"]),
             "publishedBounds": bound_label(poll.get("publishedBounds", {}).get(p["id"]))}
            for p in read(ROOT / "data/parties.json") if p.get("ballot") is not False]
    rows += [{"party": p["name"], "partyId": None, "seats": p.get("seats"), "rawPct": p.get("pct"),
              "publishedBounds": bound_label(p.get("publishedBounds") or
                    ({"max": p["pctUpperBound"], "maxExclusive": p.get("maxExclusive", False)}
                     if p.get("pctUpperBound") is not None else None))}
             for p in poll.get("unmodelledNamedParties", [])]
    metadata = {k: copy.deepcopy(poll[k]) for k in poll if k not in
                {"id", "seats", "percentages", "reportedPercentages", "secondarySourceUrls", "sourceDocument", "notes", "unmodelledNamedParties"}}
    return {**metadata, "id": poll["pollsterId"] + "-" + DAY,
            "fileName": poll["sourceDocument"]["fileName"], "includedInCurrentModel": True,
            "statusLabel": "הסקר הפעיל — נתוני המקור נשמרים; שדות חסרים אינם אפס",
            "summary": " ".join(poll.get("notes", [])), "sourceUrl": poll["sourceDocument"]["archiveUrl"],
            "primarySourceUrl": poll["sourceUrl"], "sourceKind": poll["sourceDocument"]["kind"],
            "sourceSha256": poll["sourceDocument"]["sha256"],
            "tables": [{"label": "מנדטים, אחוזים מדויקים וחסמים שפורסמו — תא ריק הוא נתון חסר", "page": 1,
                        "columns": [{"key": "party", "label": "מפלגה", "type": "text"},
                                    {"key": "seats", "label": "מנדטים", "type": "seats"},
                                    {"key": "rawPct", "label": "אחוז שפורסם", "type": "percent"},
                                    {"key": "publishedBounds", "label": "חסם שפורסם", "type": "text"}], "rows": rows}]}


def proposed_files():
    plan = plan_check()
    values = {rel: read(ROOT / rel) for rel in MUTABLE}
    current, history, sources, review = [values[rel] for rel in MUTABLE[:4]]
    polls = []
    for spec in plan["polls"]:
        expected = EXPECTED[spec["pollsterId"]]
        poll = normalized(spec, read(ROOT / spec["candidatePath"]))
        polls.append(poll)
        current["polls"] = [poll if p["pollsterId"] == spec["pollsterId"] else p for p in current["polls"]]
        old = next(p for p in history["polls"] if p.get("sourcePollId") == expected["oldId"])
        old.update(recordStatus="superseded-reviewed-record", replacedByPollId=poll["id"])
        row = copy.deepcopy(poll)
        row.update(id="history_" + poll["id"] + "_current", sourcePollId=poll["id"],
                   archiveSourceUrl=poll["validationSourceUrl"], recordStatus="current-reviewed-record")
        history["polls"].append(row)
        group = [p for p in history["polls"] if p["pollsterId"] == spec["pollsterId"]]
        coverage = next(p for p in history["coverage"] if p["pollsterId"] == spec["pollsterId"])
        coverage.update(pollCount=len(group), firstDate=min(p["date"] for p in group), lastDate=DAY,
                        primarySourceUrl=poll["sourceUrl"], validationSourceUrl=poll["validationSourceUrl"],
                        validationNote="המנדטים, האחוזים והחסמים נשמרו לפי המקור; פרטי שדה ומדגם שלא אומתו נשארו חסרים.")
        history["supplementalSourceUrls"] = list(dict.fromkeys([*history.get("supplementalSourceUrls", []),
                                                               poll["sourceUrl"], *poll["secondarySourceUrls"]]))
        previous_reports = [p for p in review["reports"] if p.get("pollsterId") == spec["pollsterId"] and p.get("includedInCurrentModel")]
        assert len(previous_reports) == 1 and previous_reports[0]["date"] == expected["oldDate"]
        previous_reports[0].update(includedInCurrentModel=False, statusLabel="הוחלף בסקר 13.10; נשמר בהיסטוריה")
        review["reports"].insert(0, report_for(poll))
        old_sources = [p for p in sources["sources"] if p.get("id") == spec["pollsterId"]]
        assert len(old_sources) == 1
        old_sources[0].pop("id")
        old_sources[0]["type"] = "historical-poll-source"
        old_sources[0].setdefault("notes", []).append("הוחלף בסקר 13.10.2026; נשמר בהיסטוריה.")
        sources["sources"].append({"id": spec["pollsterId"], "title": poll["publisher"] + " / " + poll["pollster"] + " — 13.10.2026",
                                   "url": poll["sourceUrl"], "type": poll["sourceTier"], "accessedAt": DAY,
                                   "status": "reviewed-new-published-observation", "secondarySourceUrls": poll["secondarySourceUrls"], "notes": poll.get("notes", [])})
        audit = values[expected["audit"]]
        audit_rows = audit["polls"]
        assert row["id"] not in {p["pollId"] for p in audit_rows}
        qualified = spec["strictEligible"]
        audited = {"pollId": row["id"], "sourcePollId": poll["id"], "pollsterId": poll["pollsterId"],
                   "publisher": poll["publisher"], "publicationDate": DAY,
                   "fieldworkStart": poll.get("fieldworkStart"), "fieldworkEnd": poll.get("fieldworkEnd"),
                   "eligibleStrict": qualified, "includeInStrictPostClose": qualified,
                   "crossesClosureDate": False if qualified else None,
                   "status": "verified-after-closure" if qualified else "unknown-fieldwork",
                   "sampleSize": poll.get("sampleSize"), "sampleSizeLowerBoundExclusive": poll.get("sampleSizeLowerBoundExclusive"),
                   "collectionMode": poll.get("samplingMethod"), "marginOfErrorPct": poll.get("reportedMarginOfErrorPct"),
                   "sourceUrl": poll["sourceUrl"], "evidence": copy.deepcopy(spec.get("fieldworkEvidence", [])),
                   "certainty": "verified-explicit-fieldwork-dates" if qualified else "unverified-no-date-imputation",
                   "reason": "Verified actual collection interval wholly after September8 closure." if qualified
                             else "Published observation is verified, but collection dates are unknown; publication/repost never substitutes for fieldwork."}
        if audited["evidence"]:
            first = audited["evidence"][0]
            audited.update(evidencePath=first["file"], evidenceSha256=first["sha256"], evidenceParagraph=first["quote"])
        audit_rows.append(audited)
        audit["auditDate"] = DAY
        if "checkedAt" in audit:
            audit["checkedAt"] = DAY
        included = sum(p.get("eligibleStrict", p.get("includeInStrictPostClose", False)) for p in audit_rows)
        if "includedCount" in audit:
            audit["includedCount"], audit["excludedCount"] = included, len(audit_rows) - included
        if isinstance(audit.get("summary"), dict):
            audit["summary"].update(assignedPolls=len(audit_rows), verifiedEligible=included, excludedUnverified=len(audit_rows)-included)
    history["polls"].sort(key=lambda p: (p["date"], p["pollsterId"], p["id"]))
    note = "נוספו שלושה סקרים מ־13.10.2026: i24, ערוץ 16 ווואלה/לזר; שמונה מכונים פעילים ו־120 סקרים בהיסטוריה. נתונים חסרים וחסמים נשמרים בנפרד מאפסים ומאחוזים מדויקים."
    current.update(asOf=DAY, version="2026-10-13.i24-c16-walla-v1", metadataUpdatedAt=DAY, updateNote=note)
    current.setdefault("notes", []).append(note)
    review.update(checkedAt=DAY, summary=note)
    current["documentReview"] = copy.deepcopy(review)
    history["asOf"] = sources["asOf"] = DAY
    history["metadataUpdatedAt"] = DAY
    history.setdefault("notes", []).append(note)
    sources["latestSourceCheck"] = {"checkedAt": DAY, "sources": [p["sourceUrl"] for p in polls],
                                   "note": note, "sourceReview": copy.deepcopy(plan.get("sourceReview", {})),
                                   "previousCheckRetainedInCheckpoint": "artifacts/poll-checks/2026-10-13/before/data/sources.json"}
    return values, polls, plan


def apply():
    checks = preflight()
    assert read(ART / "ingestion-preflight.json") == checks, "Run --check on unchanged reviewed inputs first"
    values, polls, plan = proposed_files()
    assert len(values[MUTABLE[0]]["polls"]) == 8 and len(values[MUTABLE[1]]["polls"]) == 120
    for spec, poll in zip(plan["polls"], polls):
        folder = PUBLIC / spec["folder"]
        folder.mkdir(parents=True)
        for evidence in spec["publicFiles"]:
            shutil.copy2(ROOT / evidence["sourcePath"], folder / evidence["publicName"])
            assert sha(folder / evidence["publicName"]) == evidence["sha256"]
        immutable_write(folder / "reviewed-poll.json", poll)
        immutable_write(folder / "ingested-poll.json", poll)
        (folder / "source-extract.txt").write_bytes(extract_text(spec, poll).encode("utf-8"))
    for rel, value in values.items():
        (ROOT / rel).write_bytes(encoded(value))
    frozen_check()
    receipt = {**checks, "phase": "applied-awaiting-independent-review", "activePollCount": 8, "historyPollCount": 120,
               "preflightSha256": sha(ART / "ingestion-preflight.json"),
               "changedCanonicalFiles": {rel: sha(ROOT / rel) for rel in MUTABLE},
               "publicEvidenceFiles": {p.relative_to(PUBLIC).as_posix(): sha(p) for p in sorted(PUBLIC.rglob("*")) if p.is_file()},
               "rawMissingnessAndCensoredBoundsRetained": True, "historicalWeightsAndCatalogueUnchanged": True,
               "conditionalAndArtisticOutputsUnchanged": True, "noNumericalAnalysesOrDashboardBuilt": True}
    immutable_write(ART / "ingestion-receipt.json", receipt)
    immutable_write(PUBLIC / "ingestion-receipt.json", receipt)
    immutable_write(PUBLIC / "source-plan.json", plan)
    print(json.dumps({k: receipt[k] for k in ["status", "phase", "activePollCount", "historyPollCount", "expectedStrictEligible", "expectedStrictWithoutChannel14"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.check:
        result = preflight()
        immutable_write(ART / "ingestion-preflight.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        apply()


if __name__ == "__main__":
    main()
