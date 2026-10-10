"""Render current bloc/party reports against the preserved October 4 audit."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = HERE / 'archive-2026-10-04'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dated(value):
    return f"{int(value[8:10])}.{int(value[5:7])}.{value[:4]}"


def fmt(value, digits=3):
    return f"{0 if abs(value) < 1e-10 else value:+.{digits}f}"


bloc = read(HERE / 'analysis.json')
party = read(HERE / 'party-analysis.json')
old_bloc = read(BEFORE / 'analysis.json')
old_party = read(BEFORE / 'party-analysis.json')
assert bloc['asOf'] == party['asOf'] == '2026-10-05'
assert old_bloc['asOf'] == old_party['asOf'] == '2026-10-04'
new = next(row for row in bloc['cohort'] if row['pollId'] == 'history_midgam_geva_2026-10-05_current')
eligible = [row for row in bloc['cohort'] if row['eligibleStrict']]
excluded = [row for row in bloc['cohort'] if not row['eligibleStrict']]
p = bloc['primary']
names = {
    'direct_polls': 'i24 / דיירקט פולס', 'hamadad_consortium': 'חדשות 13 / המדד',
    'kantar': 'כאן והיום / קנטאר', 'lazar': 'מעריב ווואלה / לזר',
    'maagar_mochot': 'ערוץ 16 / מאגר מוחות', 'midgam_geva': 'חדשות 12 / מדגם',
    'next_data': 'חדשות 14 / NEXT DATA', 'tatika': 'זמן ישראל / טאטיקה',
}
groups = {'coalition': 'קואליציה', 'opposition': 'אופוזיציה ללא ערביות',
          'opposition_raam': 'אופוזיציה עם רע״ם'}
source_link = f"[סקר חדשות 12 / מדגם מ־5.10]({new['sourceUrl']})"
fieldwork_note = (
    f"{source_link} נוסף למדגם המחמיר לאחר אימות איסוף התשובות בין "
    f"{dated(new['fieldworkStart'])} ל־{dated(new['fieldworkEnd'])} במקור."
    if new['eligibleStrict'] else
    f"{source_link} נוסף למאגר הכללי. מועדי איסוף התשובות לא הופיעו בהפרסום המקורי שנבדק, "
    "ולכן הוא הוחרג מהניתוח המחמיר; תאריך הפרסום לא הוחלף בתאריך איסוף."
)
cohort_note = (
    f"הניתוח המעודכן כולל {p['nPolls']} סקרים, {p['nPollsters']} סדרות ו־{p['nDeltas']} שינויים עוקבים. "
    f"חלון האיסוף המאומת: {dated(min(row['fieldworkStart'] for row in eligible))}–"
    f"{dated(max(row['fieldworkEnd'] for row in eligible))}. "
    f"{len(excluded)} מתוך {len(bloc['cohort'])} פרסומים הוחרגו בשל מועדי איסוף לא מאומתים. "
    "ההחרגה אינה קביעה שהאיסוף קדם לסגירת הרשימות."
)
access_note_path = ROOT / 'artifacts/2026-10-05-comparison/source-access-note.he.txt'
access_note = (access_note_path.read_text(encoding='utf-8').strip() if access_note_path.exists() else
               "מקורות והגבלות גישה מתועדים ביומן בדיקת המקורות של 5.10.2026; אין להסיק מהיעדר גישה שלא פורסמו סקרים נוספים.")
shared_method = [
    "מועד סגירת הרשימות הוא 8.9.2026. נכללו רק סקרים שכל איסופם החל ב־9.9 או אחריו ומועדי האיסוף אומתו במקור. "
    "מקורות: [ועדת הבחירות](https://www.gov.il/en/pages/time--table-26), "
    "[המכון הישראלי לדמוקרטיה](https://www.idi.org.il/articles/65737).",
    "",
    "לכל מכון נאמד קצב שבועי מכל תצפיות המנדטים לפי אמצע טווח איסוף התשובות. "
    "רגרסיה על כל התצפיות שקולה ל־GLS על השינויים העוקבים עם מטריצת שונות D Dᵀ; "
    "שינויים סמוכים שחולקים סקר אינם נספרים כתצפיות עצמאיות.",
    "",
    f"משקלי הדיוק ההיסטורי מנורמלים פעם אחת ל־{p['nPollsters']} הסדרות שנכללו; "
    "פרסום יותר סקרים אינו מגדיל את המשקל הכולל של מכון. "
    f"מבחן הפרמוטציות המדויק מערבב וקטורים מלאים בין מועדים בתוך כל סדרה, "
    f"על פני {p['exactCounting']['nPermutations']:,} צירופים. "
    f"רגישות: {p['wholeInstituteSignPatterns']} היפוכי סימן של סדרות שלמות; גם בה בוצע BH.",
    "",
    "Δ הוא ממוצע משוקלל של ההפרש בין הסקר הראשון לאחרון בכל סדרה, בחלונות זמנים שונים. "
    "ערכי p בודקים את השיפוע מכל התצפיות; הם אינם מבחן של הפרש הקצוות.",
    "",
    "מבחן הפרמוטציות מניח אפשרות להחליף תוצאות בין מועדים תחת השערת האפס ועצמאות בין סדרות. "
    "טעויות סדרתיות, שינויי שיטה וזעזועים משותפים עלולים לשבש את ערכי p. "
    "בדיקת היפוך הסימן מניחה סימטריה ועצמאות בין מכונים, ואינה פותרת תלות ביניהם. "
    "מנדטים הם תחזיות מעוגלות ותלויות באחוז חסימה; אין להסיק מהן מעבר מצביעים, סיבתיות או תוצאות בחירות.",
    "",
    f"לכל סדרה {min(len(row['pollIds']) for row in p['byPollster'])}–"
    f"{max(len(row['pollIds']) for row in p['byPollster'])} סקרים בלבד; אי־מובהקות אינה מוכיחה שלא חל שינוי. "
    "תיקון BH הוא נומינלי ותלוי בהנחות על התלות בין הבדיקות.",
]
main_sig = [groups[row['group']] for row in p['overall'] if row['qValue'] < .05]
sensitivity_sig = [groups[row['group']] for row in p['overall'] if row['wholeInstituteSignFlipQ'] < .05]
lines = [
    '# מגמות לאחר סגירת הרשימות — איסוף מאומת בלבד', '',
    f"הניתוח עודכן ב־{dated(bloc['asOf'])}. {fieldwork_note}", '', cohort_note, '',
    (f"במבחן הראשי התקבל אות לאחר תיקון BH בגושים: {', '.join(main_sig)}. " if main_sig else
     'במבחן הראשי אין מגמת גוש מובהקת לאחר תיקון BH. ')
    + (f"גם ברגישות נותר אות לאחר BH בגושים: {', '.join(sensitivity_sig)}." if sensitivity_sig else
       'ברגישות של היפוך סדרות שלמות אין מגמת גוש מובהקת לאחר BH.'), '',
    '| גוש | Δ ראשון–אחרון משוקלל | קצב במנדטים לשבוע | p ראשי | q לאחר BH | p ברגישות | q ברגישות |',
    '|---|---:|---:|---:|---:|---:|---:|',
]
old_by_group = {row['group']: row for row in old_bloc['primary']['overall']}
for row in p['overall']:
    lines.append(f"| {groups[row['group']]} | {fmt(row['weightedNetDelta'])} | {fmt(row['slopePerWeek'])} | "
                 f"{row['pValue']:.5f} | {row['qValue']:.5f} | {row['wholeInstituteSignFlipP']:.5f} | "
                 f"{row['wholeInstituteSignFlipQ']:.5f} |")
lines += ['', '## בהשוואה לניתוח מ־4.10', '',
          '| גוש | קצב קודם לשבוע | קצב מעודכן לשבוע | q קודם | q מעודכן |',
          '|---|---:|---:|---:|---:|']
for row in p['overall']:
    old = old_by_group[row['group']]
    lines.append(f"| {groups[row['group']]} | {fmt(old['slopePerWeek'])} | {fmt(row['slopePerWeek'])} | "
                 f"{old['qValue']:.5f} | {row['qValue']:.5f} |")
lines += ['', 'המשקלים והגדרות הגושים נשמרו. ' +
          ('נוסף למדגם המחמיר סקר חדשות 12 מ־5.10 בלבד.' if new['eligibleStrict'] else
           'סקר חדשות 12 החדש הוחרג בשל מועדי איסוף חסרים; אומדני המגמות והמובהקות נותרו זהים.'),
          '', '## כל סדרת סקרים בנפרד', '',
          f"לפני תיקון נמצאו {len(p['significantIndividualRaw'])} אותות ברמת סדרה; "
          f"לאחר BH על {3 * p['nPollsters']} בדיקות נותרו {len(p['significantIndividualBH'])}.", '',
          '| סדרה | גוש | סקרים | Δ ראשון–אחרון | קצב לשבוע | p | q |',
          '|---|---|---:|---:|---:|---:|---:|']
for series in p['byPollster']:
    for row in series['groups']:
        lines.append(f"| {names[series['pollsterId']]} | {groups[row['group']]} | {row['nPolls']} | "
                     f"{fmt(row['netDelta'], 0)} | {fmt(row['slopePerWeek'])} | {row['pValue']:.4f} | {row['qValue']:.4f} |")
lines += ['', '## דרך החישוב ומגבלות', '',
          'הקואליציה כוללת ליכוד, ש״ס, יהדות התורה, עוצמה יהודית, הציונות הדתית–זהות, עמך ישראל ונעם. '
          'האופוזיציה ללא ערביות כוללת ישר, ביחד, הדמוקרטים וישראל ביתנו; הגדרה נוספת מצרפת את רע״ם. '
          'הנדל–זליכה אינם משויכים לאחד משני הגושים.', '', *shared_method,
          '', '## שחזור וראיות', '',
          'analysis.json ו־by-pollster.csv מכילים את המדגם והתוצאות. '
          'audit-strict-full-series-2026-09-28.py מבצע ספירה עצמאית. '
          'archive-2026-10-04 שומר את קובצי האיסוף והניתוח הקודם; '
          'artifacts/2026-10-05-comparison/strict-trends-comparison.json מתעד את ההשוואה.', '', access_note, '']
(HERE / 'summary-he.md').write_text('\n'.join(lines), encoding='utf-8')

rows = sorted(party['primary']['overall'], key=lambda row: row['pValue'])
prior_by_party = {row['partyId']: row for row in old_party['primary']['overall']}
nominal = [row['partyName'] for row in rows if row['pValue'] < .05]
corrected = [row['partyName'] for row in rows if row['qValue'] < .05]
corrected_sensitivity = [row['partyName'] for row in rows if row['wholeSeriesSignFlipQ'] < .05]
zero = [row['partyName'] for row in rows if row['zeroSeatsThroughout']]
lines = ['# מגמות ברמת המפלגה — לאחר סגירת הרשימות בלבד', '',
         f"הניתוח עודכן ב־{dated(party['asOf'])}. {fieldwork_note}", '', cohort_note, '',
         f"לפני תיקון לריבוי בדיקות נמצאו {len(nominal)} אותות: {', '.join(nominal) or 'אין'}. "
         + (f"לאחר BH על 17 מפלגות נותרו: {', '.join(corrected)}. " if corrected else
            'לאחר BH על 17 מפלגות אין אות מובהק. ')
         + (f"ברגישות לאחר BH נותרו: {', '.join(corrected_sensitivity)}." if corrected_sensitivity else
            'ברגישות של היפוך סדרות שלמות אין מפלגה מובהקת לאחר BH.'), '',
         '| מפלגה | Δ ראשון–אחרון משוקלל | מגמה במנדטים לשבוע | p | q לאחר BH | p ברגישות | q ברגישות |',
         '|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
    lines.append(f"| {row['partyName']} | {fmt(row['weightedNetDelta'])} | {fmt(row['slopePerWeek'])} | "
                 f"{row['pValue']:.5f} | {row['qValue']:.5f} | {row['wholeSeriesSignFlipP']:.5f} | "
                 f"{row['wholeSeriesSignFlipQ']:.5f} |")
lines += ['', '## בהשוואה לניתוח מ־4.10', '',
          '| מפלגה | Δ קודם | Δ מעודכן | קצב קודם לשבוע | קצב מעודכן לשבוע | q קודם | q מעודכן |',
          '|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
    old = prior_by_party[row['partyId']]
    lines.append(f"| {row['partyName']} | {fmt(old['weightedNetDelta'])} | {fmt(row['weightedNetDelta'])} | "
                 f"{fmt(old['slopePerWeek'])} | {fmt(row['slopePerWeek'])} | {old['qValue']:.5f} | {row['qValue']:.5f} |")
lines += ['', '## שיטה ומגבלות', '', *shared_method, '',
          f"BH בוצע בנפרד על 17 בדיקות מפלגה משוקללות ועל 119 בדיקות מפלגה×סדרה. "
          f"ברמת סדרה נמצאו {len(party['primary']['significantIndividualRaw'])} אותות לפני תיקון "
          f"ו־{len(party['primary']['significantIndividualBH'])} לאחריו.", '',
          f"{', '.join(zero)} קיבלו אפס מנדטים לאורך המדגם; p=1 הוא מוסכמה לסדרה קבועה. "
          'אפס מנדטים אינו אפס תמיכה; אחוזי תמיכה מתחת לחסימה אינם נבדקים כאן. '
          'קפיצה מאפס לארבעה מנדטים יכולה לנבוע משינוי קטן בתמיכה סביב הסף.', '',
          '## שחזור וראיות', '',
          'party-analysis.json, party-overall.csv, party-by-pollster.csv ו־party-independent.json '
          'שומרים את התוצאות ואת הספירה העצמאית. analysis.json וקובצי ביקורת מועדי האיסוף '
          'שומרים את המדגם, הראיות וההחרגות. archive-2026-10-04 משמר את הבסיס הקודם; '
          'artifacts/2026-10-05-comparison/strict-trends-comparison.json שומר את ההשוואה.', '', access_note, '']
(HERE / 'party-summary-he.md').write_text('\n'.join(lines), encoding='utf-8')
print('Rendered current October 5 bloc and party summaries with October 4 comparison.')
