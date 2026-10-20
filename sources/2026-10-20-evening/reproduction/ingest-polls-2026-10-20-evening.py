"""Ingest three reviewed evening observations in the20Oct audit, preserving publication and fieldwork dates.

Requires the immutable reviewed20Oct source plan and unchanged completed daytime20Oct checkpoint.
Publication dates belong to each source observation; DAY is only the audit date.
The --check receipt pins all inputs. --apply changes survey registers and the three
fieldwork audit only; weights, model, UI and numerical outputs stay untouched.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-20"
BASELINE = "2026-10-20"
ART = ROOT / "artifacts/poll-checks/2026-10-20-evening"
BEFORE = ART / "before"
PLAN = ART / "source-plan.json"
PUBLIC = ROOT / "github-pages/sources/2026-10-20-evening"
PUBLIC_BASE = "https://victorchina-ops.github.io/israel-election-simulator/sources/" + "2026-10-20-evening/"
EXPECTED = {
    'next_data': {'folder':'c14', 'oldId':'next_data_2026-10-19', 'oldDate':'2026-10-19', 'date':'2026-10-20', 'audit':'artifacts/strict-post-close/c14-i24-fieldwork.json'},
    'maagar_mochot': {'folder':'c16', 'oldId':'maagar_mochot_2026-10-13', 'oldDate':'2026-10-13', 'date':'2026-10-20', 'audit':'artifacts/strict-post-close/c16-tatika-fieldwork.json'},
    'direct_polls': {'folder':'i24', 'oldId':'direct_polls_2026-10-18', 'oldDate':'2026-10-18', 'date':'2026-10-20', 'audit':'artifacts/strict-post-close/c14-i24-fieldwork.json'},
}
REGISTERS = ["data/current-polls.json", "data/poll-history.json", "data/sources.json", "data/survey-documents-2026-09-14.json"]
MUTABLE = REGISTERS + [spec["audit"] for spec in EXPECTED.values()]


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
        assert path.read_bytes() == body, ("Changed immutable evidence", str(path))
    else:
        path.write_bytes(body)


def strict_eligible(poll):
    if poll.get("fieldworkVerified") is not True:
        return False
    start, end = poll.get("fieldworkStart"), poll.get("fieldworkEnd")
    assert start and end and "2026-09-09" <= start <= end <= poll["date"]
    return True


def frozen_check():
    manifest = read(BEFORE / "manifest.json")
    assert manifest["baselineAsOf"] == BASELINE and manifest["updateDate"] == DAY
    assert manifest["activePollCount"] == 8 and manifest["historyPollCount"] == 132
    for rel, digest in manifest["files"].items():
        assert sha(BEFORE / rel) == digest, ("Checkpoint changed", rel)
    for category in ["authorContentHashes", "protectedRuntimeHashes", "frozenEvidenceHashes", "frozenConditionalAndArtisticHashes", "reviewedExactHelpers"]:
        for rel, digest in manifest[category].items():
            assert sha(ROOT / rel) == digest, ("Preserved source/evidence changed", rel)
    for path in (ROOT / "data").glob("*.json"):
        rel = path.relative_to(ROOT).as_posix()
        if rel not in MUTABLE:
            assert sha(path) == manifest["files"][rel], ("Unrelated model data changed", rel)
    return manifest


def plan_check():
    plan = read(PLAN)
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY
    assert plan["publicCopyrightScopeReviewed"] is True, "Public evidence must be reviewed factual extracts/graphics, not full authored articles"
    assert len(plan["polls"]) == len(EXPECTED) and {s["pollsterId"] for s in plan["polls"]} == set(EXPECTED)
    for spec in plan["polls"]:
        expected = EXPECTED[spec["pollsterId"]]
        assert spec["folder"] == expected["folder"]
        path = ROOT / spec["candidatePath"]
        assert path.resolve().is_relative_to(ART.resolve())
        assert sha(path) == spec["candidateSha256"]
        poll = read(path)
        assert poll["pollsterId"] == spec["pollsterId"]
        assert poll["date"] == expected["date"]
        assert poll["id"] == spec["pollsterId"] + "_" + poll["date"]
        assert poll["replacesPollId"] == expected["oldId"]
        assert poll["seats"] == spec["expectedSeats"]
        assert sum(poll["seats"].values()) == poll["seatTotal"] == 120
        assert all(type(v) is int and v >= 0 for v in poll["seats"].values())
        assert poll["reportedPercentages"] == spec["expectedReportedPercentages"]
        assert poll["sourceBlocSeats"] == spec["expectedSourceBlocSeats"]
        assert sum(poll["sourceBlocSeats"].values()) == 120
        assert strict_eligible(poll) is spec["strictEligible"]
        if poll.get("sampleSize") is not None:
            assert type(poll["sampleSize"]) is int and poll["sampleSize"] > 0
        assert set(poll.get("modelOnlyPercentageIds", [])).isdisjoint(poll["reportedPercentages"])
        assert set(poll.get("publishedBounds", {})).isdisjoint(poll["reportedPercentages"])
        names = set()
        for entry in spec["publicFiles"]:
            source, name = ROOT / entry["sourcePath"], entry["publicName"]
            assert source.resolve().is_relative_to(ART.resolve())
            assert Path(name).name == name and name not in names
            assert Path(name).suffix.lower() not in {".html", ".htm"}, "Full authored articles stay local"
            assert "web-reader" not in name and "sourceWeb" not in name, "Full web reader receipts stay local"
            names.add(name)
            assert sha(source) == entry["sha256"]
        assert "frozen-reviewed-candidate.json" in names
        assert next(e for e in spec["publicFiles"] if e["publicName"] == "frozen-reviewed-candidate.json")["sha256"] == spec["candidateSha256"]
        assert {poll["sourceDocument"]["fileName"], poll["sourceDocument"]["extractFileName"]} <= names
        if spec["strictEligible"]:
            assert spec.get("fieldworkEvidence"), "Verified fieldwork requires independent source evidence"
        for entry in spec.get("fieldworkEvidence", []):
            assert sha(ROOT / entry["file"]) == entry["sha256"]
    return plan


def normalized(spec, candidate):
    poll = copy.deepcopy(candidate)
    base = PUBLIC_BASE + spec["folder"] + "/"
    poll["secondarySourceUrls"] = list(dict.fromkeys([*[u for u in poll.get("secondarySourceUrls", []) if not u.startswith(PUBLIC_BASE)],
        *[base + e["publicName"] for e in spec["publicFiles"]], base + "reviewed-poll.json", base + "source-extract.txt"]))
    poll["validationSourceUrl"] = base + "reviewed-poll.json"
    document = poll["sourceDocument"]
    document["archiveUrl"], document["extractArchiveUrl"] = base + document["fileName"], base + document["extractFileName"]
    if document.get("originalGraphicFileName"):
        document["originalGraphicArchiveUrl"] = base + document["originalGraphicFileName"]
    if document.get("originalGraphicFiles"):
        document["originalGraphicArchiveUrls"] = [base + p["file"] for p in document["originalGraphicFiles"]]
    poll["unpublishedPercentagePartyIds"] = [p["id"] for p in read(ROOT / "data/parties.json") if p["id"] not in poll["reportedPercentages"]]
    return poll


def report_for(poll):
    def bound_label(value):
        if not value:
            return None
        if value.get("maxExclusive") and value.get("max") is not None:
            return "פחות מ־" + str(value["max"]) + "%"
        return json.dumps(value, ensure_ascii=False)
    rows = [{"party":p["name"], "partyId":p["id"], "seats":poll["seats"].get(p["id"]),
             "rawPct":poll["reportedPercentages"].get(p["id"]), "publishedBounds":bound_label(poll.get("publishedBounds", {}).get(p["id"]))}
            for p in read(ROOT / "data/parties.json") if p.get("ballot") is not False]
    rows += [{"party":p["name"], "partyId":None, "seats":p.get("seats"), "rawPct":p.get("pct"),
              "publishedBounds":bound_label(p.get("publishedBounds") or ({"max":p["pctUpperBound"], "maxExclusive":p.get("maxExclusive",False)} if p.get("pctUpperBound") is not None else None))}
             for p in poll.get("unmodelledNamedParties", [])]
    metadata = {k:copy.deepcopy(v) for k,v in poll.items() if k not in {"id","seats","percentages","reportedPercentages","secondarySourceUrls","sourceDocument","notes","unmodelledNamedParties"}}
    return {**metadata, "id":poll["pollsterId"] + "-" + poll["date"], "fileName":poll["sourceDocument"]["fileName"],
        "includedInCurrentModel":True, "statusLabel":"הסקר הפעיל — נתוני המקור נשמרים; שדות חסרים אינם אפס",
        "summary":" ".join(poll.get("notes", [])), "sourceUrl":poll["sourceDocument"]["archiveUrl"],
        "primarySourceUrl":poll["sourceUrl"], "sourceKind":poll["sourceDocument"]["kind"], "sourceSha256":poll["sourceDocument"]["sha256"],
        "tables":[{"label":"מנדטים, אחוזים מדויקים וחסמים שפורסמו — תא ריק הוא נתון חסר", "page":1,
            "columns":[{"key":"party","label":"מפלגה","type":"text"},{"key":"seats","label":"מנדטים","type":"seats"},
                       {"key":"rawPct","label":"אחוז שפורסם","type":"percent"},{"key":"publishedBounds","label":"חסם שפורסם","type":"text"}], "rows":rows}]}


def extract_text(spec, poll):
    return (f"Reviewed published observation {poll['id']}; publication {poll['date']}; audit {DAY}.\n"
        + f"Original source: {poll['sourceUrl']}.\n"
        + "Published mandates: " + json.dumps(poll["seats"],ensure_ascii=False) + "\n"
        + "Exact published percentages: " + json.dumps(poll["reportedPercentages"],ensure_ascii=False) + "\n"
        + "Published bounds, never exact percentages: " + json.dumps(poll.get("publishedBounds",{}),ensure_ascii=False) + "\n"
        + "Published source blocs: " + json.dumps(poll["sourceBlocSeats"],ensure_ascii=False) + "\n"
        + "Sample size exact/exclusive lower bound: " + str(poll.get("sampleSize")) + "/" + str(poll.get("sampleSizeLowerBoundExclusive")) + "\n"
        + "Verified fieldwork: " + str(spec["strictEligible"]) + "; " + str(poll.get("fieldworkStart")) + " to " + str(poll.get("fieldworkEnd")) + "\n"
        + "Missing values are not zero and are never inherited.\n" + "\n".join(poll.get("notes",[])) + "\n")


def baseline_cohort():
    rows = read(BEFORE / "artifacts/strict-post-close/analysis.json")["cohort"]
    full = [p for p in rows if p["eligibleStrict"]]
    return {"candidates":len(rows), "full":len(full), "without14":sum(p["pollsterId"] != "next_data" for p in full),
            "unknown":sum(not p["eligibleStrict"] for p in rows)}


def preflight():
    manifest, plan = frozen_check(), plan_check()
    for rel in MUTABLE:
        assert sha(ROOT / rel) == manifest["files"][rel], ("Canonical baseline changed",rel)
    current, history = [read(ROOT / p) for p in REGISTERS[:2]]
    assert current["asOf"] == history["asOf"] == BASELINE
    assert len(current["polls"]) == len({p["pollsterId"] for p in current["polls"]}) == 8
    assert len(history["polls"]) == len({p["id"] for p in history["polls"]}) == 132
    assert len({(p["pollsterId"],p["date"]) for p in history["polls"]}) == 132
    for spec in plan["polls"]:
        old = EXPECTED[spec["pollsterId"]]
        assert [p["id"] for p in current["polls"] if p["pollsterId"] == spec["pollsterId"]] == [old["oldId"]]
        assert not any(p["pollsterId"] == spec["pollsterId"] and p["date"] == old["date"] for p in history["polls"])
        assert sum(p.get("sourcePollId") == old["oldId"] for p in history["polls"]) == 1
    assert not PUBLIC.exists(), "Never overwrite a dated public source release"
    cohort = baseline_cohort()
    full_add = sum(s["strictEligible"] for s in plan["polls"])
    default_add = sum(s["strictEligible"] and s["pollsterId"] != "next_data" for s in plan["polls"])
    return {"status":"PASS", "phase":"preflight", "asOf":DAY, "baselineAsOf":BASELINE,
        "checkpointManifestSha256":sha(BEFORE / "manifest.json"), "sourcePlanSha256":sha(PLAN),
        "candidateHashes":{s["pollsterId"]:s["candidateSha256"] for s in plan["polls"]}, "expectedActiveCount":8,
        "expectedHistoryCount":132+len(plan["polls"]), "expectedStrictCandidates":cohort["candidates"]+len(plan["polls"]),
        "expectedStrictEligible":cohort["full"]+full_add, "expectedStrictWithoutChannel14":cohort["without14"]+default_add,
        "expectedUnverifiedFieldwork":cohort["unknown"]+len(plan["polls"])-full_add,
        "inputHashes":{rel:sha(ROOT / rel) for rel in MUTABLE}}


def proposed_files():
    plan = plan_check()
    values = {rel:read(ROOT / rel) for rel in MUTABLE}
    current, history, sources, review = [values[rel] for rel in REGISTERS]
    polls = []
    for spec in plan["polls"]:
        expected = EXPECTED[spec["pollsterId"]]
        poll = normalized(spec, read(ROOT / spec["candidatePath"]))
        polls.append(poll)
        current["polls"] = [poll if p["pollsterId"] == spec["pollsterId"] else p for p in current["polls"]]
        old = next(p for p in history["polls"] if p.get("sourcePollId") == expected["oldId"])
        old.update(recordStatus="superseded-reviewed-record", replacedByPollId=poll["id"])
        row = copy.deepcopy(poll)
        row.update(id="history_"+poll["id"]+"_current", sourcePollId=poll["id"], archiveSourceUrl=poll["validationSourceUrl"], recordStatus="current-reviewed-record")
        history["polls"].append(row)
        group = [p for p in history["polls"] if p["pollsterId"] == spec["pollsterId"]]
        coverage = next(p for p in history["coverage"] if p["pollsterId"] == spec["pollsterId"])
        coverage.update(pollCount=len(group), firstDate=min(p["date"] for p in group), lastDate=max(p["date"] for p in group),
            primarySourceUrl=poll["sourceUrl"], validationSourceUrl=poll["validationSourceUrl"],
            validationNote="המנדטים והאחוזים נשמרו לפי המקור; תאריך הפרסום נפרד מתאריכי האיסוף ומתאריך בדיקת האתר.")
        history["supplementalSourceUrls"] = list(dict.fromkeys([*history.get("supplementalSourceUrls",[]),poll["sourceUrl"],*poll["secondarySourceUrls"]]))
        reports = [p for p in review["reports"] if p.get("pollsterId") == spec["pollsterId"] and p.get("includedInCurrentModel")]
        assert len(reports) == 1 and reports[0]["date"] == expected["oldDate"]
        reports[0].update(includedInCurrentModel=False, statusLabel=f"הוחלף בסקר {poll['date']}; נשמר בהיסטוריה")
        review["reports"].insert(0,report_for(poll))
        old_sources = [p for p in sources["sources"] if p.get("id") == spec["pollsterId"]]
        assert len(old_sources) == 1
        old_sources[0].pop("id")
        old_sources[0]["type"] = "historical-poll-source"
        old_sources[0].setdefault("notes",[]).append(f"הוחלף בסקר שפורסם ב־{poll['date']}; נשמר בהיסטוריה.")
        sources["sources"].append({"id":spec["pollsterId"],"title":poll["publisher"]+" / "+poll["pollster"]+" — "+poll["date"],
            "url":poll["sourceUrl"],"type":poll["sourceTier"],"accessedAt":DAY,"status":"reviewed-new-published-observation",
            "secondarySourceUrls":poll["secondarySourceUrls"],"notes":poll.get("notes",[])})
        audit = values[expected["audit"]]
        rows = audit.get("rows",audit.get("polls"))
        assert row["id"] not in {p["pollId"] for p in rows}
        qualified = spec["strictEligible"]
        audited = {"pollId":row["id"], "sourcePollId":poll["id"], "pollsterId":poll["pollsterId"], "publisher":poll["publisher"],
            "publicationDate":poll["date"], "fieldworkStart":poll.get("fieldworkStart"), "fieldworkEnd":poll.get("fieldworkEnd"),
            "eligibleStrict":qualified,"includeInStrictPostClose":qualified,"crossesClosureDate":False if qualified else None,
            "status":"verified-after-closure" if qualified else "unknown-fieldwork", "sampleSize":poll.get("sampleSize"),
            "sampleSizeLowerBoundExclusive":poll.get("sampleSizeLowerBoundExclusive"), "collectionMode":poll.get("samplingMethod"),
            "marginOfErrorPct":poll.get("reportedMarginOfErrorPct"), "sourceUrl":poll["sourceUrl"],
            "evidence":copy.deepcopy(spec.get("fieldworkEvidence",[])),
            "certainty":"verified-explicit-fieldwork-dates" if qualified else "unverified-no-date-imputation",
            "reason":"Actual collection interval explicitly verified wholly after September8 closure." if qualified else "Publication date never substitutes for unknown fieldwork."}
        if audited["evidence"]:
            evidence = audited["evidence"][0]
            audited.update(evidencePath=evidence["file"],evidenceSha256=evidence["sha256"],evidenceParagraph=evidence["quote"])
        rows.append(audited)
        audit["auditDate"] = DAY
        for key in ["checkedAt","auditedAt"]:
            if key in audit:
                audit[key] = DAY
        included = sum(p.get("eligibleStrict",p.get("includeInStrictPostClose",False)) for p in rows)
        if "includedCount" in audit:
            audit["includedCount"],audit["excludedCount"] = included,len(rows)-included
        if isinstance(audit.get("counts"),dict):
            counts = audit["counts"]
            for key in ["eligibleStrict","included","verifiedEligible"]:
                if key in counts:
                    counts[key] = included
            for key in ["excluded","excludedUnknown","excludedUnverified","unknown"]:
                if key in counts:
                    counts[key] = len(rows)-included
            for key in ["total","assignedPolls","records"]:
                if key in counts:
                    counts[key] = len(rows)
    history["polls"].sort(key=lambda p:(p["date"],p["pollsterId"],p["id"]))
    details = " ".join(f"{p['publisher']} — אותר ב־{p['date']}; " +
        (f"איסוף מאומת {p['fieldworkStart']}–{p['fieldworkEnd']}." if p.get('fieldworkVerified') is True else
         "מועדי האיסוף לא אומתו; אינו נכלל בניתוח המגמות המחמיר.") for p in polls)
    note = ("עדכון מ־20.10.2026: עדכון ערב נפרד: נוספו סקרי ערוץ 16, i24NEWS וערוץ 14. " + details +
        f" שמונה מכונים פעילים ו־{len(history['polls'])} סקרים בהיסטוריה. כל הסקרים הקודמים נשמרו; " +
        "שדות חסרים אינם אפס. תאריך הפרסום נפרד מתאריך האיסוף. ערוץ 14 מוחרג כברירת מחדל מהשקלול.")
    current.update(asOf=DAY,version="2026-10-20.v2",metadataUpdatedAt=DAY,updateNote=note)
    current.setdefault("notes",[]).append(note)
    review.update(checkedAt=DAY,summary=note)
    current["documentReview"] = copy.deepcopy(review)
    history["asOf"] = sources["asOf"] = DAY
    history["metadataUpdatedAt"] = DAY
    history.setdefault("notes",[]).append(note)
    sources["latestSourceCheck"] = {"checkedAt":DAY,"sources":[p["sourceUrl"] for p in polls],"note":note,
        "sourceReview":copy.deepcopy(plan.get("sourceReview",{})),"previousCheckRetainedInCheckpoint":"artifacts/poll-checks/2026-10-20-evening/before/data/sources.json"}
    return values,polls,plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--apply",action="store_true")
    args = parser.parse_args()
    checks = preflight()
    if args.check:
        immutable_write(ART / "ingestion-preflight.json",checks)
        print(json.dumps(checks,ensure_ascii=False,indent=2))
        return
    assert read(ART / "ingestion-preflight.json") == checks, "Run --check on unchanged reviewed inputs first"
    values,polls,plan = proposed_files()
    assert len(values[REGISTERS[0]]["polls"]) == 8 and len(values[REGISTERS[1]]["polls"]) == checks["expectedHistoryCount"]
    for spec,poll in zip(plan["polls"],polls):
        folder = PUBLIC / spec["folder"]
        folder.mkdir(parents=True)
        for entry in spec["publicFiles"]:
            shutil.copy2(ROOT / entry["sourcePath"],folder / entry["publicName"])
            assert sha(folder / entry["publicName"]) == entry["sha256"]
        immutable_write(folder / "reviewed-poll.json",poll)
        immutable_write(folder / "ingested-poll.json",poll)
        (folder / "source-extract.txt").write_bytes(extract_text(spec,poll).encode("utf-8"))
    for rel,value in values.items():
        (ROOT / rel).write_bytes(encoded(value))
    frozen_check()
    receipt = {**checks,"phase":"applied-awaiting-independent-review","activePollCount":8,"historyPollCount":checks["expectedHistoryCount"],
        "preflightSha256":sha(ART / "ingestion-preflight.json"),"changedCanonicalFiles":{rel:sha(ROOT / rel) for rel in MUTABLE},
        "publicEvidenceFiles":{p.relative_to(PUBLIC).as_posix():sha(p) for p in sorted(PUBLIC.rglob("*")) if p.is_file()},
        "rawMissingnessAndCensoredBoundsRetained":True,"historicalWeightsAndCatalogueUnchanged":True,
        "conditionalAndArtisticOutputsUnchanged":True,"noNumericalAnalysesOrDashboardBuilt":True}
    immutable_write(ART / "ingestion-receipt.json",receipt)
    immutable_write(PUBLIC / "ingestion-receipt.json",receipt)
    immutable_write(PUBLIC / "source-plan.json",plan)
    print(json.dumps({key:receipt[key] for key in ["status","phase","activePollCount","historyPollCount","expectedStrictEligible","expectedStrictWithoutChannel14"]}))


if __name__ == "__main__":
    main()
