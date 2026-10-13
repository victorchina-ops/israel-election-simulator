"""Independent October 13 ingestion review, before numerical/model rebuilding.

Rereads the immutable source candidates and pre-update checkpoint without
importing the importer. Only the dated validation receipt is written.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import collections
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-13"
BEFORE = ART / "before"
PUBLIC = ROOT / "github-pages/sources/2026-10-13"
BASE = "https://victorchina-ops.github.io/israel-election-simulator/"
FILES = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
         "data/survey-documents-2026-09-14.json", "artifacts/strict-post-close/c14-i24-fieldwork.json",
         "artifacts/strict-post-close/c16-tatika-fieldwork.json", "artifacts/strict-post-close/lazar-fieldwork.json"]
EXPECTED_OLD = {"direct_polls":"direct_polls_2026-10-08", "maagar_mochot":"maagar_mochot_2026-10-06", "lazar":"lazar_2026-10-09"}
DAY = "2026-10-13"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def index(rows, key):
    values = {r[key]: r for r in rows}
    assert len(values) == len(rows), ("duplicate", key)
    return values


def immutable_write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    if path.exists():
        assert path.read_bytes() == data, f"Changed dated receipt: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def main():
    manifest = read(BEFORE / "manifest.json")
    plan = read(ART / "source-plan.json")
    specs = {s["pollsterId"]:s for s in plan["polls"]}
    assert plan["status"] == "reviewed" and set(specs) == set(EXPECTED_OLD)
    assert manifest["baselineAsOf"] == "2026-10-12" and manifest["activePollCount"] == 8 and manifest["historyPollCount"] == 117
    for rel,digest in manifest["files"].items():
        assert sha(BEFORE / rel) == digest, ("frozen checkpoint",rel)
    for category in ["authorContentHashes","frozenEvidenceHashes","protectedRuntimeHashes","frozenConditionalAndArtisticHashes"]:
        assert all(sha(ROOT / rel) == digest for rel,digest in manifest[category].items()), category
    preserved_model = ["data/calibration.json","data/weight-presets.json","data/parties.json","data/turnout-2022.json",
                       "dashboard/src/data.json","dashboard-snapshot.json","artifacts/dashboard-baseline.json","github-pages/index.html"]
    for rel in preserved_model:
        assert sha(ROOT / rel) == manifest["files"][rel], ("outside ingestion scope",rel)
    receipt = read(ART / "ingestion-receipt.json")
    assert receipt["status"] == "PASS" and receipt["asOf"] == DAY
    assert receipt["sourcePlanSha256"] == sha(ART / "source-plan.json")
    assert receipt["checkpointManifestSha256"] == sha(BEFORE / "manifest.json")
    assert receipt["preflightSha256"] == sha(ART / "ingestion-preflight.json")
    assert set(receipt["changedCanonicalFiles"]) == set(FILES)
    assert all(sha(ROOT / rel) == digest for rel,digest in receipt["changedCanonicalFiles"].items())
    assert all(sha(PUBLIC / rel) == digest for rel,digest in receipt["publicEvidenceFiles"].items())
    assert read(PUBLIC / "source-plan.json") == plan
    values = [read(ROOT / rel) for rel in FILES]
    before = [read(BEFORE / rel) for rel in FILES]
    current,history,sources,documents = values[:4]
    old_current,old_history,old_sources,old_documents = before[:4]
    assert current["asOf"] == history["asOf"] == sources["asOf"] == documents["checkedAt"] == DAY
    active,old_active = index(current["polls"],"pollsterId"),index(old_current["polls"],"pollsterId")
    archive,old_archive = index(history["polls"],"id"),index(old_history["polls"],"id")
    assert len(active) == len(old_active) == 8 and active.keys() == old_active.keys()
    assert len(archive) == 120 and len(old_archive) == 117
    assert len({p["id"] for p in current["polls"]}) == 8
    assert len({(p["pollsterId"],p["date"]) for p in history["polls"]}) == 120
    new_history_ids = {"history_"+pid+"_"+DAY+"_current" for pid in specs}
    assert set(archive)-set(old_archive) == new_history_ids
    for pid,p in old_active.items():
        if pid not in specs:
            assert active[pid] == p, ("unrelated active changed",pid)
    lifecycle = {next(p["id"] for p in old_history["polls"] if p.get("sourcePollId") == old):pid for pid,old in EXPECTED_OLD.items()}
    for history_id,original in old_archive.items():
        actual = dict(archive[history_id])
        if history_id in lifecycle:
            assert actual["recordStatus"] == "superseded-reviewed-record"
            assert actual["replacedByPollId"] == lifecycle[history_id]+"_"+DAY
            actual["recordStatus"] = original["recordStatus"]
            actual.pop("replacedByPollId")
        assert actual == original, ("old history values changed",history_id)
    source_checks = {}
    for pid,spec in specs.items():
        path = ROOT / spec["candidatePath"]
        candidate = read(path)
        folder = PUBLIC / spec["folder"]
        assert sha(path) == spec["candidateSha256"] == sha(folder / "frozen-reviewed-candidate.json")
        poll = active[pid]
        for key,value in candidate.items():
            if key not in {"secondarySourceUrls","sourceDocument","validationSourceUrl","unpublishedPercentagePartyIds"}:
                assert poll[key] == value, ("source field changed",pid,key)
        for key,value in candidate["sourceDocument"].items():
            if key not in {"archiveUrl","extractArchiveUrl","originalGraphicArchiveUrl","originalGraphicArchiveUrls"}:
                assert poll["sourceDocument"][key] == value, ("source-document field changed",pid,key)
        assert poll["date"] == DAY and poll["id"] == pid+"_"+DAY
        assert poll["seats"] == spec["expectedSeats"] and sum(poll["seats"].values()) == poll["seatTotal"] == 120
        assert poll["reportedPercentages"] == spec["expectedReportedPercentages"]
        assert poll["sourceBlocSeats"] == spec["expectedSourceBlocSeats"]
        assert read(folder / "reviewed-poll.json") == poll == read(folder / "ingested-poll.json")
        historical = dict(archive["history_"+pid+"_"+DAY+"_current"])
        for key in ["sourcePollId","archiveSourceUrl","recordStatus"]:
            historical.pop(key)
        historical["id"] = poll["id"]
        assert historical == poll
        assert sha(folder / poll["sourceDocument"]["fileName"]) == poll["sourceDocument"]["sha256"]
        assert sha(folder / poll["sourceDocument"]["extractFileName"]) == poll["sourceDocument"]["extractSha256"]
        for evidence in spec["publicFiles"]:
            assert sha(folder / evidence["publicName"]) == sha(ROOT / evidence["sourcePath"]) == evidence["sha256"]
        for part,bound in poll.get("publishedBounds",{}).items():
            assert part not in poll["reportedPercentages"], ("bound turned into published exact percentage",pid,part)
        assert set(poll.get("modelOnlyPercentageIds",[])).isdisjoint(poll["reportedPercentages"])
        if pid == "maagar_mochot":
            assert poll["sampleSize"] is None and poll["sampleSizeLowerBoundExclusive"] == 2000
            assert poll["fixedBlocSeatsForAudit"] == {"coalition":52,"opposition":50,"arab_parties":13,"unassigned":5}
        if pid == "direct_polls":
            assert poll["reportedPercentages"] == {"winter":3.1,"hendel":2.2}
            assert poll["sourceBlocSeats"] == {"coalition":57,"opposition":50,"arab_parties":13}
            assert set(poll["publishedBounds"]) == {"gantz","haredi_public","noam","israel_first"}
            assert all(b.get("max")==1 and b.get("maxExclusive") is True for b in poll["publishedBounds"].values())
            assert len(poll["unmodelledNamedParties"]) == 2
            assert all(p.get("pct") is None and p.get("pctUpperBound")==1 for p in poll["unmodelledNamedParties"])
        if pid == "lazar":
            assert poll["sampleSize"] == 601 and poll["initialSampleSize"] == 600
            assert poll["requestedParticipationCount"] == 4089 and poll["requestedParticipationSourceLabel"] == "מספר המבקשים להשתתף"
            assert poll["invitedSampleSize"] is None and poll["undecidedPct"] is None
            assert poll["reportedResponseRatePct"] == 15 and poll["reportedMarginOfErrorConfidencePct"] is None
        report = next(p for p in documents["reports"] if p["pollsterId"]==pid and p["includedInCurrentModel"])
        assert report["sampleSize"] == poll["sampleSize"] and report["date"] == DAY
        for row in report["tables"][0]["rows"]:
            if row["partyId"]:
                assert row["rawPct"] == poll["reportedPercentages"].get(row["partyId"])
                assert row["seats"] == poll["seats"].get(row["partyId"])
        source_checks[pid] = {"candidateSha256":spec["candidateSha256"],"sampleSize":poll["sampleSize"],
                              "sampleSizeLowerBoundExclusive":poll.get("sampleSizeLowerBoundExclusive"),
                              "sourceBlocSeats":poll["sourceBlocSeats"],"strictEligible":spec["strictEligible"]}
    assert current["documentReview"] == documents
    for original in old_documents["reports"]:
        revised = next(p for p in documents["reports"] if p["id"] == original["id"])
        allowed = {"includedInCurrentModel","statusLabel"} if original.get("pollsterId") in specs and original.get("includedInCurrentModel") else set()
        assert {k:v for k,v in revised.items() if k not in allowed} == {k:v for k,v in original.items() if k not in allowed}
    for original in old_sources["sources"]:
        if original.get("id") in specs:
            revised = next(p for p in sources["sources"] if p.get("url")==original["url"] and not p.get("id"))
            assert {k:v for k,v in revised.items() if k not in {"id","type","notes"}} == {k:v for k,v in original.items() if k not in {"id","type","notes"}}
            assert revised["notes"][:-1] == original["notes"]
        else:
            assert original in sources["sources"], ("unrelated source changed",original.get("url"))
    all_audits = []
    audit_hashes = {}
    for filename in ["lazar-fieldwork.json","n12-kan-c13-fieldwork.json","c14-i24-fieldwork.json","c16-tatika-fieldwork.json","new-unverified-fieldwork-2026-09-30.json"]:
        rel = "artifacts/strict-post-close/"+filename
        old,actual = read(BEFORE / rel),read(ROOT / rel)
        original_rows,rows = old.get("rows",old.get("polls",[])),actual.get("rows",actual.get("polls",[]))
        assert all(p in rows for p in original_rows), ("previous fieldwork decision changed",filename)
        if rel not in FILES:
            assert sha(ROOT / rel) == sha(BEFORE / rel)
        audit_hashes[rel] = sha(ROOT / rel)
        all_audits.extend(rows)
    audited = index(all_audits,"pollId")
    assert len(audited) == 49
    assert set(audited) == {p["id"] for p in history["polls"] if p["date"] >= "2026-09-09"}
    eligible = [p for p in all_audits if p.get("eligibleStrict",p.get("includeInStrictPostClose",False))]
    included_added = sum(s["strictEligible"] for s in specs.values())
    assert len(eligible) == 41+included_added
    default = [p for p in eligible if p["pollsterId"] != "next_data"]
    assert len(default) == 33+included_added
    for pid,spec in specs.items():
        row = audited["history_"+pid+"_"+DAY+"_current"]
        assert row["eligibleStrict"] is spec["strictEligible"]
        assert row["fieldworkStart"] == active[pid].get("fieldworkStart") and row["fieldworkEnd"] == active[pid].get("fieldworkEnd")
        if spec["strictEligible"]:
            assert row["fieldworkStart"] and "2026-09-09" <= row["fieldworkStart"] <= row["fieldworkEnd"] <= DAY
        else:
            assert row["fieldworkStart"] is None and row["fieldworkEnd"] is None
        for evidence in row["evidence"]:
            assert sha(ROOT / evidence["file"]) == evidence["sha256"]
    counts,default_counts = collections.Counter(p["pollsterId"] for p in eligible),collections.Counter(p["pollsterId"] for p in default)
    assert len(counts)==8 and len(default_counts)==7
    new_urls = []
    def walk(value):
        if isinstance(value,dict):
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
        elif isinstance(value,str) and value.startswith(BASE+"sources/2026-10-13/"):
            path = ROOT / "github-pages" / unquote(urlsplit(value).path.removeprefix("/israel-election-simulator/"))
            assert path.is_file(), ("broken new public source URL",value)
            new_urls.append(value)
    for value in [current,history,sources,documents]:walk(value)
    assert new_urls
    result = {"status":"PASS","asOf":DAY,"phase":"ingestion-validated-before-numerical-rebuilding",
              "checkpointManifestSha256":sha(BEFORE / "manifest.json"),"sourcePlanSha256":sha(ART / "source-plan.json"),
              "ingestionReceiptSha256":sha(ART / "ingestion-receipt.json"),"activePollCount":8,"historyPollCount":120,
              "previousHistoryRowsPreserved":117,"otherActivePollsUnchanged":5,"sources":source_checks,
              "fullStrict":{"candidates":49,"polls":len(eligible),"series":len(counts),"deltas":sum(n-1 for n in counts.values()),
                            "unknownFieldworkExcluded":49-len(eligible),"byInstitute":dict(sorted(counts.items()))},
              "defaultWithoutChannel14":{"polls":len(default),"series":len(default_counts),"deltas":sum(n-1 for n in default_counts.values())},
              "newPublicSourceURLs":{"uniqueCount":len(set(new_urls)),"allExistLocally":True},
              "preserved":{"authorFiles":len(manifest["authorContentHashes"]),"protectedRuntimeFiles":len(manifest["protectedRuntimeHashes"]),
                           "publishedEvidenceFiles":len(manifest["frozenEvidenceHashes"]),"conditionalAndArtisticFiles":len(manifest["frozenConditionalAndArtisticHashes"]),
                           "historicalWeightsAndPartyCatalogue":True,"modelAndDashboardNotRebuilt":True},
              "inputHashes":{rel:sha(ROOT / rel) for rel in FILES},"fieldworkAuditHashes":audit_hashes}
    immutable_write(ART / "ingestion-validation.json",result)
    immutable_write(PUBLIC / "ingestion-validation.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
