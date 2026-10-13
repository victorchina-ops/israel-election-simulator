"""Package three reviewed October13 observations after all independent checks.

Run only after the canonical, numerical, replay, browser, visual and social
receipts pass. Preserve every previous source release and the distinct earlier
October13 conditional-scenario artwork. No model or UI source is modified.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "github-pages"
ART = ROOT / "artifacts/poll-checks/2026-10-13"
DAY = "2026-10-13"
PREFIX = "sources/2026-10-13"
SOCIAL = ROOT / "outputs/social/2026-10-13-poll-update"
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
    files = []
    checkpoint = read(ART / "before/manifest.json")
    plan = read(ART / "source-plan.json")
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY
    assert {p["pollsterId"] for p in plan["polls"]} == {"direct_polls", "maagar_mochot", "lazar"}
    assert not (ART / "publication-receipt.json").exists(), "Preserve the existing dated release."
    assert not (REPO / "updates" / DAY).exists(), "Preserve previously published social assets."
    for group in ["authorContentHashes", "protectedRuntimeHashes", "frozenEvidenceHashes", "frozenConditionalAndArtisticHashes"]:
        for rel, digest in checkpoint[group].items():
            assert sha(ROOT / rel) == digest, rel

    def copy(source, name):
        dest = REPO / PREFIX / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), f"Dated evidence differs: {dest}"
        else:
            shutil.copy2(source, dest)
        files.append({"path": dest.relative_to(REPO).as_posix(), "sha256": sha(dest), "bytes": dest.stat().st_size})

    for name in ["ingestion-validation.json", "strict-validation.json", "model-comparison-validation.json"]:
        assert read(ART / name)["status"] == "PASS", name
    integer_review = read(ART / "integer-mass-repair-review.json")
    assert integer_review["status"] == "PASS" and integer_review["frozenOriginalsPreserved"]
    assert integer_review["primaryAndIndependentAlgorithmsRemainSeparate"]
    assert sha(ART / "integer-mass-tests-final.txt") == integer_review["testLogSha256"]
    assert sha(ROOT / "scripts/test-permutation-integer-mass-2026-10-13.py") == integer_review["testScriptSha256"]
    sweep_review = read(ART / "independent-sweep-repair-review.json")
    assert sweep_review["status"] == "PASS" and sweep_review["frozenOriginalsPreserved"]
    assert sweep_review["primaryAndIndependentAlgorithmsRemainSeparate"]
    assert sweep_review["stage1ReviewSha256"] == sha(ART / "integer-mass-repair-review.json")
    assert sha(ART / "independent-sweep-tests.json") == sweep_review["testReceiptSha256"]
    assert sha(ROOT / "scripts/test-independent-sweep-2026-10-13.py") == sweep_review["testScriptSha256"]
    final_helpers = {h["path"]: h for h in sweep_review["helpers"]}
    assert set(final_helpers) == {"artifacts/strict-post-close/compressed_searchsorted_exact.py",
                                  "artifacts/strict-post-close/independent-compressed-counts.py",
                                  "artifacts/audit-strict-full-series-2026-09-28.py",
                                  "artifacts/strict-post-close/party-independent.py"}
    for helper in integer_review["helpers"]:
        assert final_helpers[helper["path"]]["beforeSha256"] == helper["beforeSha256"]
        if helper["path"].endswith("independent-compressed-counts.py"):
            assert sweep_review["supersededIntermediateIndependentHelperSha256"] == helper["afterSha256"]
        else:
            assert final_helpers[helper["path"]]["afterSha256"] == helper["afterSha256"]
    for helper in final_helpers.values():
        assert sha(ROOT / helper["path"]) == helper["afterSha256"]
        assert sha(ART / "before" / helper["path"]) == helper["beforeSha256"]
    ingestion = read(ART / "ingestion-validation.json")
    assert ingestion["activePollCount"] == 8 and ingestion["historyPollCount"] == 120
    full_count = ingestion["fullStrict"]["polls"]
    default_count = ingestion["defaultWithoutChannel14"]["polls"]
    unknown_count = ingestion["fullStrict"]["unknownFieldworkExcluded"]
    assert read(ROOT / f"artifacts/poll-correlation/{DAY}/reviewed/independent-audit.json")["status"] == "passed"
    assert read(ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/reviewed/validation.json")["status"] == "PASS"
    reports = sorted((ART / "browser-local").glob("*/report.json"))
    assert reports, "A fresh local browser report is required."
    local = reports[-1]
    assert read(local)["status"] == "passed"
    visual = local.parent / "visual-review.json"
    assert visual.is_file()
    tests = (ART / "test-results-final.txt").read_text(encoding="utf-8-sig")
    assert re.search(r"fail\s+0(?:\r?\n|$)", tests)
    tests_passed = int(re.search(r"pass\s+(\d+)", tests).group(1))
    render = read(ART / "social/render-checks.json")
    assert render["status"] == "PASS" and render["visualInspectionCompleted"] is True
    assert SOCIAL.is_dir() and SOCIAL != ROOT / "outputs/social/2026-10-13"
    assert Path(render["output"]).name == render["output"]
    assert sha(SOCIAL / render["output"]) == render["outputSha256"]
    assert sha(SOCIAL / render["prompt"]) == render["promptSha256"]
    assert sha(SOCIAL / render["cleanupPrompt"]) == render["cleanupPromptSha256"]
    assert sha(ART / "model-comparison.json") == render["modelComparisonSha256"]
    social_files = sorted(p for p in SOCIAL.iterdir() if p.is_file())
    assert any(p.suffix.lower() == ".png" for p in social_files)
    assert any(p.name == "tweet.he.txt" for p in social_files)
    assert all(p.suffix.lower() in {".png", ".txt", ".json"} for p in social_files)

    snapshot = read(ROOT / "dashboard/src/data.json")
    assert snapshot["dataAsOf"] == DAY and snapshot["buildStatus"] == "complete"
    assert snapshot["features"]["chatGPT"] is False
    cfg = {r["key"]: r["value"] for r in snapshot["queries"]["model_configuration"]["rows"]}
    assert cfg["weightMode"] == "quality"
    assert all(cfg[k] is False for k in ["includeChannel14", "signalNoiseEnabled", "pollCorrelationEnabled"])
    comparison = read(ART / "model-comparison.json")
    assert comparison["status"] == "passed" and comparison["onlyControlDateDiffers"]
    assert {p["pollsterId"] for p in comparison["pollChanges"] if p["changed"]} == {"direct_polls", "maagar_mochot", "lazar"}
    assert len(comparison["after"]["pollWeights"]) == 7
    assert all(p["pollsterId"] != "next_data" for p in comparison["after"]["pollWeights"])
    inputs = {r["key"]: r["value"] for r in snapshot["queries"]["model_input"]["rows"]}
    assert len(inputs["current"]["polls"]) == 8 and len(inputs["history"]["polls"]) == 120
    assert inputs["current"] == read(ROOT / "data/current-polls.json")
    assert inputs["history"] == read(ROOT / "data/poll-history.json")
    assert inputs["calibration"] == {**read(ROOT / "data/calibration.json"),
                                     "pollCorrelation": read(ROOT / "data/poll-correlation.json")}
    selected = read(ROOT / "data/strict-party-trends-without-channel14.json")
    assert selected["asOf"] == DAY and selected["coverage"]["pollCount"] == default_count
    assert read(ROOT / "data/strict-party-trends.json")["coverage"]["pollCount"] == full_count

    # Verify every explicitly allowlisted original/reposted source before packaging.
    for spec in plan["polls"]:
        for evidence in spec["publicFiles"]:
            public = REPO / PREFIX / spec["folder"] / evidence["publicName"]
            assert sha(public) == sha(ROOT / evidence["sourcePath"]) == evidence["sha256"]
    for p in sorted((REPO / PREFIX).rglob("*")):
        if p.is_file():
            files.append({"path": p.relative_to(REPO).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size})

    compiled = (ROOT / "dashboard/dist/index.html").read_bytes()
    clean, count = re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*', b"", compiled, flags=re.I)
    assert count == 1 and b"01a0952c-a40b-7b01-b019-621f0cee2656" not in clean
    assert sha(ROOT / "dashboard/src/data.json").encode() in clean
    for p in [REPO / "index.html", ROOT / "election-simulator.html", ROOT / "artifacts/github-pages-release/index.html"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(clean)
    shutil.copy2(ROOT / "dashboard/src/data.json", ROOT / "dashboard-snapshot.json")
    for name in ["current-polls", "poll-history", "sources", "parties", "calibration", "survey-documents-2026-09-14",
                 "strict-party-trends", "strict-party-trends-without-channel14", "poll-correlation"]:
        copy(ROOT / "data" / (name + ".json"), name + ".json")
    for name in ["source-plan.json", "ingestion-preflight.json", "ingestion-receipt.json", "ingestion-validation.json",
                 "strict-validation.json", "model-comparison.json", "model-comparison-validation.json", "test-results-final.txt",
                 "integer-mass-repair-review.json", "integer-mass-tests-final.txt",
                 "independent-sweep-repair-review.json", "independent-sweep-tests.json"]:
        copy(ART / name, name)
    for p in sorted((ROOT / "artifacts/strict-post-close").iterdir()):
        if p.is_file():
            copy(p, "trends/canonical/" + p.name)
    for label, folder in [("without-channel14", ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/reviewed"),
                          ("poll-correlation", ROOT / f"artifacts/poll-correlation/{DAY}/reviewed")]:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                copy(p, "trends/" + label + "/" + p.relative_to(folder).as_posix())
    reproducers = ["ingest-polls-2026-10-13.py", "validate-ingestion-2026-10-13.py", "validate-poll-update-2026-10-13.py",
                   "build-trend-summaries-2026-10-13.py", "build-strict-party-trends.py", "derive-strict-trends-without-channel14.py",
                   "build-poll-correlation.py", "audit-poll-correlation.py", "compare-poll-update.mjs",
                   "validate-model-comparison-2026-10-13.mjs", "browser-poll-update-2026-10-13.mjs",
                   "readback-poll-update-2026-10-13.py", "package-poll-update-2026-10-13.py",
                   "test-permutation-integer-mass-2026-10-13.py", "review-permutation-integer-mass-2026-10-13.py",
                   "review-social-poll-update-2026-10-13.py", "test-independent-sweep-2026-10-13.py",
                   "review-independent-sweep-2026-10-13.py"]
    for name in reproducers:
        copy(ROOT / "scripts" / name, "reproduction/" + name)
    for name in ["analyze-strict-post-close-2026-09-28.py", "audit-strict-full-series-2026-09-28.py", "analyze-party-trends-strict-2026-09-28.py"]:
        copy(ROOT / "artifacts" / name, "reproduction/" + name)
    copy(local, "browser-local-report.json")
    copy(visual, "browser-local-visual-review.json")
    copy(ART / "israelpolls/source-summary-r1.json", "israelpolls-source-summary.json")
    copy(ART / "other-primary-web-checks.json", "other-primary-web-checks.json")
    copy(ART / "tv-primary/remaining-tv-source-summary.json", "remaining-tv-source-summary.json")
    for name, digest in read(ART / "tv-primary/remaining-tv-source-summary.json")["receiptFiles"].items():
        assert Path(name).name == name
        receipt_path = ART / "tv-primary" / name
        assert sha(receipt_path) == digest
        copy(receipt_path, name)

    # Only the newly authored poll-update social assets are eligible for this release.
    for p in social_files:
        dest = REPO / "updates" / DAY / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        files.append({"path": dest.relative_to(REPO).as_posix(), "sha256": sha(dest), "bytes": dest.stat().st_size})

    after = comparison["after"]
    party = lambda pid: next(p for p in after["parties"] if p["id"] == pid)
    groups = {g["id"]: g["stats"]["mean"] for g in after["reportingGroups"]}
    assert abs(sum(groups.values()) - 120) < 1e-8
    bloc = read(ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/reviewed/party-analysis.json")
    bloc_labels = {"coalition": "קואליציה", "opposition": "אופוזיציה ללא ערביות", "opposition_raam": "אופוזיציה עם רע״ם"}
    bloc_findings = [bloc_labels[r["group"]] for r in bloc["primary"]["blocOverall"] if r["qValue"] < .05]
    party_findings = [r["partyName"] for r in selected["rows"] if r["qValue"] < .05]
    sensitivity_findings = [r["partyName"] for r in selected["rows"] if r["wholeSeriesSignFlipQ"] < .05]
    png_name = next(p.name for p in social_files if p.suffix.lower() == ".png")
    heading = "## שלושה סקרים חדשים — 13.10.2026\n\n"
    section = heading + f'''נוספו שלוש תצפיות חדשות: i24NEWS / דיירקט פולס (1,210 משיבים; איסוף13.10), ערוץ16 / מאגר מוחות (פורסם ״למעלה מ־2,000 משיבים״; גודל מדגם מדויק ומועדי איסוף אינם מאומתים), וואלה / לזר מחקרים (601 משיבים; איסוף12.10, פרסום13.10). פרסום מעריב של סקר וואלה הוא אותו מדגם ולא סקר רביעי. [מקורi24](https://www.i24news.tv/he/news/israel-elections-2026/polls/artc-b9e16632) · [מקורוואלה](https://www.walla.co.il/news/politics/383957251) · [אימות המקורות]({PREFIX}/source-plan.json).

בגרפיקות שפורסמו: i24 — קואליציה57, אופוזיציה50 וערביות13; ערוץ16 — קואליציה52 **כולל וינטר**, אופוזיציה50, ערביות13 והנדל–זליכה5 בנפרד; וואלה — קואליציה49, אופוזיציה54, ערביות13 והנדל–זליכה4 בנפרד. בהגדרות הקבועות של האתר וינטר משויך כברירת מחדל לקואליציה והנדל–זליכה ללא שיוך. ההשוואה ש־i24 פרסם ל־8.10 מציגה60→57 בגוש הקואליציה, ו־60 הקודמים כוללים וינטר4; הגדרות מקור היסטוריות נשמרו כפי שפורסמו. אין לערבב גוש ״אחרים55״ בטבלת16 עם אופוזיציה50, משום שהראשון כולל הנדל5.

האחוזים המדויקים שפורסמו נשמרו בנפרד משחזור למודל: i24 — וינטר3.1% והנדל–זליכה2.2%; ארבע רשימות במודל ושתי רשימות נוספות דווחו ״מתחת ל־1%״, כחסם ולא כאפס או אחוז מדויק. ערוץ16 — כחול לבן1.2%, הציבור החרדי1.1%; וואלה — וינטר2.8%, כחול לבן1.1%, הציבור החרדי1.0%, נעם0.2%. אחוזי המפלגות העוברות, אחוז ״אחרים״ ונתונים שלא פורסמו נשארו חסרים. בערוץ16 המדגם המדויק נותרnull; שחזור המודל הקיים משתמש בברירת מחדלn=500 לחישוב אי־ודאות כש־n חסר, **זו הנחת מודל ולא המדגם שפורסם**. בוואלה ״מספר המבקשים להשתתף4,089״ נשמר בשמו המקורי, ולא הומר למספר מוזמנים; שיעור המענה15%, גודל מדגם התחלתי600 ובפועל601. שאלות ודאות ההצבעה נשמרו בנפרד ולא הוזנו כשיעור מתלבטים או השתתפות.

ברירת המחדל נשארה דיוק היסטורי, השתתפות בסיס2022, ללא ערוץ14, אות־רעש כבוי ודמיון־סקרים כבוי. ממוצעי המודל: קואליציה{groups['a']:.2f}, אופוזיציה{groups['b']:.2f}, ערביות{groups['arab']:.2f}, שאר הרשימות{groups['other']:.2f}; סכומם120. סיכויי המעבר במודל: וינטר{100 * party('winter')['passProbability']:.2f}%, הנדל–זליכה{100 * party('hendel')['passProbability']:.2f}%. אלה הסתברויות מותנות בהנחות המודל ולא אחוזי תמיכה שפורסמו או הבטחה לבחירות. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).

המגמות חושבו מחדש לפי שינוי בתוך כל מכון, במשקלי הדיוק ההיסטורי הקיימים: {full_count} סקרים מאומתים בניתוח הכולל; ללא14 — {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים ו־{selected['coverage']['deltaCount']} דלתות. i24 ווואלה החדשים זכאים לניתוח זה; סקר16 החדש נשמר בתחזית ובהיסטוריה אך מוחרג מהמבחן המחמיר משום שמועד איסופו לא אומת. {unknown_count} תצפיות בסך הכול מוחרגות עקב שדה לא מאומת. במבחן הפרמוטציות הראשי לאחר תיקוןBH, הגושים המובהקים: {', '.join(bloc_findings) or 'אין'}; המפלגות המובהקות: {', '.join(party_findings) or 'אין'}. בבדיקת הרגישות של החלפת כיוון כל סדרת מכון, לאחר תיקוןBH, המפלגות המובהקות: {', '.join(sensitivity_findings) or 'אין'}. כל הכרעה מוצגת בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [ניתוח ברירת המחדל]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

[ציוץ](updates/{DAY}/tweet.he.txt) · [אינפוגרפיקה](updates/{DAY}/{png_name}) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json). נשמרו8 מכונים פעילים ו־120 תצפיות היסטוריות, כל משקלי הדיוק, העיצוב, המקורות הישנים ואינפוגרפיקת ארבעת התרחישים שנוצרה מוקדם יותר ב־13.10 על בסיס נתוני12.10.

'''
    readme = REPO / "README.md"
    body = readme.read_text(encoding="utf-8-sig")
    assert heading not in body
    anchor = "## שני סקרים חדשים — 12.10.2026"
    assert anchor in body
    readme.write_bytes(body.replace(anchor, section + anchor, 1).encode("utf-8"))
    attrs = REPO / ".gitattributes"
    body = attrs.read_text(encoding="utf-8-sig").rstrip() + "\n"
    for prefix in [PREFIX, "updates/" + DAY]:
        line = "/" + prefix + "/** -text"
        assert line not in body
        body += line + "\n"
    attrs.write_bytes(body.encode("utf-8"))
    for group in ["authorContentHashes", "protectedRuntimeHashes", "frozenEvidenceHashes", "frozenConditionalAndArtisticHashes"]:
        for rel, digest in checkpoint[group].items():
            assert sha(ROOT / rel) == digest, rel
    unique_files = {row["path"]: row for row in files}
    receipt = {"status": "PASS", "asOf": DAY, "runId": "reviewed", "newPollCount": 3, "activePolls": 8,
               "historyPolls": 120, "eligibleFull": full_count, "eligibleWithout14": default_count,
               "unknownFieldworkExcluded": unknown_count, "testsPassed": tests_passed,
               "authorContentFilesUnchanged": len(checkpoint["authorContentHashes"]),
               "protectedRuntimeFilesVerified": len(checkpoint["protectedRuntimeHashes"]),
               "frozenEvidenceFilesPreserved": len(checkpoint["frozenEvidenceHashes"]),
               "conditionalAndArtisticFilesPreserved": len(checkpoint["frozenConditionalAndArtisticHashes"]),
               "snapshotSha256": sha(ROOT / "dashboard/src/data.json"), "publishedHtmlSha256": sha(REPO / "index.html"),
               "featuresChatGPT": False, "defaultWeightMode": "quality", "includeChannel14": False,
               "signalNoiseEnabled": False, "pollCorrelationEnabled": False, "socialDraftOnly": True,
               "files": [unique_files[key] for key in sorted(unique_files)]}
    immutable_write(ART / "publication-receipt.json", receipt)
    immutable_write(REPO / PREFIX / "release.json", receipt)
    print(json.dumps({"status": "PASS", "files": len(unique_files), "testsPassed": tests_passed,
                      "publishedHtmlSha256": receipt["publishedHtmlSha256"]}))


if __name__ == "__main__":
    main()
