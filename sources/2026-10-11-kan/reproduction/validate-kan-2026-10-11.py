"""Independent count/preservation validation for the Oct11 ingestion.

Read-only canonical checks; writes a dated receipt only. Does not run trends.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-11"
BEFORE = ART / "before"
PUBLIC = ROOT / "github-pages/sources/2026-10-11-kan"
DAY = "2026-10-11"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def index(rows, key):
    result = {row[key]: row for row in rows}
    assert len(result) == len(rows), ("duplicate", key)
    return result


spec = importlib.util.spec_from_file_location("kan_oct11_ingester", ROOT / "scripts/ingest-kan-2026-10-11.py")
ingester = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingester)
manifest = ingester.frozen_check()
candidate, hashes = ingester.candidate_check()
revision = (ART / "ingestion-receipt-model-only-r1.json").exists()
receipt_path = ART / ("ingestion-receipt-model-only-r1.json" if revision else "ingestion-receipt.json")
receipt = read(receipt_path)
assert receipt["status"] == "PASS" and receipt["asOf"] == DAY
assert receipt["candidateSha256"] == hashes["reviewed-poll.json"]
assert receipt["checkpointManifestSha256"] == sha(BEFORE / "manifest.json")
assert receipt["preflightSha256"] == sha(ART / "ingestion-preflight.json")
for rel, digest in receipt["changedCanonicalFiles"].items():
    assert sha(ROOT / rel) == digest, rel
for name, digest in receipt["publicEvidenceFiles"].items():
    assert sha(PUBLIC / name) == digest, name
assert sha(PUBLIC / "frozen-reviewed-candidate.json") == hashes["reviewed-poll.json"]
for name, digest in hashes.items():
    if name != "reviewed-poll.json":
        assert sha(PUBLIC / name) == digest, name

paths = ingester.MUTABLE
current, history, sources, documents, audit = [read(ROOT / rel) for rel in paths]
old_current, old_history, old_sources, old_documents, old_audit = [read(BEFORE / rel) for rel in paths]
assert current["asOf"] == history["asOf"] == sources["asOf"] == documents["checkedAt"] == audit["auditedAt"] == DAY
active = index(current["polls"], "pollsterId")
old_active = index(old_current["polls"], "pollsterId")
assert len(active) == len(old_active) == 8 and active.keys() == old_active.keys()
for pid in active:
    if pid != "kantar":
        assert active[pid] == old_active[pid], ("other-active-institute-changed", pid)
poll = active["kantar"]
expected_poll = ingester.archive_links(candidate)
if revision:
    expected_poll["modelOnlyPercentageIds"] = ["other"]
    expected_poll["validationSourceUrl"] = ingester.PUBLIC_BASE + "model-only-r1/reviewed-poll.json"
    expected_poll["secondarySourceUrls"] += [ingester.PUBLIC_BASE + "model-only-r1/reviewed-poll.json", ingester.PUBLIC_BASE + "model-only-r1/revision-receipt.json"]
    for rel, digest in receipt["initialPublicEvidenceHashesPreserved"].items():
        assert sha(PUBLIC / rel) == digest, rel
assert poll == expected_poll
record_folder = PUBLIC / "model-only-r1" if revision else PUBLIC
assert poll == read(record_folder / "reviewed-poll.json") == read(record_folder / "ingested-poll.json")
assert poll["id"] == ingester.ID and poll["replacesPollId"] == old_active["kantar"]["id"] == ingester.OLD_ID
current_metadata_allowed = {"asOf", "version", "updateNote", "metadataUpdatedAt", "notes", "documentReview", "polls"}
assert {k: v for k, v in current.items() if k not in current_metadata_allowed} == {k: v for k, v in old_current.items() if k not in current_metadata_allowed}

archive = index(history["polls"], "id")
old_archive = index(old_history["polls"], "id")
assert len(archive) == 115 and len(old_archive) == 114
assert set(archive) - set(old_archive) == {ingester.HISTORY_ID}
assert len({(row["pollsterId"], row["date"]) for row in archive.values()}) == len(archive)
previous_id = next(row["id"] for row in old_archive.values() if row.get("sourcePollId") == ingester.OLD_ID)
for poll_id, old in old_archive.items():
    expected = dict(old)
    if poll_id == previous_id:
        expected.update(recordStatus="superseded-reviewed-record", replacedByPollId=ingester.ID)
    assert archive[poll_id] == expected, ("historical-observation-changed", poll_id)
new = dict(poll)
new.update(id=ingester.HISTORY_ID, sourcePollId=ingester.ID, archiveSourceUrl=poll["validationSourceUrl"], recordStatus="current-reviewed-record")
assert archive[ingester.HISTORY_ID] == new
for pid, coverage in index(history["coverage"], "pollsterId").items():
    if pid != "kantar":
        assert coverage == index(old_history["coverage"], "pollsterId")[pid]
    else:
        rows = [p for p in archive.values() if p["pollsterId"] == pid]
        assert coverage["pollCount"] == len(rows) == 20
        assert coverage["firstDate"] == min(r["date"] for r in rows) and coverage["lastDate"] == DAY
assert {k: v for k, v in history.items() if k not in {"asOf", "polls", "coverage", "notes", "supplementalSourceUrls"}} == {k: v for k, v in old_history.items() if k not in {"asOf", "polls", "coverage", "notes", "supplementalSourceUrls"}}
assert history["notes"][:-1] == old_history.get("notes", [])
assert set(old_history.get("supplementalSourceUrls", [])).issubset(history["supplementalSourceUrls"])

old_source_kantar = next(row for row in old_sources["sources"] if row.get("id") == "kantar")
assert len(sources["sources"]) == len(old_sources["sources"]) + 1
for before, after in zip(old_sources["sources"], sources["sources"][:-1]):
    expected = dict(before)
    if before == old_source_kantar:
        expected.pop("id")
        expected["type"] = "historical-poll-source"
        expected["notes"] = [*before.get("notes", []), "הוחלף בסקר כאן מ־11.10.2026; המקור נשמר בהיסטוריה."]
    assert after == expected
assert len([row for row in sources["sources"] if row.get("id") == "kantar"]) == 1
assert sources["sources"][-1]["url"] == poll["sourceUrl"]
assert read(ART / "previous-source-check.json") == old_sources["latestSourceCheck"]
assert sources["latestSourceCheck"]["checks"] == poll["sourceAccessSummary"]
assert sum(row.get("access") == "blocked" for row in sources["latestSourceCheck"]["checks"]) == 4

old_reports, reports = index(old_documents["reports"], "id"), index(documents["reports"], "id")
assert set(reports) - set(old_reports) == {"kantar-2026-10-11"}
for report_id, old in old_reports.items():
    expected = dict(old)
    if old.get("pollsterId") == "kantar" and old.get("includedInCurrentModel"):
        expected.update(includedInCurrentModel=False, statusLabel="הוחלף בסקר כאן מ־11.10; נשמר בהיסטוריה")
    assert reports[report_id] == expected, report_id
assert len([r for r in reports.values() if r.get("includedInCurrentModel")]) == 8
assert [r["date"] for r in reports.values() if r.get("pollsterId") == "kantar" and r.get("includedInCurrentModel")] == [DAY]
assert current["documentReview"] == documents == read(PUBLIC / "extracted-surveys.json")
raw_rows = reports["kantar-2026-10-11"]["tables"][0]["rows"]
party_rows = {r["partyId"]: r for r in raw_rows if r["partyId"]}
assert party_rows["winter"]["seats"] == 4 and party_rows["winter"]["rawPct"] is None
for pid in ["noam", "israel_first"]:
    assert party_rows[pid]["seats"] is None and party_rows[pid]["rawPct"] is None
assert [r["rawPct"] for r in raw_rows if r["partyId"] is None] == [.7, .5]
assert poll["reportedPercentages"] == {"gantz": .9, "haredi_public": .9} and "other" not in poll["reportedPercentages"]
assert poll["percentages"]["other"] == sum(r["pct"] for r in poll["unmodelledNamedParties"])

audit_rows, old_audit_rows = index(audit["rows"], "pollId"), index(old_audit["rows"], "pollId")
assert set(audit_rows) - set(old_audit_rows) == {ingester.HISTORY_ID}
assert all(audit_rows[pid] == row for pid, row in old_audit_rows.items())
added = audit_rows[ingester.HISTORY_ID]
assert added["fieldworkStart"] is added["fieldworkEnd"] is None
assert added["eligibleStrict"] is False and added["includeInStrictPostClose"] is False
assert sum(r["eligibleStrict"] for r in audit["rows"]) == sum(r["eligibleStrict"] for r in old_audit["rows"])
assert audit["counts"] == {"records": len(audit_rows), "verifiedEligible": sum(r["eligibleStrict"] for r in audit["rows"]), "unknown": sum(not r["eligibleStrict"] for r in audit["rows"])}
for item in added["evidence"]:
    assert sha(ROOT / item["file"]) == item["sha256"]
assert audit["limitations"][:-1] == old_audit["limitations"]
for key in ["closureDate", "closureDateSource", "criterion", "scope"]:
    assert audit[key] == old_audit[key]
for name in ["data/calibration.json", "data/weight-presets.json", "data/parties.json"]:
    assert sha(ROOT / name) == manifest["files"][name]
for url in [poll["validationSourceUrl"], poll["sourceDocument"]["archiveUrl"], *poll["secondarySourceUrls"]]:
    if url.startswith(ingester.PUBLIC_BASE):
        assert (PUBLIC / url.removeprefix(ingester.PUBLIC_BASE)).is_file(), url
assert not any("2026-10-11/kan-source" in url for url in poll["secondarySourceUrls"])
assert not any("telegram" in path.name.lower() or "gilead" in path.name.lower() or path.suffix in {".mp4", ".docx", ".pdf"} for path in PUBLIC.iterdir())
assert sha(PUBLIC / "source-extract.txt") == poll["sourceDocument"]["extractSha256"]

result = {"status": "PASS", "asOf": DAY, "activeInstituteCount": len(active), "historyCount": len(archive),
          "newObservationCount": 1, "updatedInstitute": "kantar", "replacesPollId": ingester.OLD_ID,
          "otherActiveInstitutesExactlyPreserved": True, "existingHistoricalObservationsExactlyPreservedExceptSupersededStatus": True,
          "historicalWeightsAndPartyCataloguePreserved": True, "sourceEvidenceHashesMatch": True,
          "checkpointUnchanged": True, "originalKanMethodologySuccessfullyRead": False,
          "unverifiedFieldworkExcluded": True, "strictEligibleCountsUnchanged": True,
          "fieldworkAuditCounts": audit["counts"], "rawMissingnessPreserved": True,
          "winterVoteShareMissing": True, "noamAndIsraelFirstMissing": True,
          "derivedOtherPct": 1.2, "derivedOtherNotLabeledRaw": True,
          "publicArchiveLinksResolveWithinPackage": True, "privateGileadMaterialNotPublished": True,
          **({"modelOnlyPercentageIds": poll["modelOnlyPercentageIds"], "revisionId": "model-only-r1"} if revision else {}),
          "candidateSha256": hashes["reviewed-poll.json"], "ingestionReceiptSha256": sha(receipt_path),
          "canonicalHashes": {rel: sha(ROOT / rel) for rel in paths}}
ingester.write_new(ART / ("ingestion-validation-model-only-r1.json" if revision else "ingestion-validation.json"), result)
ingester.write_new(record_folder / "ingestion-validation.json", result)
print(json.dumps(result, ensure_ascii=False, indent=2))
