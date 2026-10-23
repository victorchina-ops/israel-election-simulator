"""Independent row-by-row ingestion review for the23Oct reviewed publisher update.

Rereads immutable source candidates, reviewed source plan and the full pre-update
checkpoint without importing the ingestion implementation. No canonical file is
written; only a dated receipt is created after every assertion passes.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-23"
BASELINE = "2026-10-21"
ART = ROOT / "artifacts/poll-checks/2026-10-23"
BEFORE = ART / "before"
PUBLIC = ROOT / "github-pages/sources/2026-10-23"
ALLOWED = {
    'lazar': {'folder':'maariv','audit':'artifacts/strict-post-close/lazar-fieldwork.json'},
    'tatika': {'folder':'zman','audit':'artifacts/strict-post-close/c16-tatika-fieldwork.json'},
    'kantar': {'folder':'kan','audit':'artifacts/strict-post-close/n12-kan-c13-fieldwork.json'},
    'maagar_mochot': {'folder':'c16','audit':'artifacts/strict-post-close/c16-tatika-fieldwork.json'},
    'next_data': {'folder':'c14','audit':'artifacts/strict-post-close/c14-i24-fieldwork.json'},
}
EXPECTED = {}
BASELINE_ACTIVE_COUNT = 8
BASELINE_HISTORY_COUNT = 138
FILES = []

read = lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def published_aggregate_other_check(poll, candidate_path):
    # A named residual list is not aggregateOther. Accept aggregateOther only when
    # that exact candidate and hashed primary numerical proof both report it.
    reported, raw = poll["reportedPercentages"], poll["percentages"]
    if "other" not in reported:
        if "other" in raw:
            # Existing explicit model-only mapping of individually named lists.
            # This does not add a published aggregateOther measurement.
            assert "other" in poll.get("modelOnlyPercentageIds", [])
            named = [p for p in poll.get("unmodelledNamedParties", []) if p.get("mappedTo") == "other"]
            assert named and all(p.get("name") and isinstance(p.get("pct"), (int, float))
                                 and not isinstance(p["pct"], bool) and p["pct"] >= 0 for p in named)
            assert raw["other"] == sum(p["pct"] for p in named)
            assert poll.get("otherAggregatePublished") is not True
        return
    assert "other" in raw and "other" not in poll.get("modelOnlyPercentageIds", [])
    assert raw["other"] == reported["other"]
    assert poll["sourceTier"] == "original-publisher"
    assert poll.get("percentageSourceUrls", {}).get("other") == poll["sourceUrl"]
    doc = poll["sourceDocument"]
    assert doc["primarySourceUrl"] == poll["sourceUrl"]
    proof_path = candidate_path.parent / doc["verificationFileName"]
    assert proof_path.resolve().is_relative_to(ART.resolve())
    assert sha(proof_path) == doc["verificationSha256"]
    proof = read(proof_path)
    assert proof["sourceUrl"] == poll["sourceUrl"]
    published = proof.get("reportedBelowThresholdPercentages", proof.get("reportedPercentages", {}))
    assert "other" in published and published["other"] == reported["other"]
    original_frames = {p["file"]:p for p in doc.get("originalGraphicFiles", [])}
    aggregate_frames = [p for p in proof.get("visualEvidence", [])
                        if p.get("visuallyReviewed") is True
                        and any(label in p.get("reviewedContent", "")
                                for label in ("aggregateOther", "מפלגות אחרות", "רשימות אחרות"))]
    assert aggregate_frames, "Explicit aggregateOther needs reviewed primary numerical evidence"
    for frame in aggregate_frames:
        assert frame["sourceUrl"] == poll["sourceUrl"]
        assert frame["file"] in original_frames
        assert original_frames[frame["file"]]["sha256"] == frame["sha256"]
        assert original_frames[frame["file"]].get("visuallyReviewed") is True
        frame_path = candidate_path.parent / frame["file"]
        assert frame_path.resolve().is_relative_to(ART.resolve())
        assert sha(frame_path) == frame["sha256"]


def index(rows,key):
    result = {p[key]:p for p in rows}
    assert len(result) == len(rows), ("duplicate",key)
    return result


def immutable_write(path,value):
    body = (json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    if path.exists():
        assert path.read_bytes() == body, "Changed immutable ingestion review"
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(body)



def configure_expected():
    # Independently derive the comparison identities from the frozen active rows.
    global FILES
    plan = read(ART / 'source-plan.json')
    baseline = read(BEFORE / 'data/current-polls.json')
    ids = [s['pollsterId'] for s in plan['polls']]
    assert ids and len(ids) == len(set(ids)) and set(ids) <= set(ALLOWED)
    old = {p['pollsterId']:p for p in baseline['polls']}
    EXPECTED.clear()
    for spec in plan['polls']:
        pid = spec['pollsterId']
        candidate = read(ROOT / spec['candidatePath'])
        assert spec['folder'] == ALLOWED[pid]['folder']
        assert spec['previousActivePollId'] == old[pid]['id']
        assert spec['previousActivePollDate'] == old[pid]['date']
        assert spec['publicationDate'] == candidate['date']
        assert old[pid]['date'] < candidate['date'] <= DAY
        EXPECTED[pid] = {**ALLOWED[pid], 'oldId':old[pid]['id'],
            'id':pid+'_'+candidate['date'], 'date':candidate['date']}
    FILES = ['data/current-polls.json','data/poll-history.json','data/sources.json',
             'data/survey-documents-2026-09-14.json'] + list(dict.fromkeys(s['audit'] for s in EXPECTED.values()))

def main():
    configure_expected()
    manifest = read(BEFORE / "manifest.json")
    plan = read(ART / "source-plan.json")
    specs = index(plan["polls"],"pollsterId")
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY and set(specs) == set(EXPECTED)
    assert plan["baselineAsOf"] == BASELINE and plan["checkpointManifestSha256"] == sha(BEFORE / "manifest.json")
    assert plan["publicCopyrightScopeReviewed"] is True
    assert manifest["baselineAsOf"] == BASELINE and manifest["activePollCount"] == BASELINE_ACTIVE_COUNT and manifest["historyPollCount"] == BASELINE_HISTORY_COUNT
    for rel,digest in manifest["files"].items():
        assert sha(BEFORE / rel) == digest, ("Checkpoint changed",rel)
    for family in ["authorContentHashes","protectedRuntimeHashes","frozenEvidenceHashes","frozenConditionalAndArtisticHashes","reviewedExactHelpers"]:
        for rel,digest in manifest[family].items():
            assert sha(ROOT / rel) == digest, ("Preserved evidence/code changed",rel)
    for path in (ROOT / "data").glob("*.json"):
        relative = path.relative_to(ROOT).as_posix()
        if relative not in FILES:
            assert sha(path) == manifest["files"][relative], ("Unrelated data changed",relative)
    for relative in ["dashboard/src/data.json","dashboard-snapshot.json","artifacts/dashboard-baseline.json","github-pages/index.html"]:
        assert sha(ROOT / relative) == manifest["files"][relative], ("Outside ingestion scope",relative)
    receipt = read(ART / "ingestion-receipt.json")
    assert receipt["status"] == "PASS" and receipt["asOf"] == DAY
    assert receipt["sourcePlanSha256"] == sha(ART / "source-plan.json")
    assert receipt["checkpointManifestSha256"] == sha(BEFORE / "manifest.json")
    assert receipt["preflightSha256"] == sha(ART / "ingestion-preflight.json")
    preflight = read(ART / "ingestion-preflight.json")
    assert receipt["implementationSha256"] == preflight["implementationSha256"] == sha(ROOT / "scripts/ingest-polls-2026-10-23.py")
    assert receipt["independentValidatorSha256"] == preflight["independentValidatorSha256"] == sha(Path(__file__))
    assert set(receipt["changedCanonicalFiles"]) == set(FILES)
    for relative,digest in receipt["changedCanonicalFiles"].items():
        assert sha(ROOT / relative) == digest
    for relative,digest in receipt["publicEvidenceFiles"].items():
        assert sha(PUBLIC / relative) == digest
    assert read(PUBLIC / "source-plan.json") == plan
    values = [read(ROOT / p) for p in FILES]
    before = [read(BEFORE / p) for p in FILES]
    current,history,sources,documents = values[:4]
    old_current,old_history,old_sources,old_documents = before[:4]
    assert current["asOf"] == history["asOf"] == sources["asOf"] == documents["checkedAt"] == DAY
    active, old_active = index(current["polls"],"pollsterId"), index(old_current["polls"],"pollsterId")
    archive, old_archive = index(history["polls"],"id"), index(old_history["polls"],"id")
    assert len(active) == len(old_active) == BASELINE_ACTIVE_COUNT and active.keys() == old_active.keys()
    assert len(archive) == receipt["expectedHistoryCount"] == manifest["historyPollCount"] + len(specs)
    assert len(old_archive) == manifest["historyPollCount"]
    assert len({p["id"] for p in current["polls"]}) == BASELINE_ACTIVE_COUNT
    assert len({(p["pollsterId"],p["date"]) for p in history["polls"]}) == len(archive)
    expected_new = {"history_"+spec["id"]+"_current" for spec in EXPECTED.values()}
    assert set(archive)-set(old_archive) == expected_new
    for pid,poll in old_active.items():
        if pid not in specs:
            assert active[pid] == poll, ("Unrelated current poll changed",pid)
    lifecycle = {next(p["id"] for p in old_history["polls"] if p.get("sourcePollId") == spec["oldId"]):spec["id"] for spec in EXPECTED.values()}
    for history_id,original in old_archive.items():
        actual = dict(archive[history_id])
        if history_id in lifecycle:
            assert actual["recordStatus"] == "superseded-reviewed-record" and actual["replacedByPollId"] == lifecycle[history_id]
            actual["recordStatus"] = original["recordStatus"]
            actual.pop("replacedByPollId")
        assert actual == original, ("Prior raw historical observation changed",history_id)
    source_checks = {}
    for pid,spec in specs.items():
        expected = EXPECTED[pid]
        candidate_path = ROOT / spec["candidatePath"]
        candidate,poll = read(candidate_path),active[pid]
        folder = PUBLIC / expected["folder"]
        assert spec["folder"] == expected["folder"]
        assert sha(candidate_path) == spec["candidateSha256"] == sha(folder / "frozen-reviewed-candidate.json")
        for key,value in candidate.items():
            if key not in {"secondarySourceUrls","sourceDocument","validationSourceUrl","unpublishedPercentagePartyIds"}:
                assert poll[key] == value, ("Original source field changed",pid,key)
        for key,value in candidate["sourceDocument"].items():
            if key not in {"archiveUrl","extractArchiveUrl","originalGraphicArchiveUrl","originalGraphicArchiveUrls"}:
                assert poll["sourceDocument"][key] == value, ("Original source document field changed",pid,key)
        assert poll["id"] == expected["id"] and poll["date"] == expected["date"]
        assert poll["date"] <= DAY and poll["replacesPollId"] == expected["oldId"]
        assert poll.get("sampleSize") == candidate.get("sampleSize")
        assert spec["strictEligible"] is (candidate.get("fieldworkVerified") is True and candidate.get("fieldworkStart", "") >= "2026-09-09")
        assert poll["seats"] == spec["expectedSeats"] and sum(poll["seats"].values()) == poll["seatTotal"] == 120
        assert poll["reportedPercentages"] == spec["expectedReportedPercentages"]
        published_aggregate_other_check(poll, candidate_path)
        assert poll["sourceBlocSeats"] == spec["expectedSourceBlocSeats"] and sum(poll["sourceBlocSeats"].values()) == 120
        assert read(folder / "reviewed-poll.json") == read(folder / "ingested-poll.json") == poll
        historical = dict(archive["history_"+expected["id"]+"_current"])
        for key in ["sourcePollId","archiveSourceUrl","recordStatus"]:
            historical.pop(key)
        historical["id"] = poll["id"]
        assert historical == poll
        assert sha(folder / poll["sourceDocument"]["fileName"]) == poll["sourceDocument"]["sha256"]
        assert sha(folder / poll["sourceDocument"]["extractFileName"]) == poll["sourceDocument"]["extractSha256"]
        for evidence in spec["publicFiles"]:
            assert Path(evidence["publicName"]).suffix.lower() not in {".html", ".htm"}
            assert "web-reader" not in evidence["publicName"] and "sourceWeb" not in evidence["publicName"]
            assert sha(folder / evidence["publicName"]) == sha(ROOT / evidence["sourcePath"]) == evidence["sha256"]
        assert set(poll.get("publishedBounds",{})).isdisjoint(poll["reportedPercentages"])
        assert set(poll.get("modelOnlyPercentageIds",[])).isdisjoint(poll["reportedPercentages"])
        report = next(p for p in documents["reports"] if p["pollsterId"] == pid and p["includedInCurrentModel"])
        assert report["sampleSize"] == poll["sampleSize"] and report["date"] == expected["date"]
        for row in report["tables"][0]["rows"]:
            if row["partyId"]:
                assert row["rawPct"] == poll["reportedPercentages"].get(row["partyId"])
                assert row["seats"] == poll["seats"].get(row["partyId"])
        assert [row for row in report["tables"][0]["rows"] if row["partyId"] is None] == [
            {"party": p["name"], "partyId": None, "seats": p.get("seats"), "rawPct": p.get("pct"), "publishedBounds": None}
            for p in poll.get("unmodelledNamedParties", [])], "Named small-party facts must remain visible and separate"
        assert "other" not in poll["percentages"] or "other" in poll["reportedPercentages"] or "other" in poll.get("modelOnlyPercentageIds", []), "Other requires published proof or explicit model-only named-list mapping"
        for party in read(ROOT / "data/parties.json"):
            if party.get("ballot") and party["id"] not in candidate["seats"]:
                assert party["id"] not in poll["seats"]
                assert next(r for r in report["tables"][0]["rows"] if r["partyId"] == party["id"])["seats"] is None
        archived_names = {e["publicName"] for e in spec["publicFiles"]}
        doc = poll["sourceDocument"]
        if doc.get("originalGraphicArchiveUrl"):
            assert doc["originalGraphicFileName"] in archived_names
            assert sha(folder / doc["originalGraphicFileName"]) == doc["originalGraphicSha256"]
        coverage = next(p for p in history["coverage"] if p["pollsterId"] == pid)
        assert coverage["lastDate"] == expected["date"] and coverage["pollCount"] == sum(p["pollsterId"] == pid for p in history["polls"])
        source_checks[pid] = {"candidateSha256":spec["candidateSha256"],"sampleSize":poll.get("sampleSize"),
            "sourceBlocSeats":poll["sourceBlocSeats"],"publicationDate":poll["date"],"fieldworkStart":poll.get("fieldworkStart"),
            "fieldworkEnd":poll.get("fieldworkEnd"),"strictEligible":spec["strictEligible"]}
    assert current["documentReview"] == documents
    for original in old_documents["reports"]:
        revised = next(p for p in documents["reports"] if p["id"] == original["id"])
        allowed = {"includedInCurrentModel","statusLabel"} if original.get("pollsterId") in specs and original.get("includedInCurrentModel") else set()
        assert {k:v for k,v in revised.items() if k not in allowed} == {k:v for k,v in original.items() if k not in allowed}
    for original in old_sources["sources"]:
        if original.get("id") in specs:
            revised = next(p for p in sources["sources"] if p.get("url") == original["url"] and not p.get("id"))
            assert {k:v for k,v in revised.items() if k not in {"id","type","notes"}} == {k:v for k,v in original.items() if k not in {"id","type","notes"}}
            assert revised["notes"][:-1] == original["notes"]
        else:
            assert original in sources["sources"], ("Unrelated source changed",original.get("url"))
    all_audits,audit_hashes = [],{}
    prior_candidate_count = 0
    for name in ["lazar-fieldwork.json","n12-kan-c13-fieldwork.json","c14-i24-fieldwork.json","c16-tatika-fieldwork.json","new-unverified-fieldwork-2026-09-30.json"]:
        relative = "artifacts/strict-post-close/"+name
        old,new = read(BEFORE / relative),read(ROOT / relative)
        prior_rows,rows = old.get("rows",old.get("polls",[])),new.get("rows",new.get("polls",[]))
        prior_candidate_count += len(prior_rows)
        assert all(p in rows for p in prior_rows), ("Previous fieldwork decision changed",name)
        if relative not in FILES:
            assert sha(ROOT / relative) == sha(BEFORE / relative)
        audit_hashes[relative] = sha(ROOT / relative)
        all_audits.extend(rows)
    audited = index(all_audits,"pollId")
    assert len(audited) == receipt["expectedStrictCandidates"] == prior_candidate_count + len(specs)
    assert set(audited) == {p["id"] for p in history["polls"] if p["date"] >= "2026-09-09"}
    eligible = [p for p in all_audits if p.get("eligibleStrict",p.get("includeInStrictPostClose",False))]
    default = [p for p in eligible if p["pollsterId"] != "next_data"]
    assert len(eligible) == receipt["expectedStrictEligible"]
    assert len(default) == receipt["expectedStrictWithoutChannel14"]
    assert len(all_audits)-len(eligible) == receipt["expectedUnverifiedFieldwork"]
    for pid,spec in specs.items():
        row = audited["history_"+EXPECTED[pid]["id"]+"_current"]
        assert row["eligibleStrict"] is spec["strictEligible"]
        relevant = read(ROOT / ALLOWED[pid]["audit"])
        relevant_rows = relevant.get("rows", relevant.get("polls", []))
        assert relevant["auditDate"] == DAY and row in relevant_rows
        assert row["evidence"] == spec.get("fieldworkEvidence", [])
        for evidence in row["evidence"]:
            assert sha(ROOT / evidence["file"]) == evidence["sha256"]
        assert row["publicationDate"] == EXPECTED[pid]["date"]
        assert row["fieldworkStart"] == active[pid].get("fieldworkStart") and row["fieldworkEnd"] == active[pid].get("fieldworkEnd")
        if spec["strictEligible"]:
            assert "2026-09-09" <= row["fieldworkStart"] <= row["fieldworkEnd"] <= row["publicationDate"] <= DAY
    receipt_out = {"status":"PASS","asOf":DAY,"baselineAsOf":BASELINE,"activePollCount":len(active),"historyPollCount":len(archive),
        "newPollCount":len(specs),"sourceChecks":source_checks,
        "fullStrict":{"candidates":len(all_audits),"polls":len(eligible),"series":len({p["pollsterId"] for p in eligible}),
            "deltas":len(eligible)-len({p["pollsterId"] for p in eligible}),"unknownFieldworkExcluded":len(all_audits)-len(eligible)},
        "defaultWithoutChannel14":{"polls":len(default),"series":len({p["pollsterId"] for p in default}),
            "deltas":len(default)-len({p["pollsterId"] for p in default})},
        "checkpointManifestSha256":sha(BEFORE / "manifest.json"),"sourcePlanSha256":sha(ART / "source-plan.json"),
        "ingestionReceiptSha256":sha(ART / "ingestion-receipt.json"),"auditHashes":audit_hashes,
        "authorFilesVerified":len(manifest["authorContentHashes"]),"protectedRuntimeFilesVerified":len(manifest["protectedRuntimeHashes"]),
        "frozenEvidenceFilesPreserved":len(manifest["frozenEvidenceHashes"]),"conditionalAndArtisticFilesPreserved":len(manifest["frozenConditionalAndArtisticHashes"]),
        "reviewedPythonIntegerHelpersPreserved":manifest["reviewedExactHelpers"],"historicalWeightsUnchanged":True,
        "previousRawHistoryPreserved":True,"publicationAndAuditDatesSeparated":True,"noNumericalOrDashboardMutation":True,
        "validatorSha256":sha(Path(__file__))}
    immutable_write(ART / "ingestion-validation.json",receipt_out)
    print(json.dumps(receipt_out,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
