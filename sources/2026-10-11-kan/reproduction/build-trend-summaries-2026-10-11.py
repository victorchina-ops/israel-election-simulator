"""Build Hebrew trend summaries from the validated October 11 canonical audits.

Dates, cohort counts, effect sizes, p/q values and verdicts come from the audits.
The new Kan forecast observation is explicitly separated from the unchanged
strict fieldwork cohort; no statistical values are hand-entered.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT = ROOT / "artifacts/strict-post-close"
DAY = "2026-10-11"
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
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in rows:
        result.append(
            f"| {label(row)} | {row['weightedNetDelta']:+.3f} | {row['slopePerWeek']:+.3f} "
            f"| {row['pValue']:.6f} | {row['qValue']:.6f} | {verdict(row['qValue'])} "
            f"| {row[sensitivity_p]:.6f} | {row[sensitivity_q]:.6f} | {verdict(row[sensitivity_q])} |"
        )
    return "\n".join(result)


def make_summary(title, audit, bloc, party, current, history, snapshot, validation, is_party):
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
    new_poll = next(row for row in current["polls"] if row["id"] == validation["addedActivePollIds"][0])
    new_cohort = next(row for row in audit["cohort"] if row["pollId"] == validation["addedHistoryPollIds"][0])
    assert not new_cohort["eligibleStrict"]
    intro = (
        f"נתונים שפורסמו עד {hebrew_date(audit['asOf'])}; חלון האיסוף המאומת לצורך ניתוח המגמות הוא "
        f"{hebrew_date(first)}–{hebrew_date(last)}. סקר כאן / קנטאר שפורסם ב־{hebrew_date(new_poll['date'])} "
        "נוסף למאגר ולתחזית, ומחליף את הסקר הפעיל הקודם של קנטאר; כל הסקרים הקודמים נשמרים בהיסטוריה. "
        "מועדי עבודת השדה של הסקר החדש טרם אומתו ולכן הם נשארים חסרים, והוא אינו נכלל במבחני המגמה המחמירים. "
        "עצם תאריך הפרסום אינו מוכיח שכל איסוף התשובות נעשה אחרי סגירת הרשימות."
    )
    parts = [
        f"# {title} — איסוף מאומת אחרי סגירת הרשימות",
        intro,
        f"במאגר ההיסטורי {len(history['polls'])} סקרים ובמאגר הפעיל {len(current['polls'])} סקרים. "
        f"בבדיקה המחמירה {len(audit['cohort'])} מועמדים: {len(eligible)} סקרים זכאים, {n_series} מכונים "
        f"ו־{primary['nDeltas']} שינויים עוקבים. הוחרגו {len(excluded)} פרסומים שמועדי איסופם לא אומתו. "
        f"נכללו רק סקרים שכל איסופם החל מ־{hebrew_date(audit['closure']['firstEligibleFieldworkDate'])}, "
        f"אחרי סגירת הרשימות ב־{hebrew_date(audit['closure']['date'])}. משקלי הדיוק ההיסטורי נשמרו.",
        "הקבוצה הזכאית לא השתנתה בעקבות הסקר החדש. שחזור קנוני ובדיקה מספרית עצמאית אישרו "
        "שמבחני המגמות — גודל השינוי, השיפועים, ערכי p, התיקון לריבוי בדיקות ובדיקות הרגישות — "
        "נותרו בדיוק כפי שהיו בעדכון הקודם. אין להסיק מכך שהתחזית המשוקללת לא השתנתה.",
        "משווים כל מכון לנקודת ההתחלה שלו: מכון שנותן בקביעות יותר מנדטים לגוש אינו יוצר "
        "כשלעצמו מגמת עלייה. Δ הוא ממוצע משוקלל של השינוי הראשון–אחרון בכל סדרה, בחלונות שונים; "
        "זו אינה השוואה בין שני סקרים של מכונים שונים או בין שני תאריכים זהים בכל המכונים. "
        "המובהקות בודקת את השיפוע מכל התצפיות, ולא רק את הקצוות. לכן כיוון Δ וכיוון השיפוע יכולים להיות שונים.",
        "המבחן הראשי: מבחן פרמוטציה מדויק של סדר הזמן בתוך כל מכון, תוך שמירת וקטור המנדטים "
        "המלא ומשקלו ההיסטורי. ציר הזמן הראשי הוא אמצע חלון האיסוף המאומת; בדיקה נוספת משתמשת "
        "בתאריכי הפרסום. השינויים העוקבים אינם נחשבים לתצפיות עצמאיות: השיפוע נאמד מכל התצפיות "
        "באופן השקול להתחשבות בתלות בין דלתות סמוכות.",
        f"בדיקת הרגישות לפי מכונים: הופכים את כיוון השיפוע השלם של כל מכון ושומרים את גודלו, "
        f"בכל {sign_patterns} הצירופים. היא בודקת עד כמה הכיוון המשוקלל חריג מול האפשרות שכיווני "
        f"התנועה בין {n_series} המכונים היו מתחלפים. זו אינה בדיקת הסכמה מלאה, ואינה מבחן נוסף "
        "של כל שינוי שבועי בנפרד. מספר המכונים קטן, ערכי p גסים וכוח הבדיקה מוגבל.",
        f"בכל בדיקה מתקנים בנפרד לריבוי בדיקות באמצעות Benjamini–Hochberg: {n_parties} מפלגות "
        f"במשפחה אחת ו־{n_groups} הגדרות גוש במשפחה נפרדת. בבדיקות של כל מכון בנפרד מתקנים "
        f"משפחות נפרדות של {n_parties * n_series} מבחני מפלגה ושל {n_groups * n_series} מבחני גוש. "
        "q קטן מ־0.05 מסומן מובהק. אם הראשי מובהק אחרי תיקון והרגישות אינה מובהקת, "
        "מציגים את שתי ההכרעות; אין לומר שהתיקון ביטל את המובהקות הראשית.",
        "אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. המבחנים מניחים חילופיות בזמן או סימטריה "
        "בכיוון, ועצמאות בין מכונים. שינוי שיטות שקלול, תלות בזמן או זעזוע משותף עלולים להשפיע "
        "על p. מנדטים מעוגלים אינם נתוני משיבים גולמיים; מפלגה יכולה להשתנות באחוזי התמיכה "
        "ולהישאר על אפס מנדטים מתחת לחסימה. מובהקות אינה תחזית לבחירות.",
        "**הקבוצה בטבלאות שבמסמך הזה כוללת את כל המכונים, לרבות ערוץ 14.** "
        "באתר ערוץ 14 כבוי כברירת מחדל, ומוצגת טבלה שחושבה ואומתה בנפרד לקבוצה ללא ערוץ 14. "
        "הוצאת מפרסם אינה אותו דבר כמו החרגת סקר שמועדי איסופו לא אומתו; אין להסיר שורה "
        "ולהשאיר את ערכי p ו־q מהקבוצה המלאה.",
        table(rows, name, pkey, qkey),
        f"מובהקים במבחן הראשי לאחר BH: {names(rows, 'qValue', name)}.",
        f"מובהקים בבדיקת הרגישות לאחר BH: {names(rows, qkey, name)}.",
        "הקואליציה כוללת עמך ישראל; האופוזיציה הלא־ערבית כוללת ישר, ביחד, הדמוקרטים וישראל ביתנו. "
        "הנדל–זליכה נשארים ללא שיוך. הגדרה נוספת מצרפת רע״ם לאופוזיציה. אלו הגדרות ניתוח קבועות, "
        "והן אינן משתנות עם הבחירה האישית בממשק.",
        "מקורות: " + "; ".join(f"[{row['title']}]({row['url']})" for row in snapshot["sources"])
        + f". [פרסום סקר כאן החדש]({new_poll['sourceUrl']}). קישורי המקור של כל סקר נשמרים ב־cohort.",
        "שחזור ואימות: analysis.json, party-analysis.json, party-independent.json, "
        "independent-strict-numeric-audit.json, party-validation.json; "
        "artifacts/poll-checks/2026-10-11/strict-validation.json. "
        "artifacts/poll-checks/2026-10-11/before משמר את הנתונים והניתוחים שלפני סקר כאן החדש.",
    ]
    return "\n\n".join(parts) + "\n"


def main():
    bloc = read(STRICT / "analysis.json")
    party = read(STRICT / "party-analysis.json")
    current = read(ROOT / "data/current-polls.json")
    history = read(ROOT / "data/poll-history.json")
    snapshot = read(ROOT / "data/strict-party-trends.json")
    validation = read(STRICT / "party-validation.json")
    assert all(doc["asOf"] == DAY for doc in [bloc, party, current, history, snapshot, validation])
    assert validation["passed"] and validation["status"] == "PASS"
    assert validation["primaryAndPublicationAxisNumericalOutputsUnchanged"]
    for relative, expected in validation["inputHashes"].items():
        assert sha(ROOT / relative) == expected, ("validated source changed before summary", relative)
    assert bloc["cohort"] == party["cohort"]
    outputs = [
        ("summary-he.md", "מגמות הגושים", bloc, False),
        ("party-summary-he.md", "מגמות המפלגות", party, True),
    ]
    for filename, title, audit, is_party in outputs:
        text = make_summary(title, audit, bloc, party, current, history, snapshot, validation, is_party)
        (STRICT / filename).write_text(text, encoding="utf-8")
        print(f"Built {filename} from validated {DAY} audits; {audit['primary']['nPolls']} eligible polls.")


if __name__ == "__main__":
    main()
