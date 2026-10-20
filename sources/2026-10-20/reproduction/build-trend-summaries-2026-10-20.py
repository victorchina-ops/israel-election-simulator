"""Build neutral Hebrew trend summaries from the validated October 20 canonical audits.

Dates, cohorts, effect sizes, p/q values and significance verdicts are read from
validated evidence. Describe each added observation and its actual fieldwork
eligibility without assuming that an update leaves significance unchanged.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT = ROOT / "artifacts/strict-post-close"
DAY = "2026-10-20"
LABELS = {
    "coalition": "קואליציה כולל עמך ישראל",
    "opposition": "אופוזיציה ללא ערביות",
    "opposition_raam": "אופוזיציה עם רע״ם",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hebrew_date(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.day}.{parsed.month}.{parsed.year}"


def verdict(value):
    return "מובהק" if value < .05 else "לא מובהק"


def names(rows, key, name_key):
    selected = [name_key(row) for row in rows if row[key] < .05]
    return ", ".join(selected) if selected else "אין"


def table(rows, label, sensitivity_p, sensitivity_q):
    result = [
        "| שם | Δ כולל | קצב לשבוע | p ראשי | q ראשי אחרי BH | הכרעה ראשית | p רגישות | q רגישות אחרי BH | הכרעת רגישות |",
        "|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        result.append(
            f"| {label(row)} | {row['weightedNetDelta']:+.3f} | {row['slopePerWeek']:+.3f} "
            f"| {row['pValue']:.6f} | {row['qValue']:.6f} | {verdict(row['qValue'])} "
            f"| {row[sensitivity_p]:.6f} | {row[sensitivity_q]:.6f} | {verdict(row[sensitivity_q])} |"
        )
    return "\n".join(result)


def make_summary(title, audit, bloc, party, current, history, snapshot, validation, default_snapshot, default_audit, is_party):
    primary = audit["primary"]
    eligible = [row for row in audit["cohort"] if row["eligibleStrict"]]
    excluded = [row for row in audit["cohort"] if not row["eligibleStrict"]]
    first, last = min(row["fieldworkStart"] for row in eligible), max(row["fieldworkEnd"] for row in eligible)
    n_series = len(primary["byPollster"])
    n_parties = len(party["testedPartyIds"])
    n_groups = len(bloc["primary"]["overall"])
    sign_patterns = primary["wholeSeriesSignPatterns" if is_party else "wholeInstituteSignPatterns"]
    rows = primary["overall"]
    name = (lambda row: row["partyName"]) if is_party else (lambda row: LABELS[row["group"]])
    pkey = "wholeSeriesSignFlipP" if is_party else "wholeInstituteSignFlipP"
    qkey = "wholeSeriesSignFlipQ" if is_party else "wholeInstituteSignFlipQ"
    new_polls = [row for row in current["polls"] if row["id"] in validation["addedActivePollIds"]]
    new_cohort = [row for row in audit["cohort"] if row["pollId"] in validation["addedHistoryPollIds"]]
    assert len(new_polls) == len(new_cohort) == validation["newPollCount"]
    new_eligible = [row for row in new_cohort if row["eligibleStrict"]]
    new_excluded = [row for row in new_cohort if not row["eligibleStrict"]]
    assert {row["pollId"] for row in new_eligible} == set(validation["newStrictEligiblePollIds"])
    assert {row["pollId"] for row in new_excluded} == set(validation["newStrictExcludedPollIds"])
    publishers = {f"history_{row['id']}_current":row["publisher"] for row in new_polls}
    eligible_names = " ו־".join(publishers[row["pollId"]] for row in new_eligible)
    excluded_names = " ו־".join(publishers[row["pollId"]] for row in new_excluded)
    display_date = hebrew_date(audit["asOf"])
    new_names = " ו־".join(row["publisher"] for row in new_polls)
    c14 = next(row for row in current["polls"] if row["pollsterId"] == "next_data")
    new_by_id = {row["pollId"]:row for row in new_cohort}
    new_default_eligible = [row for row in new_eligible if row["pollsterId"] != "next_data"]
    update_details = []
    fixed_bloc_details = []
    for poll in new_polls:
        row = new_by_id[f"history_{poll['id']}_current"]
        if row["eligibleStrict"]:
            detail = (f"{poll['publisher']} ({hebrew_date(poll['date'])}): איסוף מאומת "
                      f"{hebrew_date(row['fieldworkStart'])}–{hebrew_date(row['fieldworkEnd'])}; נכלל במבחן המחמיר")
        else:
            detail = (f"{poll['publisher']} ({hebrew_date(poll['date'])}): מועדי האיסוף לא אומתו; "
                      "נכלל בתחזית ובהיסטוריה ומוחרג מהמבחן המחמיר")
        sample = poll.get("sampleSize")
        detail += f"; גודל המדגם שפורסם: {sample if sample is not None else 'לא פורסם'}"
        update_details.append(detail)
        coalition = sum(poll["seats"].get(pid,0) for pid in bloc["groups"]["coalition"])
        opposition = sum(poll["seats"].get(pid,0) for pid in bloc["groups"]["opposition"])
        arab = sum(poll["seats"].get(pid,0) for pid in ["joint","raam"])
        hendel = poll["seats"].get("hendel",0)
        assert coalition + opposition + arab + hendel == 120
        fixed_bloc_details.append(f"{poll['publisher']} ({hebrew_date(poll['date'])}): "
                                  f"קואליציה {coalition}, אופוזיציה {opposition}, ערביות {arab}, הנדל–זליכה {hendel}")
    update_note = "; ".join(update_details) + ". "
    if new_excluded:
        update_note += ("תאריך פרסום לבדו אינו מוכיח שהאיסוף נעשה כולו אחרי סגירת הרשימות; "
                        "אין להשלים את מועדי האיסוף מתאריך הפרסום או מסקר קודם. ")
    primary_findings = names(rows, "qValue", name)
    sensitivity_findings = names(rows, qkey, name)
    default_rows = default_audit["primary"]["overall" if is_party else "blocOverall"]
    default_coverage = default_snapshot["coverage"]
    default_primary_findings = names(default_rows, "qValue", name)
    default_sensitivity_findings = names(default_rows, qkey, name)
    parts = [
        f"# {title} — איסוף מאומת אחרי סגירת הרשימות",
        f"בדיקה מ־{display_date}; נוספו {len(new_polls)} סקרים: {new_names}. "
        + update_note +
        "כל סקר חדש מחליף את הסקר הפעיל הקודם של אותו מכון; המקורי נשמר בהיסטוריה. "
        "מועד הפרסום ומועד האיסוף נשמרים בנפרד. כל ההחלטות הקודמות לגבי זכאות לאיסוף מאומת "
        "נשמרו ללא שינוי; אין לספור גרפיקה וטבלה של אותו סקר כשתי תצפיות.",
        f"חלון האיסוף המאומת הוא {hebrew_date(first)}–{hebrew_date(last)}. במאגר ההיסטורי "
        f"{len(history['polls'])} סקרים ובמאגר הפעיל {len(current['polls'])}. מתוך {len(audit['cohort'])} "
        f"מועמדים לבדיקה, נכללו {len(eligible)} סקרים של {n_series} מכונים, עם {primary['nDeltas']} "
        f"שינויים עוקבים; {len(excluded)} פרסומים הוחרגו בגלל מועדי איסוף שלא אומתו. "
        f"כל איסוף שנכלל התחיל מ־{hebrew_date(audit['closure']['firstEligibleFieldworkDate'])}, "
        f"אחרי סגירת הרשימות ב־{hebrew_date(audit['closure']['date'])}. משקלי הדיוק ההיסטורי לא השתנו.",
        f"**ברירת המחדל באתר — ללא ערוץ 14:** {default_coverage['pollCount']} סקרים זכאים, "
        f"{default_coverage['seriesCount']} מכונים ו־{default_coverage['deltaCount']} שינויים עוקבים; "
        f"חלון האיסוף בקבוצה זו {hebrew_date(default_coverage['from'])}–{hebrew_date(default_coverage['to'])}. "
        f"מובהקים בראשי אחרי BH: {default_primary_findings}. מובהקים ברגישות לפי מכונים אחרי BH: "
        f"{default_sensitivity_findings}. בעדכון זה נוספו לקבוצה המלאה {len(new_eligible)} סקרים זכאים "
        f"ולקבוצת ברירת המחדל {len(new_default_eligible)}; {len(new_excluded)} פרסומים חדשים עם איסוף לא מאומת הוחרגו. "
        f"סקר ערוץ 14 מ־{hebrew_date(c14['date'])} נשמר במאגר ונכלל בקבוצה המלאה, "
        "אך אינו נכלל כאשר מתג ערוץ 14 כבוי. מדובר בהוצאת מפרסם, "
        "ולא בחוסר מידע על מועד האיסוף.",
        "טבלת ברירת המחדל באתר — ללא ערוץ 14:",
        table(default_rows, name, pkey, qkey),
        f"בקבוצה ללא ערוץ 14 בדיקת הרגישות כוללת {default_audit['primary']['wholeSeriesSignPatterns']} "
        f"היפוכי כיוון של {default_coverage['seriesCount']} מכונים. במשפחות הבדיקות לפי מכון "
        f"נכללים {n_parties*default_coverage['seriesCount']} מבחני מפלגה ו־"
        f"{n_groups*default_coverage['seriesCount']} מבחני גוש; גם בקבוצה זו מתקנים בנפרד "
        "לריבוי בדיקות.",
        f"**כל המכונים — המבחן הראשי אחרי תיקון לריבוי בדיקות:** {primary_findings}. "
        f"**בדיקת הרגישות לפי מכונים אחרי תיקון:** {sensitivity_findings}. "
        "הטבלה מפרידה בין שינוי שנצפה לבין הראיות למגמה יציבה. אי־מובהקות אינה הוכחה שהכול אקראי או שלא חל שינוי.",
        "**מה משווים?** כל מכון מושווה לנקודת ההתחלה שלו. כך, מכון שנותן בקביעות יותר מנדטים "
        "לגוש מסוים אינו יוצר בעצמו מגמת עלייה. Δ הכולל הוא ממוצע משוקלל של השינוי הראשון–אחרון "
        "בכל מכון; חלונות המדידה שונים בין המכונים. השיפוע נעזר בכל התצפיות לאורך הסדרה, ולא רק "
        "בשני הקצוות. לכן כיוון Δ הכולל וכיוון קצב השינוי יכולים להיות שונים.",
        "**המבחן הראשי — פרמוטציה מדויקת בתוך כל מכון:** מחליפים את סדר הזמן של הסקרים "
        "ושואלים באיזו תדירות מתקבל שיפוע משוקלל חריג לפחות כמו זה שנצפה. בכל החלפה שומרים "
        "את כל וקטור המנדטים ואת המשקל ההיסטורי של המכון. ציר הזמן הראשי הוא אמצע חלון "
        "האיסוף; בדיקה נפרדת משתמשת בתאריכי הפרסום. השינויים השבועיים הסמוכים אינם נספרים "
        "כתצפיות עצמאיות, משום שהם חולקים את אותו סקר.",
        f"**בדיקת הרגישות לפי מכונים — היפוך כיוון סדרה שלמה:** הופכים את כיוון השיפוע של "
        f"כל מכון, בלי לשנות את גודלו, ובודקים את כל {sign_patterns} הצירופים. כך בודקים עד "
        f"כמה התוצאה תלויה בכיווני התנועה בין {n_series} המכונים. זו אינה בדיקת הסכמה מלאה "
        "ואינה בדיקה נוספת של כל שינוי שבועי. מספר המכונים קטן, ולכן כוח הבדיקה מוגבל. אם "
        "הראשי מובהק והרגישות אינה מובהקת, מציגים את שתי התוצאות; אין לייחס את ההבדל לתיקון "
        "ריבוי הבדיקות לבדו או לומר שהמגמה בוודאות אינה קיימת.",
        f"**ריבוי בדיקות:** משתמשים ב־Benjamini–Hochberg (BH), עם משפחות נפרדות של "
        f"{n_parties} מפלגות ושל {n_groups} הגדרות גוש. בבדיקות של כל מכון בנפרד מתקנים "
        f"משפחות של {n_parties*n_series} מבחני מפלגה ושל {n_groups*n_series} מבחני גוש. "
        "p הוא הערך לפני התיקון ו־q אחריו; q קטן מ־0.05 מסומן מובהק.",
        "**מגבלות:** המבחנים מניחים חילופיות בזמן או סימטריה בכיוון, וכן עצמאות בין מכונים. "
        "שינוי בשיטות שקלול, תלות בזמן או אירוע משותף לכל הסקרים עלולים להשפיע על המובהקות. "
        "אנחנו מנתחים מנדטים מעוגלים, ולא תשובות גולמיות של משיבים. תמיכה במפלגה יכולה להשתנות "
        "גם כשהיא נשארת מתחת לחסימה עם אפס מנדטים. מובהקות של מגמה אינה תחזית לתוצאות הבחירות.",
        "**הטבלה הבאה כוללת את כל המכונים, לרבות ערוץ 14.** באתר ערוץ 14 כבוי כברירת "
        "מחדל, והטבלה הראשונה מציגה קבוצה זו. לקבוצה ללא ערוץ 14 מחושבים ומאומתים מחדש השיפועים וערכי p ו־q; אין להסיר שורה "
        "ולהשאיר את המובהקות של הקבוצה המלאה. הוצאת מפרסם אינה אותו דבר כמו החרגת סקר "
        "שמועד איסופו אינו ידוע.",
        table(rows, name, pkey, qkey),
        "הקואליציה בניתוח הקבוע כוללת עמך ישראל; האופוזיציה הלא־ערבית כוללת ישר, ביחד, "
        "הדמוקרטים וישראל ביתנו. הנדל–זליכה נשארים ללא שיוך. הגדרה נוספת מצרפת רע״ם "
        "לאופוזיציה. אלו הגדרות ניתוח קבועות שאינן משתנות עם הבחירה האישית בממשק. "
        "בחלוקת הסקרים החדשים לפי הגדרות ניתוח אלו: " + "; ".join(fixed_bloc_details) + ". "
        "נתוני מנדטים שפורסמו אינם אחוזי תמיכה מדויקים; אחוזים שלא פורסמו נשארים חסרים, "
        "ושחזור אחוזים לצורך הסימולציה הוא תוצאת מודל. הגדרות גושים קבועות מונעות ספירה כפולה.",
        "מקורות: " + "; ".join(f"[{row['title']}]({row['url']})" for row in snapshot["sources"])
        + ". הסקרים החדשים: " + "; ".join(f"[{row['publisher']}]({row['sourceUrl']})" for row in new_polls)
        + ". קישורי המקור, מועדי האיסוף וקובצי הראיות נשמרים בכל רשומת cohort.",
        "שחזור ואימות: analysis.json, party-analysis.json, party-independent.json, "
        "independent-strict-numeric-audit.json, party-validation.json; "
        "artifacts/poll-checks/2026-10-20/strict-validation.json. "
        "התיקייה artifacts/poll-checks/2026-10-20/before משמרת את הנתונים והניתוחים "
        f"שלפני {len(new_polls)} הסקרים החדשים, לרבות ניתוחי המובהקות ומקורות המידע הקודמים.",
    ]
    return "\n\n".join(parts)+"\n"


def main():
    bloc=read(STRICT/"analysis.json")
    party=read(STRICT/"party-analysis.json")
    current=read(ROOT/"data/current-polls.json")
    history=read(ROOT/"data/poll-history.json")
    snapshot=read(ROOT/"data/strict-party-trends.json")
    validation=read(STRICT/"party-validation.json")
    assert all(doc["asOf"]==DAY for doc in [bloc,party,current,history,snapshot,validation])
    assert validation["passed"] and validation["status"]=="PASS" and validation["runId"]=="reviewed"
    assert validation["newPollsIncludedInForecast"] and validation["allPriorStrictCohortRowsUnchanged"]
    assert validation["newStrictEligiblePollCount"] == len(validation["newStrictEligiblePollIds"])
    assert validation["c16Oct13FieldworkStillUnknown"] and validation["i24CensoredPercentagesPreservedAsBounds"]
    assert validation["kanOct18FieldworkStillUnknown"] and validation["c14AndI24Oct18VerifiedStrictEligible"]
    assert validation["c13Oct19FieldworkStillUnknown"] and validation["n12C14AndLazarOct19VerifiedStrictEligible"]
    assert validation["memorySafeExactEnumerationWithIndependentDP"]
    assert validation["newPollsIncludedInStrictTrends"] == (validation["newStrictEligiblePollCount"] == validation["newPollCount"])
    assert validation["reviewedExactHelpersUnchanged"]
    for family in ["inputHashes","sourceEvidenceHashes","candidateHashes","preservedCodeHashes","exactArithmeticRepairInputHashes"]:
        for relative,expected in validation[family].items():
            assert sha(ROOT/relative)==expected,("validated evidence changed before summary",relative)
    assert bloc["cohort"]==party["cohort"]
    default_path=ROOT/"data/strict-party-trends-without-channel14.json"
    default_snapshot=read(default_path)
    assert default_snapshot["asOf"]==DAY and default_snapshot["includeChannel14"] is False
    matching=[path for path in (STRICT/"without-channel14"/DAY).glob("*/party-analysis.json")
              if sha(path)==default_snapshot["provenance"]["analysisSha256"]]
    assert matching,"Current default snapshot has no matching dated audit"
    default_audit_path=matching[0]
    default_audit=read(default_audit_path)
    default_receipt_path=default_audit_path.parent/"validation.json"
    default_receipt=read(default_receipt_path)
    assert default_receipt["status"]=="PASS" and default_receipt["asOf"]==DAY
    assert default_receipt["snapshotSha256"]==sha(default_path)
    assert default_receipt["analysisSha256"]==sha(default_audit_path)
    assert default_snapshot["provenance"]["sourceAnalysisSha256"]==sha(STRICT/"party-analysis.json")
    assert default_audit["historySha256"]==sha(ROOT/"data/poll-history.json")
    default_hashes={path:sha(path) for path in [default_path,default_audit_path,default_receipt_path]}
    for filename,title,audit,is_party in [
        ("summary-he.md","מגמות הגושים",bloc,False),
        ("party-summary-he.md","מגמות המפלגות",party,True)]:
        result=make_summary(title,audit,bloc,party,current,history,snapshot,validation,default_snapshot,default_audit,is_party)
        (STRICT/filename).write_text(result,encoding="utf-8")
        print(f"Built {filename} from validated {DAY} audits; {audit['primary']['nPolls']} eligible polls.")
    assert all(sha(path)==expected for path,expected in default_hashes.items()),"Default cohort evidence changed during summary"


if __name__=="__main__":
    main()
