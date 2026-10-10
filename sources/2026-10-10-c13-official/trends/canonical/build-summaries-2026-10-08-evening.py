"""Write current accessible summaries from the computed results, without hardcoded verdicts."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
bloc, party = read(HERE / 'analysis.json'), read(HERE / 'party-analysis.json')
snapshot = read(HERE.parents[1] / 'data/strict-party-trends.json')
c = snapshot['coverage']
intro = [
 'נתונים עד 8.10.2026. נוספו שלושה סקרים: ישראל היום / קנטאר, i24 / דיירקט פולס וזמן ישראל / טאטיקה. כל אחד מחליף את הסקר הפעיל הקודם של אותו מכון; התצפית הקודמת נשמרת בהיסטוריה.', '',
 f"{c['pollCount']} סקרים, {c['seriesCount']} מכונים ו־{c['deltaCount']} שינויים עוקבים. נכללו רק סקרים שכל איסופם החל אחרי סגירת הרשימות ב־8.9: חלון האיסוף המאומת 9.9–8.10. ארבעה פרסומים שמועד איסופם לא אומת הוחרגו. משקלי הדיוק ההיסטורי נשמרו.", '',
 'משווים כל מכון לנקודת ההתחלה שלו: הבדלי רמה קבועים בין מכונים אינם מוצגים כמגמה. Δ הוא השינוי המשוקלל הראשון–אחרון בכל סדרה, בחלונות שונים. המובהקות בודקת את השיפוע מכל התצפיות, ולא רק את הקצוות.', '',
 'המבחן הראשי: פרמוטציות של סדר הזמן בתוך כל מכון, תוך שמירת וקטור המנדטים המלא ומשקלו ההיסטורי. בדיקת הרגישות: הופכים את כיוון השיפוע השלם של כל מכון ושומרים את גודלו, בכל 256 הצירופים. בכל בדיקה מתקנים בנפרד לריבוי בדיקות באמצעות Benjamini–Hochberg: 17 מפלגות ו־3 הגדרות גוש.', '',
 'בדיקת הרגישות מבוססת על שמונה מכונים בלבד; ערכי p בה גסים וכוחה מוגבל. אי־מובהקות בה אינה שוללת את הממצא הראשי ואינה מעידה בהכרח על חוסר הסכמה בין מכונים.', '',
 'המבחנים מניחים חילופיות בזמן או סימטריה בכיוון, ועצמאות בין מכונים. שינוי שיטות שקלול, תלות בזמן או זעזוע משותף עלולים להשפיע על p. מנדטים מעוגלים אינם נתוני משיבים גולמיים. אי־מובהקות אינה הוכחת אקראיות, ומובהקות אינה תחזית לבחירות.', '',
]
headers = ['| שם | Δ כולל | קצב לשבוע | p ראשי | q ראשי אחרי BH | הכרעה ראשית | p רגישות | q רגישות אחרי BH | הכרעת רגישות |',
 '|---|---:|---:|---:|---:|---|---:|---:|---|']
groups = {'coalition': 'קואליציה כולל עמך ישראל', 'opposition': 'אופוזיציה ללא ערביות', 'opposition_raam': 'אופוזיציה עם רע״ם'}
for kind, doc in [('bloc', bloc), ('party', party)]:
    title = 'מגמות הגושים' if kind == 'bloc' else 'מגמות המפלגות'
    rows = doc['primary']['overall']
    sp, sq = ('wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ') if kind == 'bloc' else ('wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ')
    label = lambda r: groups[r['group']] if kind == 'bloc' else r['partyName']
    lines = ['# ' + title + ' — איסוף מאומת אחרי סגירת הרשימות', '', *intro, *headers]
    for r in rows:
        lines.append(f"| {label(r)} | {r['weightedNetDelta']:+.3f} | {r['slopePerWeek']:+.3f} | {r['pValue']:.6f} | {r['qValue']:.6f} | {'מובהק' if r['qValue'] < .05 else 'לא מובהק'} | {r[sp]:.6f} | {r[sq]:.6f} | {'מובהק' if r[sq] < .05 else 'לא מובהק'} |")
    main = [label(r) for r in rows if r['qValue'] < .05]
    sensitivity = [label(r) for r in rows if r[sq] < .05]
    lines += ['', 'מובהקים במבחן הראשי לאחר BH: ' + (', '.join(main) or 'אין') + '.', '',
      'מובהקים בבדיקת הרגישות לאחר BH: ' + (', '.join(sensitivity) or 'אין') + '.', '',
      'הקואליציה כוללת עמך ישראל; האופוזיציה הלא־ערבית כוללת ישר, ביחד, הדמוקרטים וישראל ביתנו. הנדל–זליכה נשארים ללא שיוך. הגדרה נוספת מצרפת רע״ם לאופוזיציה.', '',
      'שחזור: analysis.json, party-analysis.json, party-independent.json, independent-strict-numeric-audit.json, party-validation.json. archive-2026-10-08-metadata משמר את הניתוח לפני שלושת הסקרים החדשים.', '']
    (HERE / ('summary-he.md' if kind == 'bloc' else 'party-summary-he.md')).write_text('\n'.join(lines), encoding='utf-8')
print('Wrote summaries with computed primary and sensitivity verdicts.')
