"""Package the Israel Hayom/Kantar October15 observation after independent checks.

Run only after canonical, numerical, replay, browser, visual and social receipts
pass. Existing published sources, content, runtime and artwork are immutable.
New source publication is an explicit factual/graphic allowlist: raw article
bodies, full reader exports and To120 compiled data remain local.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "github-pages"
DAY = "2026-10-15"
RELEASE = "2026-10-15-hayom"
ART = ROOT / "artifacts/poll-checks" / RELEASE
PREFIX = "sources/" + RELEASE
SOCIAL = ROOT / "outputs/social/2026-10-15-hayom"
EXPECTED = {"kantar"}
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def immutable_write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, f"Changed dated receipt: {path}"
    else:
        path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the complete package without writing any file")
    args = parser.parse_args()
    files = {}
    copies, writes = {}, {}
    checkpoint = read(ART / "before/manifest.json")
    plan = read(ART / "source-plan.json")
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY
    assert plan["publicCopyrightScopeReviewed"] is True
    assert {p["pollsterId"] for p in plan["polls"]} == EXPECTED and len(plan["polls"]) == 1
    assert not (ART / "publication-receipt.json").exists(), "Preserve the existing dated release."
    assert not (REPO / "updates" / RELEASE).exists(), "Preserve previously published social assets."

    def preserved():
        for group in ["authorContentHashes", "protectedRuntimeHashes", "frozenEvidenceHashes", "frozenConditionalAndArtisticHashes", "reviewedExactHelpers"]:
            for rel, digest in checkpoint[group].items():
                assert sha(ROOT / rel) == sha(ART / "before" / rel) == digest, (group, rel)

    def record(dest):
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(dest), "bytes": dest.stat().st_size}

    def copy(source, name):
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        dest = REPO / PREFIX / name
        assert source.is_file(), source
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), f"Dated evidence differs: {dest}"
        if dest in copies:
            assert source.read_bytes() == copies[dest].read_bytes(), ("Duplicate destination differs", dest)
        copies[dest] = source
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(source), "bytes": source.stat().st_size}

    preserved()
    for name in ["ingestion-validation.json", "strict-validation.json", "model-comparison-validation.json"]:
        assert read(ART / name)["status"] == "PASS", name
    ingestion = read(ART / "ingestion-validation.json")
    preflight = read(ART / "ingestion-preflight.json")
    ingest_receipt = read(ART / "ingestion-receipt.json")
    normalization_dir = ART / "metadata-normalization-r1"
    normalization = read(normalization_dir / "validation.json")
    normalization_receipt = read(normalization_dir / "receipt.json")
    assert normalization["status"] == "PASS" and normalization["asOf"] == DAY
    assert normalization["observationId"] == "kantar_2026-10-15"
    assert normalization["fromSourceTier"] == "original-publisher-with-user-supplied-original-report"
    assert normalization["toSourceTier"] == "original-publisher"
    for key in ["candidateAndOriginalReceiptsUnchanged", "onlyNewObservationTierFieldsChanged",
                "detailedSourceDocumentProvenanceUnchanged", "allPollValuesFieldworkWeightsAndPriorRowsUnchanged"]:
        assert normalization[key] is True
    assert normalization["receiptSha256"] == sha(normalization_dir / "receipt.json")
    assert normalization["preflightSha256"] == sha(normalization_dir / "preflight.json")
    assert normalization["ingestionReceiptSha256"] == sha(ART / "ingestion-receipt.json")
    assert normalization["ingestionValidationSha256"] == sha(ART / "ingestion-validation.json")
    assert normalization["sourcePlanSha256"] == sha(ART / "source-plan.json")
    assert normalization["candidateSha256"] == sha(ROOT / plan["polls"][0]["candidatePath"])
    assert normalization["validatorSha256"] == sha(ROOT / "scripts/validate-kantar-source-tier-2026-10-15-hayom-r1.py")
    normalized_canonical = {"data/" + name + ".json" for name in ["current-polls", "poll-history", "sources", "survey-documents-2026-09-14"]}
    normalized_public = {"hayom/reviewed-poll.json", "hayom/ingested-poll.json"}
    assert set(normalization["files"]) == normalized_canonical | {"github-pages/" + PREFIX + "/" + rel for rel in normalized_public}
    assert set(normalization["publicDerivativeChanges"]) == normalized_public
    assert normalization["publicDerivativeChanges"] == normalization_receipt["publicDerivativeChanges"]
    for row in normalization_receipt["files"]:
        rel = row["path"]
        assert normalization["files"][rel] == {key: row[key] for key in ["beforeSha256", "afterSha256"]}
        assert sha(ROOT / rel) == row["afterSha256"]
        assert sha(normalization_dir / row["beforeCopy"]) == row["beforeSha256"]
        if rel in normalized_canonical:
            assert ingest_receipt["changedCanonicalFiles"][rel] == row["beforeSha256"]
    assert sha(ART / "source-plan.json") == ingestion["sourcePlanSha256"] == preflight["sourcePlanSha256"]
    assert ingestion["activePollCount"] == checkpoint["activePollCount"] == 8
    assert ingestion["historyPollCount"] == checkpoint["historyPollCount"] + len(plan["polls"]) == 124
    full_count = ingestion["fullStrict"]["polls"]
    default_count = ingestion["defaultWithoutChannel14"]["polls"]
    unknown_count = ingestion["fullStrict"]["unknownFieldworkExcluded"]
    assert full_count == preflight["expectedStrictEligible"]
    assert default_count == preflight["expectedStrictWithoutChannel14"]
    assert unknown_count == preflight["expectedUnverifiedFieldwork"]
    corr_dir = ROOT / f"artifacts/poll-correlation/{DAY}/hayom"
    without_dir = ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/hayom"
    assert read(corr_dir / "independent-audit.json")["status"] == "passed"
    assert read(without_dir / "validation.json")["status"] == "PASS"

    reports = sorted((ART / "browser-local").glob("*/report.json"))
    assert reports, "A fresh local browser report is required."
    local = reports[-1]
    assert read(local)["status"] == "passed"
    visual = local.parent / "visual-review.json"
    visual_receipt = read(visual)
    assert visual_receipt["status"] == "passed"
    assert visual_receipt["browserReportSha256"] == sha(local)
    for rel, digest in visual_receipt["reviewedScreenshots"].items():
        assert Path(rel).name == rel and sha(local.parent / rel) == digest
    tests = (ART / "test-results-final.txt").read_text(encoding="utf-8-sig")
    assert re.search(r"fail\s+0(?:\r?\n|$)", tests)
    tests_passed = int(re.search(r"pass\s+(\d+)", tests).group(1))
    render = read(ART / "social/render-checks.json")
    assert render["status"] == "PASS" and render["visualInspectionCompleted"] is True
    assert render["asOf"] == DAY
    for key in ["output", "prompt"]:
        assert Path(render[key]).name == render[key]
        assert sha(SOCIAL / render[key]) == render[key + "Sha256"]
    if render.get("cleanupPrompt"):
        assert Path(render["cleanupPrompt"]).name == render["cleanupPrompt"]
        assert sha(SOCIAL / render["cleanupPrompt"]) == render["cleanupPromptSha256"]
    assert sha(ART / "model-comparison.json") == render["modelComparisonSha256"]
    social_files = sorted(p for p in SOCIAL.iterdir() if p.is_file())
    assert any(p.name == render["output"] and p.suffix.lower() == ".png" for p in social_files)
    assert any(p.name == "tweet.he.txt" for p in social_files)
    assert "https://victorchina-ops.github.io/israel-election-simulator/" in (SOCIAL / "tweet.he.txt").read_text(encoding="utf-8-sig")
    assert all(p.suffix.lower() in {".png", ".txt", ".json"} for p in social_files)

    snapshot = read(ROOT / "dashboard/src/data.json")
    assert snapshot["dataAsOf"] == DAY and snapshot["buildStatus"] == "complete"
    assert snapshot["features"]["chatGPT"] is False
    cfg = {r["key"]: r["value"] for r in snapshot["queries"]["model_configuration"]["rows"]}
    assert cfg["weightMode"] == "quality"
    assert all(cfg[k] is False for k in ["includeChannel14", "signalNoiseEnabled", "pollCorrelationEnabled"])
    comparison = read(ART / "model-comparison.json")
    assert comparison["status"] == "passed" and comparison["onlyControlDateDiffers"]
    assert {p["pollsterId"] for p in comparison["pollChanges"] if p["changed"]} == EXPECTED
    selected_institutes = ingestion["activePollCount"] - 1
    assert len(comparison["after"]["pollWeights"]) == selected_institutes
    assert all(p["pollsterId"] != "next_data" for p in comparison["after"]["pollWeights"])
    inputs = {r["key"]: r["value"] for r in snapshot["queries"]["model_input"]["rows"]}
    assert len(inputs["current"]["polls"]) == ingestion["activePollCount"]
    assert len(inputs["history"]["polls"]) == ingestion["historyPollCount"]
    assert inputs["current"] == read(ROOT / "data/current-polls.json")
    assert inputs["history"] == read(ROOT / "data/poll-history.json")
    assert inputs["calibration"] == {**read(ROOT / "data/calibration.json"), "pollCorrelation": read(ROOT / "data/poll-correlation.json")}
    selected = read(ROOT / "data/strict-party-trends-without-channel14.json")
    full = read(ROOT / "data/strict-party-trends.json")
    assert selected["asOf"] == full["asOf"] == DAY
    assert selected["coverage"]["pollCount"] == default_count
    assert full["coverage"]["pollCount"] == full_count

    # Ingestion already copied the explicitly reviewed original graphic/factual
    # files. Reject unaccounted files before extending this new public prefix.
    source_prefix = REPO / PREFIX
    allowed_existing = dict(ingest_receipt["publicEvidenceFiles"])
    for rel, change in normalization["publicDerivativeChanges"].items():
        assert allowed_existing[rel] == change["beforeSha256"]
        assert sha(source_prefix / rel) == change["afterSha256"]
        allowed_existing[rel] = change["afterSha256"]
    allowed_existing.update({"source-plan.json": sha(ART / "source-plan.json"), "ingestion-receipt.json": sha(ART / "ingestion-receipt.json")})
    for p in source_prefix.rglob("*"):
        if p.is_file():
            rel = p.relative_to(source_prefix).as_posix()
            assert rel in allowed_existing and sha(p) == allowed_existing[rel], ("Unreviewed public source file", rel)
            record(p)
    for spec in plan["polls"]:
        for evidence in spec["publicFiles"]:
            public = source_prefix / spec["folder"] / evidence["publicName"]
            assert sha(public) == sha(ROOT / evidence["sourcePath"]) == evidence["sha256"]

    # Explicit factual source summary only. Raw article/reader bodies stay local.
    public_source = ART / 'primary-source-public-summary.json'
    root_summary = read(public_source)
    assert root_summary['asOf'] == DAY
    assert root_summary['fullCopyrightedArticleBodiesExcluded'] is True
    copy(public_source, 'primary-source-public-summary.json')
    discovery_receipt_path = ART / 'source/source-public-freeze-receipt.json'
    discovery = read(discovery_receipt_path)
    assert discovery['status'] == 'PASS' and discovery['asOf'] == DAY
    assert 'Full authored articles' in discovery['publicScope'] and 'excluded' in discovery['publicScope']
    safe_names={item['fileName'] for item in discovery['safePublicFiles']}
    assert 'kantar-verification-summary-r1.json' in safe_names
    assert 'primary-live-index-supplement.json' in safe_names
    assert 'kantar-verification-summary.json' not in safe_names, 'Initial unsupported closure wording stays local.'
    assert all('local-only' not in name.lower() for name in safe_names), 'Reader exports and article bodies stay local.'
    for item in discovery['safePublicFiles']:
        name = item['fileName']
        assert Path(name).name == name and Path(name).suffix.lower() in {'.json','.txt','.png','.webp','.jpeg','.jpg'}
        source = discovery_receipt_path.parent / name
        assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
        copy(source, 'source-discovery/' + name)
    copy(discovery_receipt_path, 'source-discovery/source-public-freeze-receipt.json')

    compiled = (ROOT / "dashboard/dist/index.html").read_bytes()
    clean, count = re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*', b"", compiled, flags=re.I)
    assert count == 1 and b"01a0952c-a40b-7b01-b019-621f0cee2656" not in clean
    assert sha(ROOT / "dashboard/src/data.json").encode() in clean
    for p in [REPO / "index.html", ROOT / "election-simulator.html", ROOT / "artifacts/github-pages-release/index.html"]:
        writes[p] = clean
    writes[ROOT / "dashboard-snapshot.json"] = (ROOT / "dashboard/src/data.json").read_bytes()
    for name in ["current-polls", "poll-history", "sources", "parties", "calibration", "survey-documents-2026-09-14",
                 "strict-party-trends", "strict-party-trends-without-channel14", "poll-correlation"]:
        copy(ROOT / "data" / (name + ".json"), name + ".json")
    for name in ["source-plan.json", "ingestion-preflight.json", "ingestion-receipt.json", "ingestion-validation.json",
                 "strict-validation.json", "model-comparison.json", "model-comparison-validation.json", "test-results-final.txt"]:
        copy(ART / name, name)
    for name in ["preflight.json", "receipt.json", "validation.json"]:
        copy(normalization_dir / name, "metadata-normalization-r1/" + name)
    for row in normalization_receipt["files"]:
        copy(normalization_dir / row["beforeCopy"], "metadata-normalization-r1/" + row["beforeCopy"])
    # Current numerical evidence and required fieldwork audits only. The root
    # strict folder also contains old HTML/text archives, which stay local.
    canonical_numeric = ["analysis.json", "by-pollster.csv", "independent-strict-numeric-audit.json", "party-analysis.json",
        "party-by-pollster.csv", "party-independent.json", "party-overall.csv", "party-summary-he.md", "party-validation.json", "summary-he.md",
        "n12-kan-c13-fieldwork.json", "c14-i24-fieldwork.json", "c16-tatika-fieldwork.json", "lazar-fieldwork.json", "new-unverified-fieldwork-2026-09-30.json"]
    for name in canonical_numeric:
        copy(ROOT / "artifacts/strict-post-close" / name, "trends/canonical/" + name)
    for label, folder in [("without-channel14", without_dir), ("poll-correlation", corr_dir)]:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                assert p.suffix.lower() not in {".html", ".htm"}, p
                copy(p, "trends/" + label + "/" + p.relative_to(folder).as_posix())
    reproducers = ["ingest-polls-2026-10-15-hayom.py", "validate-ingestion-2026-10-15-hayom.py", "validate-poll-update-2026-10-15-hayom.py",
        "build-trend-summaries-2026-10-15-hayom.py", "build-strict-party-trends.py", "derive-strict-trends-without-channel14.py",
        "build-poll-correlation.py", "audit-poll-correlation.py", "compare-poll-update.mjs", "validate-model-comparison-2026-10-15-hayom.mjs",
        "browser-poll-update-2026-10-15-hayom.mjs", "review-browser-visual-2026-10-15-hayom.py", "review-social-poll-update-2026-10-15-hayom.py",
        "readback-poll-update-2026-10-15-hayom.py", "package-poll-update-2026-10-15-hayom.py",
        "normalize-kantar-source-tier-2026-10-15-hayom-r1.py", "validate-kantar-source-tier-2026-10-15-hayom-r1.py"]
    for name in reproducers:
        copy(ROOT / "scripts" / name, "reproduction/" + name)
    for name in ["analyze-strict-post-close-2026-09-28.py", "audit-strict-full-series-2026-09-28.py", "analyze-party-trends-strict-2026-09-28.py"]:
        copy(ROOT / "artifacts" / name, "reproduction/" + name)
    for rel, digest in checkpoint["reviewedExactHelpers"].items():
        assert sha(ROOT / rel) == digest
        if rel.startswith("artifacts/strict-post-close/"):
            copy(ROOT / rel, "reproduction/" + Path(rel).name)
    copy(local, "browser-local-report.json")
    copy(visual, "browser-local-visual-review.json")
    copy(ART / "social/render-checks.json", "social/render-checks.json")
    for p in social_files:
        dest = REPO / "updates" / RELEASE / p.name
        copies[dest] = p
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(p), "bytes": p.stat().st_size}

    after = comparison["after"]
    party = lambda pid: next(p for p in after["parties"] if p["id"] == pid)
    groups = {g["id"]: g["stats"]["mean"] for g in after["reportingGroups"]}
    assert abs(sum(groups.values()) - 120) < 1e-8
    bloc = read(without_dir / "party-analysis.json")
    bloc_labels = {"coalition": "קואליציה", "opposition": "אופוזיציה ללא ערביות", "opposition_raam": "אופוזיציה עם רע״ם"}
    bloc_findings = [bloc_labels[r["group"]] for r in bloc["primary"]["blocOverall"] if r["qValue"] < .05]
    party_findings = [r["partyName"] for r in selected["rows"] if r["qValue"] < .05]
    sensitivity_findings = [r["partyName"] for r in selected["rows"] if r["wholeSeriesSignFlipQ"] < .05]
    heading = "## ישראל היום / קנטאר — עדכון נוסף 15.10.2026\n\n"
    candidate = read(ROOT / plan['polls'][0]['candidatePath'])
    old_current = next(p for p in read(ART/'before/data/current-polls.json')['polls'] if p['pollsterId']=='kantar')
    old_hayom = next(p for p in read(ART/'before/data/poll-history.json')['polls'] if p['pollsterId']=='kantar' and p['date']=='2026-10-08' and p['sourcePollId']=='kantar_2026-10-08')
    assert old_current['date']=='2026-10-11' and candidate['date']=='2026-10-15'
    assert candidate['fieldworkStart']=='2026-10-14' and candidate['fieldworkEnd']=='2026-10-15' and candidate['sampleSize']==551
    opposition_ids=['yashar','beyachad','democrats','yisrael_beiteinu']
    arab_ids=['joint','raam']
    coalition_ids=['likud','otzma','utj','shas','rz_zehut','winter']
    raw_before={k:sum(old_hayom['seats'][p] for p in ids) for k,ids in [('coalition',coalition_ids),('opposition',opposition_ids),('arab',arab_ids)]}
    raw_after={k:sum(candidate['seats'][p] for p in ids) for k,ids in [('coalition',coalition_ids),('opposition',opposition_ids),('arab',arab_ids)]}
    assert raw_before=={'coalition':51,'opposition':51,'arab':13}
    assert raw_after=={'coalition':50,'opposition':52,'arab':14}
    assert old_hayom['seats']['hendel']==5 and candidate['seats']['hendel']==4
    assert candidate['reportedPercentages']['winter']==3.0
    section = heading + f'''נוסף סקר ישראל היום / קנטאר שפורסם ב־15.10.2026 ונאסף ב־14–15.10 בקרב 551 משיבים. בדוח המקורי: דגימה אינטרנטית, גברים ונשים בגיל18 ומעלה כולל המגזר הערבי, 2,476 אנשים שהתבקשו לענות וטעות דגימה שפורסמה ±4.2%. תאריך הפרסום ומועדי האיסוף נשמרים בנפרד; פרטים שלא פורסמו נשארים חסרים. [המקור המקורי]({candidate['sourceUrl']}) · [אימות המקורות]({PREFIX}/source-plan.json).

בסקר החדש: קואליציה50 כולל וינטר, אופוזיציה52 ללא ערביות והנדל–זליכה, ערביות14 והנדל–זליכה4 בנפרד; וינטר מתחת לחסימה עם3.0%. בהשוואה לפרסום ישראל היום הקודם מ־8.10: הקואליציה51→50, האופוזיציה51→52, הערביות13→14 והנדל–זליכה5→4. זו השוואה תיאורית בין שני סקרים של אותו מפרסם, ואין להסיק ממנה לבדה מעבר מצביעים או מגמה מובהקת. החלפת התצפית הפעילה בשקלול נעשית לפי מכון: סקר קנטאר מכאן11.10 מוחלף, והוא נשמר בהיסטוריה עם מועד איסוף לא מאומת. השוואת המפרסם8.10 אינה נקודת הבסיס של חישוב השינוי במודל.

ברירת המחדל נשארה דיוק היסטורי, השתתפות בסיס2022, ללא ערוץ14, אות־רעש כבוי ודמיון־סקרים כבוי. ממוצעי המודל: קואליציה {groups['a']:.2f}, אופוזיציה {groups['b']:.2f}, ערביות {groups['arab']:.2f}, שאר הרשימות {groups['other']:.2f}; סכומם120. סיכויי מעבר במודל: וינטר {100 * party('winter')['passProbability']:.2f}%, הנדל–זליכה {100 * party('hendel')['passProbability']:.2f}%. אלה הסתברויות לפי הנחות המודל, ואינן אחוזי תמיכה שפורסמו. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).

המגמות חושבו מחדש באמצעות השינוי בתוך כל מכון, במשקלי הדיוק ההיסטורי הקיימים. נכללו {full_count} סקרים מאומתים בניתוח הכולל; ללא14 — {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים ו־{selected['coverage']['deltaCount']} דלתות. הסקר החדש נכלל בזכות איסוף מאומת לאחר סגירת הרשימות. {unknown_count} תצפיות אחרות מוחרגות עקב מועד איסוף לא מאומת; החרגת ערוץ14 היא בחירת מקורות נפרדת. במבחן הפרמוטציות הראשי לאחר תיקוןBH, הגושים המובהקים: {', '.join(bloc_findings) or 'אין'}; המפלגות המובהקות: {', '.join(party_findings) or 'אין'}. בבדיקת הרגישות לפי מכונים לאחר תיקוןBH, המפלגות המובהקות: {', '.join(sensitivity_findings) or 'אין'}. כל הכרעה מוצגת בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [הניתוח ללא14]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

נשמרו {ingestion['activePollCount']} מכונים פעילים ו־{ingestion['historyPollCount']} תצפיות היסטוריות. כל {len(checkpoint['frozenEvidenceHashes'])} קובצי הראיות מהפרסומים הקודמים נשמרו ללא שינוי. ראיות הפרסום החדשות מוגבלות לנתונים, גרפיקות ומראי מקום; גופי כתבות מלאים נשארים מחוץ לחבילה. [טיוטת ציוץ](updates/{RELEASE}/tweet.he.txt) · [איור לשיתוף](updates/{RELEASE}/{render['output']}) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json).

'''
    readme = REPO / "README.md"
    body = readme.read_text(encoding="utf-8-sig")
    assert heading not in body
    anchor = "## זמן ישראל / טאטיקה — עדכון נוסף 15.10.2026"
    assert anchor in body
    writes[readme] = body.replace(anchor, section + anchor, 1).encode("utf-8")
    attrs = REPO / ".gitattributes"
    body = attrs.read_text(encoding="utf-8-sig").rstrip() + "\n"
    for prefix in [PREFIX, "updates/" + RELEASE]:
        line = "/" + prefix + "/** -text"
        assert line not in body
        body += line + "\n"
    writes[attrs] = body.encode("utf-8")
    preserved()
    receipt = {"status": "PASS", "asOf": DAY, "runId": "hayom", "newPollCount": len(plan["polls"]),
        "documentedSourceTierNormalization": {"revision": "metadata-normalization-r1", "validationSha256": sha(normalization_dir / "validation.json"),
            "receiptSha256": sha(normalization_dir / "receipt.json"), "onlyTwoNewPublicDerivativesNormalized": True,
            "sourceCandidateAndOriginalIngestionReceiptsPreserved": True},
        "observationPublicationDates": sorted({read(ROOT / p['candidatePath'])['date'] for p in plan['polls']}),
        "activePolls": ingestion["activePollCount"], "historyPolls": ingestion["historyPollCount"],
        "eligibleFull": full_count, "eligibleWithout14": default_count,
        "unknownFieldworkExcluded": unknown_count, "testsPassed": tests_passed,
        "authorContentFilesUnchanged": len(checkpoint["authorContentHashes"]),
        "protectedRuntimeFilesVerified": len(checkpoint["protectedRuntimeHashes"]),
        "frozenEvidenceFilesPreserved": len(checkpoint["frozenEvidenceHashes"]),
        "conditionalAndArtisticFilesPreserved": len(checkpoint["frozenConditionalAndArtisticHashes"]),
        "reviewedExactHelpersUnchanged": checkpoint["reviewedExactHelpers"],
        "snapshotSha256": sha(ROOT / "dashboard/src/data.json"), "publishedHtmlSha256": hashlib.sha256(clean).hexdigest(),
        "featuresChatGPT": False, "defaultWeightMode": "quality", "includeChannel14": False,
        "signalNoiseEnabled": False, "pollCorrelationEnabled": False, "socialDraftOnly": True,
        "fullArticleBodiesExcludedFromNewRelease": True, "compiledTo120DatasetExcludedFromNewRelease": True,
        "sourcePlanSha256": sha(ART / "source-plan.json"), "primarySourceSummarySha256": sha(public_source), "sourcePublicFreezeReceiptSha256": sha(discovery_receipt_path),
        "files": [files[key] for key in sorted(files)]}
    if args.check:
        print(json.dumps({"status": "PASS", "phase": "package-preflight-no-files-written", "files": len(files),
            "testsPassed": tests_passed, "publishedHtmlSha256": receipt["publishedHtmlSha256"]}))
        return
    # All dependencies, hashes, paths and README insertion are validated before
    # the first write. Existing dated files remain immutable.
    for dest, source in copies.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), ("Existing output changed during preflight", dest)
        else:
            shutil.copy2(source, dest)
    for dest, body in writes.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
    preserved()
    immutable_write(ART / "publication-receipt.json", receipt)
    immutable_write(REPO / PREFIX / "release.json", receipt)
    print(json.dumps({"status": "PASS", "files": len(files), "testsPassed": tests_passed,
        "publishedHtmlSha256": receipt["publishedHtmlSha256"]}))


if __name__ == "__main__":
    main()
