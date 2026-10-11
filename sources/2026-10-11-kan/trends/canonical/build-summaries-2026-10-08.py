"""Render metadata revision with correct public interpretation of both tests."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
bloc = read(HERE / 'analysis.json')
party = read(HERE / 'party-analysis.json')
old_bloc = read(HERE / 'archive-2026-10-07/analysis.json')
old_party = read(HERE / 'archive-2026-10-07/party-analysis.json')
intro = [
    'הנתונים עד 7.10.2026; השלמת פרטי המקור אומתה ב־8.10. לא נוסף סקר חדש ולא שונו המנדטים. המדד מפרסם כי סקר חדשות 13 מ־7.10 נאסף ב־6.10, ולכן הוא מצטרף לניתוח המחמיר.', '',
    '35 סקרים, 8 מכונים ו־27 שינויים עוקבים. נכללו רק סקרים שכל איסופם החל אחרי סגירת הרשימות ב־8.9: חלון האיסוף המאומת 9.9–7.10. ארבעה פרסומים בעלי מועד איסוף לא מאומת הוחרגו. משקלי הדיוק ההיסטורי ושיטת הניתוח נשמרו.', '',
    'משווים כל מכון לנקודת ההתחלה של עצמו, כדי שהבדלי רמה קבועים בין מכונים לא יתפרשו כמגמה. Δ הוא השינוי המשוקלל הראשון–אחרון בכל סדרה, בחלונות שונים. המובהקות בודקת את השיפוע לאורך כל הסדרה, ולא רק את הקצוות.', '',
    'המבחן הראשי: פרמוטציות של סדר הזמן בתוך כל מכון, תוך שמירת וקטור המנדטים המלא והמשקל ההיסטורי. בדיקת הרגישות: הופכים את כיוון השיפוע השלם של כל מכון ושומרים את גודלו, בכל 256 הצירופים. בשתי הבדיקות מתקנים בנפרד לריבוי בדיקות באמצעות Benjamini–Hochberg.', '',
    'בדיקת הרגישות מבוססת על 8 מכונים בלבד; ערכי p בה גסים וכוחה מוגבל, במיוחד לאחר תיקון ל־17 מפלגות. אי־מובהקות בה אינה שוללת את הממצא הראשי ואינה מעידה בהכרח על חוסר הסכמה בין המכונים. במשותפת, למשל, השיפוע עולה ב־6 מכונים ושטוח ב־2, ללא שיפוע יורד.', '',
    'המבחנים מניחים חילופיות בזמן או סימטריה בכיוון, ועצמאות בין מכונים. שינוי שיטת שקלול, תלות בזמן או זעזוע משותף עלולים להשפיע על p. ניתוח מנדטים מעוגלים אינו מחליף נתוני משיבים גולמיים. אי־מובהקות אינה הוכחת אקראיות, ומובהקות אינה תחזית לבחירות.', '',
    'המנדטים ואחוזי המודל לא השתנו. נבחרה השלמת הסוקר המקורי: 1,263 משיבים וטעות ממוצעת ארצית ±2.8 נקודות אחוז ברמת ביטחון 95%; בכתבת חדשות 13 דווחו 1,013 ו־2.5. הסתירה מתועדת. 5.4% מתחת לחסימה מול 4.8% בסכום הרשימות המפורטות נשמרו כפער לא מוסבר, ללא הקצאה למפלגה.', '',
]
headers = ['| שם | Δ כולל | קצב לשבוע | p ראשי | q ראשי לאחר BH | הכרעה ראשית | p רגישות | q רגישות לאחר BH | הכרעת רגישות |',
           '|---|---:|---:|---:|---:|---|---:|---:|---|']
groups = {'coalition': 'קואליציה כולל עמך ישראל', 'opposition': 'אופוזיציה ללא ערביות', 'opposition_raam': 'אופוזיציה עם רע״ם'}
for kind, doc, old in [('bloc', bloc, old_bloc), ('party', party, old_party)]:
    title = 'מגמות הגושים' if kind == 'bloc' else 'מגמות המפלגות'
    rows = doc['primary']['overall']
    lines = ['# ' + title + ' — איסוף מאומת אחרי סגירת הרשימות', '', *intro, *headers]
    for r in rows:
        label = groups[r['group']] if kind == 'bloc' else r['partyName']
        sp, sq = ('wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ') if kind == 'bloc' else ('wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ')
        lines.append(f"| {label} | {r['weightedNetDelta']:+.3f} | {r['slopePerWeek']:+.3f} | {r['pValue']:.6f} | {r['qValue']:.6f} | {'מובהק' if r['qValue'] < .05 else 'לא מובהק'} | {r[sp]:.6f} | {r[sq]:.6f} | {'מובהק' if r[sq] < .05 else 'לא מובהק'} |")
    lines += ['', 'לא נמצאה מגמה מובהקת בגושים. במפלגות נותרו במבחן הראשי לאחר BH: ירידה בביחד ועלייה במשותפת. בשום מפלגה לא נמצאה מובהקות בבדיקת הרגישות לאחר BH.', '',
              'הקואליציה כוללת את עמך ישראל; האופוזיציה הלא־ערבית כוללת ישר, ביחד, הדמוקרטים וישראל ביתנו. הנדל–זליכה נשארים ללא שיוך. לרע״ם מוצגת הגדרה נפרדת.', '',
              'מקור השלמת סקר 13: https://themadad.com/סקר-המדד-7-באוקטובר-2026/ ; המקורות המקוריים וגרפיקות IsraelPolls נשמרו לצד ההיסטוריה.', '',
              'שחזור: analysis.json, party-analysis.json, party-independent.json, independent-strict-numeric-audit.json, party-validation.json. archive-2026-10-07 משמר את הניתוח לפני השלמת המידע.', '']
    (HERE / ('summary-he.md' if kind == 'bloc' else 'party-summary-he.md')).write_text('\n'.join(lines), encoding='utf-8')
print('Rendered revised summaries with separate primary and sensitivity verdicts.')
