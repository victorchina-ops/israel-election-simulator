"""Ingest one reviewed Kan/Kantar observation after an immutable preflight.

Only the four canonical survey files and one fieldwork audit are changed.
The republished graphic is verified; inaccessible original methodology stays
missing. This script does not build numerical trends, the app or index.html.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY, BEFORE = "2026-10-11", "2026-10-10"
ART = ROOT / "artifacts/poll-checks/2026-10-11"
CHECKPOINT = ART / "before"
EVIDENCE = ART / "kan-source"
PUBLIC = ROOT / "github-pages/sources/2026-10-11-kan"
PUBLIC_BASE = "https://victorchina-ops.github.io/israel-election-simulator/sources/2026-10-11-kan/"
ID, HISTORY_ID, OLD_ID = "kantar_2026-10-11", "history_kantar_2026-10-11_current", "kantar_2026-10-08"
MUTABLE = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
           "data/survey-documents-2026-09-14.json", "artifacts/strict-post-close/n12-kan-c13-fieldwork.json"]
SAFE_FILES = ["israelpolls-graphic.jpg", "israelpolls-history-graphic.png",
              "israelpolls-new-post.html", "israelpolls-new-post.txt",
              "israelpolls-history-post.html", "israelpolls-history-post.txt",
              "israelpolls.html", "israelpolls.txt", "reviewed-poll.json",
              "verification-summary.json", "index-network-receipts.json",
              "social-receipts.json", "media-history-receipts.json"]
SEATS = {"yashar": 22, "likud": 20, "beyachad": 12, "otzma": 9, "democrats": 8,
         "yisrael_beiteinu": 8, "utj": 8, "joint": 8, "shas": 7, "rz_zehut": 5,
         "raam": 5, "winter": 4, "hendel": 4, "gantz": 0, "haredi_public": 0}
UNKNOWN_FIELDS = ["fieldworkStart", "fieldworkEnd", "publicationTime", "publishedAt",
                  "invitedSampleSize", "initialSampleSize", "reportedMarginOfErrorPct",
                  "reportedMarginOfErrorConfidencePct", "population", "samplingMethod",
                  "panelProvider", "undecidedPct", "percentageDenominator"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_new(path, value):
    content = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == content, f"Refuse changed dated evidence: {path}"
    else:
        path.write_bytes(content)


def frozen_check():
    manifest = read(CHECKPOINT / "manifest.json")
    assert manifest["baselineAsOf"] == BEFORE and manifest["updateDate"] == DAY
    assert manifest["activePollCount"] == 8 and manifest["historyPollCount"] == 114
    for rel, digest in manifest["files"].items():
        assert sha(CHECKPOINT / rel) == digest, f"Frozen checkpoint mismatch: {rel}"
    for category in ["authorContentHashes", "frozenEvidenceHashes"]:
        for rel, digest in manifest[category].items():
            assert sha(ROOT / rel) == digest, f"Existing evidence/author content changed: {rel}"
    return manifest


def candidate_check():
    candidate = read(EVIDENCE / "reviewed-poll.json")
    verification = read(EVIDENCE / "verification-summary.json")
    assert candidate["id"] == ID and candidate["pollsterId"] == "kantar"
    assert candidate["date"] == DAY and candidate["replacesPollId"] == OLD_ID
    assert candidate["seats"] == SEATS and candidate["seatTotal"] == sum(SEATS.values()) == 120
    assert candidate["sourceBlocSeats"] == {"coalition": 53, "opposition": 50, "arab_parties": 13, "hendel": 4}
    assert sum(candidate["sourceBlocSeats"].values()) == 120
    assert candidate["reportedPercentages"] == {"gantz": .9, "haredi_public": .9}
    assert candidate["percentages"] == {"gantz": .9, "haredi_public": .9, "other": 1.2}
    assert candidate["sampleSize"] == 554
    assert all(candidate[key] is None for key in UNKNOWN_FIELDS)
    assert "winter" not in candidate["reportedPercentages"]
    assert "noam" not in candidate["seats"] and "noam" not in candidate["percentages"]
    assert "israel_first" not in candidate["seats"] and "israel_first" not in candidate["percentages"]
    named = candidate["unmodelledNamedParties"]
    assert [row["pct"] for row in named] == [.7, .5]
    assert all(row["mappedTo"] == "other" and row["seats"] == 0 for row in named)
    assert abs(sum(row["pct"] for row in named) - candidate["percentages"]["other"]) < 1e-12
    assert candidate["knownPercentageSum"] == candidate["originalCoveragePct"] == 3.0
    assert candidate["sourceTier"] == "republished-publisher-graphic"
    assert candidate["sourceDocument"]["primaryPublicationVerified"] is False
    assert sha(EVIDENCE / candidate["sourceDocument"]["fileName"]) == candidate["sourceDocument"]["sha256"]
    assert verification["poll"] == ID and verification["strictEligible"] is False
    for name, digest in verification["sourceHashes"].items():
        assert Path(name).name == name and sha(EVIDENCE / name) == digest, name
    for name in SAFE_FILES:
        assert (EVIDENCE / name).is_file(), name
    return candidate, {name: sha(EVIDENCE / name) for name in SAFE_FILES}


def preflight():
    manifest = frozen_check()
    candidate, source_hashes = candidate_check()
    for rel in MUTABLE:
        assert sha(ROOT / rel) == manifest["files"][rel], f"Canonical baseline changed: {rel}"
    current, history = [read(ROOT / f"data/{name}.json") for name in ["current-polls", "poll-history"]]
    assert current["asOf"] == history["asOf"] == BEFORE
    assert len(current["polls"]) == len({p["pollsterId"] for p in current["polls"]}) == 8
    assert len(history["polls"]) == len({(p["pollsterId"], p["date"]) for p in history["polls"]}) == 114
    assert len({p["id"] for p in history["polls"]}) == 114
    assert not any(p["pollsterId"] == "kantar" and p["date"] == DAY for p in history["polls"])
    assert [p["id"] for p in current["polls"] if p["pollsterId"] == "kantar"] == [OLD_ID]
    assert len([p for p in history["polls"] if p.get("sourcePollId") == OLD_ID]) == 1
    assert not PUBLIC.exists(), "Do not overwrite an existing evidence release"
    return {"status": "PASS", "phase": "preflight", "asOf": DAY, "baselineAsOf": BEFORE,
            "candidateId": ID, "replacesPollId": OLD_ID, "expectedCurrentCount": 8,
            "expectedHistoryCount": 115, "strictEligible": False,
            "checkpointManifestSha256": sha(CHECKPOINT / "manifest.json"),
            "inputHashes": {rel: sha(ROOT / rel) for rel in MUTABLE},
            "sourceHashes": source_hashes, "sourceCheck": "republished-graphic-and-history-table-visually-reviewed",
            "originalKanMethodologySuccessfullyRead": False,
            "missingFieldworkImputed": False, "derivedOtherPct": 1.2,
            "publicRelativePath": PUBLIC.relative_to(ROOT / "github-pages").as_posix()}


def archive_links(candidate):
    poll = copy.deepcopy(candidate)
    poll["secondarySourceUrls"] = [url for url in poll["secondarySourceUrls"]
                                  if not url.startswith("https://victorchina-ops.github.io/")]
    poll["secondarySourceUrls"] += [PUBLIC_BASE + name for name in SAFE_FILES]
    poll["secondarySourceUrls"].append(PUBLIC_BASE + "source-extract.txt")
    poll["validationSourceUrl"] = PUBLIC_BASE + "reviewed-poll.json"
    poll["sourceDocument"]["archiveUrl"] = PUBLIC_BASE + poll["sourceDocument"]["fileName"]
    poll["sourceDocument"].update(extractFileName="source-extract.txt",
                                  extractSha256=hashlib.sha256(extract_text(poll).encode("utf-8")).hexdigest())
    poll["notes"] = [
        "סקר כאן חדשות / קנטאר מ־11.10.2026, במדגם של 554 נשאלים כפי שמופיע בגרפיקה. מחליף רק את סקר קנטאר / ישראל היום מ־8.10 בשקלול הפעיל; שתי התצפיות נשמרות בהיסטוריה.",
        "המנדטים, המדגם ותאריך הסקר נבדקו בגרפיקה של כאן שפרסם IsraelPolls; אחוזים מתחת לחסימה נבדקו בעמודת 11.10 בטבלה ההיסטורית. אתר כאן ומדורי החדשות, הפוליטיקה והסקרים החזירו HTTP403; הפרסום המקורי המלא והמתודולוגיה לא נקראו בהצלחה.",
        "לא אומתו תאריכי עבודת השדה, השיטה, האוכלוסייה, מספר המוזמנים, טעות הדגימה ושיעור המתלבטים; השדות נשארים חסרים. הסקר אינו נוסף למבחני המגמה המחמירים עד אימות מועדי האיסוף.",
        "עמך ישראל מקבלת 4 מנדטים, אך אחוז התמיכה שלה לא פורסם במקורות שנבדקו; אין להעתיק את 2.9% או 2.6% מהסקרים הקודמים. אחוזי הרשימות העוברות משוחזרים במודל ואינם אחוזי משיבים שפורסמו.",
        "בטבלת IsraelPolls: כחול לבן 0.9%, הציבור החרדי 0.9%, צבע שחור 0.7% ואח״י 0.5%. שתי האחרונות נשמרות בשם המקור; 1.2% שלהן הוא סכום מחושב לרכיב אחרים במודל, לא אחוז מצרפי שפורסם. נעם וישראל תחילה נשארות חסרות.",
        "חלוקת המקור: גוש נתניהו 53 כולל וינטר, גוש איזנקוט 50, ערביות 13 והנדל־זליכה 4. שיוך הגושים באתר נתון לבחירת המשתמש.",
        "חותמות הפרסום החוזר ב־IsraelPolls נשמרות בנפרד; אינן תאריכי עבודת שדה או שעת הפרסום הראשונה של כאן.",
    ]
    return poll


def extract_text(poll):
    return ("Kan/Kantar published observation 2026-10-11.\n"
            "Source tier: Kan broadcast graphic republished by IsraelPolls; original Kan webpages HTTP403.\n"
            "Published seats and n554 visually verified; date11.10 printed on graphic and latest history-table column.\n"
            "Graphic post: " + poll["sourceUrl"] + "\n"
            "Historical table: https://x.com/IsraelPolls/status/2109340303660552420\n"
            "Seats: " + json.dumps(poll["seats"], ensure_ascii=False) + "\n"
            "Published below-threshold percentages: Gantz0.9; HarediPublic0.9; TzevaShahor0.7; Ahi0.5.\n"
            "Derived modelother1.2 = namedTzevaShahor0.7 + namedAhi0.5; not a published aggregate.\n"
            "Winter4seats but vote percentage unpublished. Noam/IsraelFirst absent: missing, not zero.\n"
            "Fieldwork, collection method, population, invited n, margin, confidence, undecided share and denominator unverified.\n"
            "Strict post-closure significance: excluded until verified fieldwork dates; publication/repost dates not imputed.\n"
            "Source blocs: Netanyahu53 includingWinter; opposition50; Arab13; Hendel4.\n"
            "Repost: " + poll["sourceRepostPublishedAtIsrael"] + "; table repost: " + poll["sourceHistoryRepostPublishedAtIsrael"] + ".\n")


def proposed_files():
    candidate, _ = candidate_check()
    poll = archive_links(candidate)
    current, history, sources, review, audit = [read(ROOT / rel) for rel in MUTABLE]
    parties = read(ROOT / "data/parties.json")
    current["polls"] = [poll if p["pollsterId"] == "kantar" else p for p in current["polls"]]
    old = next(p for p in history["polls"] if p.get("sourcePollId") == OLD_ID)
    old.update(recordStatus="superseded-reviewed-record", replacedByPollId=ID)
    historical = copy.deepcopy(poll)
    historical.update(id=HISTORY_ID, sourcePollId=ID, archiveSourceUrl=poll["validationSourceUrl"], recordStatus="current-reviewed-record")
    history["polls"].append(historical)
    history["polls"].sort(key=lambda p: (p["date"], p["pollsterId"], p["id"]))
    rows = [p for p in history["polls"] if p["pollsterId"] == "kantar"]
    coverage = next(p for p in history["coverage"] if p["pollsterId"] == "kantar")
    coverage.update(pollCount=len(rows), firstDate=min(p["date"] for p in rows), lastDate=DAY,
                    primarySourceUrl=poll["sourceUrl"], validationSourceUrl=poll["validationSourceUrl"],
                    validationNote="גרפיקה וטבלה חוזרות של כאן ב־IsraelPolls נבדקו; המקור המקורי המלא חסום, ומועדי האיסוף והשיטה נשארים חסרים. אין להסיק פרטי שדה מתאריך הפרסום.")
    history["supplementalSourceUrls"] = list(dict.fromkeys([*history.get("supplementalSourceUrls", []), poll["sourceUrl"], *poll["secondarySourceUrls"]]))
    old_reports = [r for r in review["reports"] if r.get("pollsterId") == "kantar" and r.get("includedInCurrentModel")]
    assert len(old_reports) == 1 and old_reports[0]["date"] == "2026-10-08"
    old_reports[0].update(includedInCurrentModel=False, statusLabel="הוחלף בסקר כאן מ־11.10; נשמר בהיסטוריה")
    table_rows = [{"party": p["name"], "partyId": p["id"], "seats": poll["seats"].get(p["id"]),
                   "rawPct": poll["reportedPercentages"].get(p["id"])} for p in parties if p.get("ballot") is not False]
    table_rows += [{"party": p["name"], "partyId": None, "seats": p["seats"], "rawPct": p["pct"]} for p in poll["unmodelledNamedParties"]]
    report = {"id": "kantar-2026-10-11", "pollsterId": "kantar", "fileName": poll["sourceDocument"]["fileName"],
              "publisher": poll["publisher"], "pollster": poll["pollster"], "date": DAY,
              **{key: copy.deepcopy(poll.get(key)) for key in ["dateKind", "fieldworkStart", "fieldworkEnd", "sampleSize", "initialSampleSize", "invitedSampleSize", "sampleSizeSourceUrl", "samplingMethod", "population", "panelProvider", "reportedMarginOfErrorPct", "reportedMarginOfErrorConfidencePct", "publicationTime", "undecidedPct", "sourceRepostPublishedAtIsrael"]},
              "includedInCurrentModel": True, "statusLabel": "הסקר הפעיל — גרפיקה חוזרת אומתה; פרטי שדה ושיטה חסרים",
              "summary": " ".join(poll["notes"]), "sourceUrl": poll["sourceDocument"]["archiveUrl"],
              "primarySourceUrl": poll["sourceUrl"], "sourceTier": poll["sourceTier"],
              "sourceKind": poll["sourceDocument"]["kind"], "sourceSha256": poll["sourceDocument"]["sha256"],
              "tables": [{"label": "המנדטים והאחוזים שפורסמו — תא ריק משמעו נתון חסר", "page": 1,
                          "columns": [{"key": "party", "label": "מפלגה", "type": "text"}, {"key": "seats", "label": "מנדטים", "type": "seats"}, {"key": "rawPct", "label": "אחוז שפורסם", "type": "percent"}], "rows": table_rows}]}
    review["reports"].insert(0, report)
    active_sources = [s for s in sources["sources"] if s.get("id") == "kantar"]
    assert len(active_sources) == 1
    active_sources[0].pop("id")
    active_sources[0].update(type="historical-poll-source")
    active_sources[0].setdefault("notes", []).append("הוחלף בסקר כאן מ־11.10.2026; המקור נשמר בהיסטוריה.")
    sources["sources"].append({"id": "kantar", "title": "כאן חדשות / קנטאר — דודי חסיד — 11.10.2026", "url": poll["sourceUrl"], "type": "republished-publisher-graphic", "accessedAt": DAY,
                               "status": "reviewed-republished-graphic-original-blocked-metadata-pending", "secondarySourceUrls": poll["secondarySourceUrls"], "notes": poll["notes"]})
    note = "נוסף סקר כאן / קנטאר מ־11.10.2026: שמונה מכונים פעילים ו־115 סקרים בהיסטוריה. הגרפיקה והטבלה ב־IsraelPolls נבדקו; המקור המקורי חסום, ומועדי האיסוף אינם מאומתים."
    current.update(asOf=DAY, version="2026-10-11.kan-kantar-v1", updateNote=note, metadataUpdatedAt=DAY,
                   notes=[note, "אחוז חסר אינו אפס; סקר חדש עם מועדי איסוף חסרים נשאר מחוץ למבחני המגמות המחמירים."])
    review.update(checkedAt=DAY, summary=note)
    current["documentReview"] = copy.deepcopy(review)
    history["asOf"] = sources["asOf"] = DAY
    history.setdefault("notes", []).append(note)
    previous_check = copy.deepcopy(sources.get("latestSourceCheck"))
    sources["latestSourceCheck"] = {"checkedAt": DAY, "sources": [s["url"] for s in poll["sourceAccessSummary"]],
                                   "checks": copy.deepcopy(poll["sourceAccessSummary"]),
                                   "limitations": copy.deepcopy(poll["limitations"]), "note": note,
                                   "sourceScanReceiptUrl": PUBLIC_BASE + "index-network-receipts.json",
                                   "previousCheckRetainedInCheckpoint": "artifacts/poll-checks/2026-10-11/before/data/sources.json"}
    # This is not an original-publisher URL: preserve the actual evidence tier.
    audited = {"pollId": HISTORY_ID, "sourcePollId": ID, "pollsterId": "kantar", "publisher": poll["publisher"], "publicationDate": DAY,
               "fieldworkStart": None, "fieldworkEnd": None, "eligibleStrict": False, "includeInStrictPostClose": False,
               "crossesClosureDate": None, "status": "unknown-fieldwork", "sampleSize": 554,
               "collectionMode": None, "marginOfErrorPct": None, "sourceUrl": poll["sourceUrl"],
               "evidence": [{"file": (EVIDENCE / name).relative_to(ROOT).as_posix(), "url": poll["sourceUrl"] if name == "israelpolls-graphic.jpg" else "https://x.com/IsraelPolls/status/2109340303660552420",
                             "kind": "republished-broadcast-graphic" if name == "israelpolls-graphic.jpg" else "republished-poll-history-table",
                             "quote": "Printed publication date11.10 and n554; no verified fieldwork interval." if name == "israelpolls-graphic.jpg" else "Latest11.10column gives seats and below-threshold percentages; no collection dates.",
                             "locator": "Graphic headline and left methodology footer" if name == "israelpolls-graphic.jpg" else "latest11.10column", "sha256": sha(EVIDENCE / name)} for name in ["israelpolls-graphic.jpg", "israelpolls-history-graphic.png"]],
               "reason": "Kan original webpages returned HTTP403. The republished broadcast graphic and history table establish the published observation, not collection dates. Both fieldwork dates remain null; no publication/repost-date imputation.",
               "accessNote": "IsraelPolls profile/posts and graphics read; original Kan home/news/politics/polls indexes blocked."}
    assert HISTORY_ID not in {r["pollId"] for r in audit["rows"]}
    audit["rows"].append(audited)
    audit["auditedAt"] = DAY
    audit["counts"] = {"records": len(audit["rows"]), "verifiedEligible": sum(r["eligibleStrict"] for r in audit["rows"]), "unknown": sum(not r["eligibleStrict"] for r in audit["rows"])}
    audit["limitations"].append("Kan11Oct published seats and n554 are verified from the republished graphic; full original methodology is blocked. Fieldwork is unknown, so this new observation remains excluded; no existing verified record is removed.")
    return dict(zip(MUTABLE, [current, history, sources, review, audit])), poll, previous_check


def apply():
    checks = preflight()
    assert read(ART / "ingestion-preflight.json") == checks, "Run --check on the unchanged inputs first"
    values, poll, previous_check = proposed_files()
    assert len(values["data/current-polls.json"]["polls"]) == 8
    assert len(values["data/poll-history.json"]["polls"]) == 115
    PUBLIC.mkdir(parents=True)
    for name in SAFE_FILES:
        target_name = "frozen-reviewed-candidate.json" if name == "reviewed-poll.json" else name
        shutil.copy2(EVIDENCE / name, PUBLIC / target_name)
        assert sha(PUBLIC / target_name) == checks["sourceHashes"][name]
    (PUBLIC / "source-extract.txt").write_bytes(extract_text(poll).encode("utf-8"))
    write_new(PUBLIC / "reviewed-poll.json", poll)
    write_new(PUBLIC / "ingested-poll.json", poll)
    for rel, value in values.items():
        (ROOT / rel).write_bytes(encoded(value))
    write_new(ART / "previous-source-check.json", previous_check)
    write_new(PUBLIC / "extracted-surveys.json", values["data/survey-documents-2026-09-14.json"])
    flat = [{"file": report["fileName"], "publisher": report["publisher"], "reportDate": report["date"],
             "fieldworkStart": report.get("fieldworkStart"), "fieldworkEnd": report.get("fieldworkEnd"), "sampleSize": report.get("sampleSize"),
             "includedInCurrentModel": report["includedInCurrentModel"], "table": table["label"], "page": table.get("page"), **row}
            for report in values["data/survey-documents-2026-09-14.json"]["reports"] for table in report.get("tables", []) for row in table.get("rows", [])]
    csv_path = ROOT / "outputs/surveys-extracted-2026-10-11.csv"
    assert not csv_path.exists()
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(key for row in flat for key in row)))
        writer.writeheader()
        writer.writerows(flat)
    shutil.copy2(csv_path, PUBLIC / csv_path.name)
    frozen_check()
    receipt = {"status": "PASS", "phase": "applied-awaiting-independent-review", "asOf": DAY, "baselineAsOf": BEFORE,
               "pollId": ID, "historyId": HISTORY_ID, "replacesPollId": OLD_ID,
               "activePollCount": 8, "historyPollCount": 115, "strictEligible": False,
               "checkpointManifestSha256": checks["checkpointManifestSha256"], "preflightSha256": sha(ART / "ingestion-preflight.json"),
               "candidateSha256": checks["sourceHashes"]["reviewed-poll.json"],
               "changedCanonicalFiles": {rel: sha(ROOT / rel) for rel in MUTABLE},
               "publicEvidenceFiles": {p.name: sha(p) for p in sorted(PUBLIC.iterdir()) if p.is_file()},
               "rawMissingnessRetained": True, "originalKanMethodologySuccessfullyRead": False,
               "noNumericalTrendsOrDashboardBuilt": True, "historicalWeightsUnchanged": True}
    write_new(ART / "ingestion-receipt.json", receipt)
    write_new(PUBLIC / "ingestion-receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ["status", "phase", "pollId", "activePollCount", "historyPollCount", "strictEligible"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.check:
        result = preflight()
        write_new(ART / "ingestion-preflight.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        apply()


if __name__ == "__main__":
    main()
