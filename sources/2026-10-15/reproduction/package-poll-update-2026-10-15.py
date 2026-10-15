"""Package the two October14 observations after the October15 independent checks.

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
ART = ROOT / "artifacts/poll-checks" / DAY
PREFIX = "sources/" + DAY
SOCIAL = ROOT / "outputs/social/2026-10-15-poll-update"
EXPECTED = {"hamadad_consortium", "next_data"}
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
    assert {p["pollsterId"] for p in plan["polls"]} == EXPECTED and len(plan["polls"]) == 2
    assert not (ART / "publication-receipt.json").exists(), "Preserve the existing dated release."
    assert not (REPO / "updates" / DAY).exists(), "Preserve previously published social assets."

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
    assert sha(ART / "source-plan.json") == ingestion["sourcePlanSha256"] == preflight["sourcePlanSha256"]
    assert ingestion["activePollCount"] == checkpoint["activePollCount"] == 8
    assert ingestion["historyPollCount"] == checkpoint["historyPollCount"] + len(plan["polls"]) == 122
    full_count = ingestion["fullStrict"]["polls"]
    default_count = ingestion["defaultWithoutChannel14"]["polls"]
    unknown_count = ingestion["fullStrict"]["unknownFieldworkExcluded"]
    assert full_count == preflight["expectedStrictEligible"]
    assert default_count == preflight["expectedStrictWithoutChannel14"]
    assert unknown_count == preflight["expectedUnverifiedFieldwork"]
    corr_dir = ROOT / f"artifacts/poll-correlation/{DAY}/reviewed"
    without_dir = ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/reviewed"
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

    # Safe source discovery receipt explicitly excludes full article bodies and
    # the compiled supplementary dataset. Do not recursively copy its folder.
    public_source = ART / "israelpolls/source-public-freeze-receipt-r1.json"
    source_receipt = read(public_source)
    assert source_receipt["status"] == "PASS" and source_receipt["asOf"] == DAY
    assert source_receipt["fullCopyrightedArticleBodiesExcluded"] is True
    assert source_receipt["compiledTo120DatasetExcluded"] is True
    for item in source_receipt["safePublicFiles"]:
        name = item["fileName"]
        assert Path(name).name == name and Path(name).suffix.lower() not in {".html", ".htm"}
        source = public_source.parent / name
        assert sha(source) == item["sha256"]
        copy(source, "source-discovery/" + name)
    copy(public_source, "source-discovery/source-public-freeze-receipt-r1.json")
    root_summary = ART / "primary-source-public-summary.json"
    assert read(root_summary)["asOf"] == DAY
    copy(root_summary, "primary-source-public-summary.json")

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
    reproducers = ["ingest-polls-2026-10-15.py", "validate-ingestion-2026-10-15.py", "validate-poll-update-2026-10-15.py",
        "build-trend-summaries-2026-10-15.py", "build-strict-party-trends.py", "derive-strict-trends-without-channel14.py",
        "build-poll-correlation.py", "audit-poll-correlation.py", "compare-poll-update.mjs", "validate-model-comparison-2026-10-15.mjs",
        "browser-poll-update-2026-10-15.mjs", "review-social-poll-update-2026-10-15.py",
        "readback-poll-update-2026-10-15.py", "package-poll-update-2026-10-15.py"]
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
        dest = REPO / "updates" / DAY / p.name
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
    heading = "## שני סקרים שפורסמו ב־14.10 — עדכון 15.10.2026\n\n"
    section = heading + f'''נוספו סקר חדשות13/המדד וסקר ערוץ14/NEXT DATA, שניהם פורסמו ב־14.10.2026. נתוני האתר נבדקו ועודכנו ב־15.10, ותאריך זה אינו תאריך איסוף חדש. חדשות13: איסוף13.10, 1,018 משיבים, טעות דגימה מדווחת3.1% ברמת ביטחון95%. ערוץ14: איסוף14.10, 568 משיבים; שיטת האיסוף, טעות הדגימה ורמת הביטחון לא פורסמו במקור שנקרא ונותרו חסרות. [מקור13](https://13tv.co.il/item/news/politics/politics/survey-905396904/) · [דוח המדד](https://themadad.com/סקר-המדד-14-באוקטובר-2026/) · [מקור14](https://www.c14.co.il/article/1739046) · [אימות מקורות]({PREFIX}/source-plan.json).

בסקר13: קואליציה51 **כולל וינטר**, אופוזיציה50, ערביות15 והנדל–זליכה4 בנפרד. לעומת7.10 הקואליציה ירדה55→51; האופוזיציה והערביות ללא שינוי והנדל–זליכה עלו0→4. השוואת שתי תצפיות אינה מעידה כשלעצמה על מעבר מצביעים או מגמה מובהקת. בסקר14: קואליציה62, אופוזיציה44 וערביות14. וינטר2.7% והנדל–זליכה3.1%, שניהם מתחת לחסימה. חדשות14 נשארות מחוץ לשקלול ברירת המחדל, אך כל הנתונים נשמרו וזמינים במתג ההכללה.

בסקר13 דווחו כחול לבן1.2% והציבור החרדי1.1%; יתר אחוזי התמיכה המדויקים שלא פורסמו נשארו חסרים, לרבות אחוז וינטר ואחוז הנדל. בסקר14 נשמרו גם כחול לבן1.2%, נעם0.8%, הציבור החרדי0.4% ואח״י0.2% כרשימה מקורית נפרדת; מיפויה לתא ״אחרים״ הוא לצורכי המודל ואינו אחוז ״אחרים״ שפורסם. דיווח וואלה על סקר13 ושאלות הדעה הנוספות מאותו מדגם14 לא נספרו כסקרים עצמאיים. מגבלות גישה לכאן ולערוץ16 מתועדות ב[סיכום בדיקת המקורות]({PREFIX}/primary-source-public-summary.json); אין להסיק מכך שלא פורסם בהם דבר.

ברירת המחדל נשארה דיוק היסטורי, השתתפות בסיס2022, ללא ערוץ14, אות־רעש כבוי ודמיון־סקרים כבוי. ממוצעי המודל: קואליציה{groups['a']:.2f}, אופוזיציה{groups['b']:.2f}, ערביות{groups['arab']:.2f}, שאר הרשימות{groups['other']:.2f}; סכומם120. סיכויי מעבר במודל: וינטר{100 * party('winter')['passProbability']:.2f}%, הנדל–זליכה{100 * party('hendel')['passProbability']:.2f}%. אלה הסתברויות מותנות בהנחות המודל, ואינן אחוזי תמיכה שפורסמו. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).

המגמות חושבו מחדש באמצעות השינוי בתוך כל מכון, במשקלי הדיוק ההיסטורי הקיימים. נכללו {full_count} סקרים מאומתים בניתוח הכולל; ללא14 — {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים ו־{selected['coverage']['deltaCount']} דלתות. שני הסקרים החדשים זכאים מבחינת איסוף מאומת לאחר סגירת הרשימות. {unknown_count} תצפיות אחרות מוחרגות עקב מועד איסוף לא מאומת; החרגת ערוץ14 היא בחירת מקורות נפרדת. במבחן הפרמוטציות הראשי לאחר תיקוןBH, הגושים המובהקים: {', '.join(bloc_findings) or 'אין'}; המפלגות המובהקות: {', '.join(party_findings) or 'אין'}. בבדיקת הרגישות, המחליפה את כיוון כל סדרת מכון כדי לבחון תמיכה בין מכונים, לאחר תיקוןBH, המפלגות המובהקות: {', '.join(sensitivity_findings) or 'אין'}. כל הכרעה מוצגת בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [הניתוח ללא14]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

האיור החדש מתמקד בתשובת ״אצביע בוודאות״ בסקר13: אופוזיציה84% וקואליציה76%, פער תיאורי של8 נקודות אחוז. זו הצהרת כוונה של הנשאלים ולא תחזית השתתפות בפועל או תוצאת שקלול. גודלי תתי־המדגמים לא פורסמו, ומובהקות הפער לא נבדקה. נתון זה אינו משנה את הנחות ההשתתפות במודל. [טיוטת ציוץ](updates/{DAY}/tweet.he.txt) · [איור לשיתוף](updates/{DAY}/{render['output']}) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json).

נשמרו {ingestion['activePollCount']} מכונים פעילים ו־{ingestion['historyPollCount']} תצפיות היסטוריות, כל המשקלים, התוכן והעיצוב הקיימים, {len(checkpoint['frozenEvidenceHashes'])} קובצי הראיות הקודמים והאיורים הקודמים. הראיות החדשות לציבור מוגבלות לנתונים, גרפיקות ומראי מקום; גופי כתבות מלאים ומאגר To120 המורכב נשארו מחוץ לחבילה החדשה.

'''
    readme = REPO / "README.md"
    body = readme.read_text(encoding="utf-8-sig")
    assert heading not in body
    anchor = "## שלושה סקרים חדשים — 13.10.2026"
    assert anchor in body
    writes[readme] = body.replace(anchor, section + anchor, 1).encode("utf-8")
    attrs = REPO / ".gitattributes"
    body = attrs.read_text(encoding="utf-8-sig").rstrip() + "\n"
    for prefix in [PREFIX, "updates/" + DAY]:
        line = "/" + prefix + "/** -text"
        assert line not in body
        body += line + "\n"
    writes[attrs] = body.encode("utf-8")
    preserved()
    receipt = {"status": "PASS", "asOf": DAY, "runId": "reviewed", "newPollCount": len(plan["polls"]),
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
        "sourcePlanSha256": sha(ART / "source-plan.json"), "sourcePublicFreezeReceiptSha256": sha(public_source),
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
