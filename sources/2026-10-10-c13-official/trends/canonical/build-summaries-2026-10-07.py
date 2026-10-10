"""Render the reviewed October 7 trends against the preserved October 6 audit."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = HERE / 'archive-2026-10-06'


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
comparison = read(ROOT / 'artifacts/2026-10-07-comparison/strict-trends-comparison.json')
assert bloc['asOf'] == party['asOf'] == '2026-10-07'
assert old_bloc['asOf'] == old_party['asOf'] == '2026-10-06'
new = comparison['addedPolls'][0]
assert new['pollId'] == 'history_hamadad_consortium_2026-10-07_current'
new_c14 = comparison['addedPolls'][1]
assert new_c14['pollId'] == 'history_next_data_2026-10-07_current' and new_c14['eligibleStrict']
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
source_link = f"[סקר חדשות 13 / המדד מ־7.10]({new['sourceUrl']})"
fieldwork_note = (
    f"{source_link} נכלל בניתוח המחמיר לאחר אימות האיסוף בין "
    f"{dated(new['fieldworkStart'])} ל־{dated(new['fieldworkEnd'])} במקור."
    if new['eligibleStrict'] else
    f"{source_link} נוסף למודל ולמאגר ההיסטורי, אך מועדי איסוף התשובות לא אומתו במקור. "
    "לכן הוא אינו נכלל בבדיקת המגמות המחמירה; תאריך הפרסום אינו תחליף למועד האיסוף."
)
fieldwork_note += (
    f" [סקר חדשות 14 / NEXT DATA מ־7.10]({new_c14['sourceUrl']}) נכלל בניתוח המחמיר "
    f"לאחר אימות איסוף התשובות ב־{dated(new_c14['fieldworkStart'])} במקור."
)
revision_note = ''
for item in comparison['revisedExistingPolls']:
    row = item['after']
    revision_note += (
        f" דיווח מקורי אימת כעת את איסוף הסקר הקיים של {names[row['pollsterId']]} "
        f"מ־{dated(row['publicationDate'])} בין {dated(row['fieldworkStart'])} "
        f"ל־{dated(row['fieldworkEnd'])}. הוא נכלל כעת בלי להיספר כסקר חדש."
    )
cohort_note = (
    f"הניתוח כולל {p['nPolls']} סקרים מ־{p['nPollsters']} סדרות, ו־{p['nDeltas']} שינויים עוקבים. "
    f"חלון איסוף מאומת: {dated(min(row['fieldworkStart'] for row in eligible))}–"
    f"{dated(max(row['fieldworkEnd'] for row in eligible))}. "
    f"{len(excluded)} מתוך {len(bloc['cohort'])} פרסומים הוחרגו בשל מועדי איסוף לא מאומתים. "
    "ההחרגה אינה קביעה שהאיסוף קדם לסגירת הרשימות."
    + revision_note
)
if not comparison['newlyEligiblePollIds']:
    change_note = ('מבחני המגמות והסיכום הסטטיסטי לא השתנו לעומת 6.10: הסקר החדש מוחרג בשל '
                   'מועדי איסוף חסרים. זה אינו אומר שתוצאות הסקר החדש אינן שונות, אלא שאין די תיעוד '
                   'כדי לכלול אותו בחלון שהוגדר מראש.')
else:
    change_note = ('משקלי הדיוק הבסיסיים, הגדרות הגושים ושיטת המבחן נשמרו. '
                   'השינוי בניתוח נובע מהתצפיות שמועדי איסופן אומתו, המפורטות לעיל. '
                   'המשקלים מנורמלים פעם אחת בין שמונה סדרות, בלי לתת משקל נוסף למכון בשל יותר פרסומים.')
access_path = ROOT / 'artifacts/2026-10-07-comparison/source-access-note.he.txt'
access_note = (access_path.read_text(encoding='utf-8').strip() if access_path.exists() else
               'בדיקות המקורות והגבלות הגישה מתועדות ביומן העדכון מ־7.10.2026. אין להסיק מהיעדר גישה שלא פורסמו סקרים נוספים.')
shared_method = [
    'מועד סגירת הרשימות: 8.9.2026. נכללו רק סקרים שכל איסופם החל ב־9.9 או אחריו ומועדי האיסוף אומתו במקור. '
    'מקורות: [ועדת הבחירות](https://www.gov.il/en/pages/time--table-26), '
    '[המכון הישראלי לדמוקרטיה](https://www.idi.org.il/articles/65737).', '',
    'לכל מכון נאמד קצב שבועי מכל תצפיות המנדטים לפי אמצע טווח האיסוף. '
    'רגרסיה על כל התצפיות שקולה ל־GLS על השינויים העוקבים עם מטריצת שונות D Dᵀ; '
    'שינויים סמוכים שחולקים סקר אינם נחשבים תצפיות עצמאיות.', '',
    f"משקלי הדיוק ההיסטורי מנורמלים פעם אחת ל־{p['nPollsters']} הסדרות. "
    f"מבחן פרמוטציות דו־צדדי מדויק מערבב וקטורים מלאים בין מועדים בתוך כל סדרה, על פני "
    f"{p['exactCounting']['nPermutations']:,} צירופים. "
    f"בדיקת רגישות הופכת סימנים של סדרות שלמות, בכל {p['wholeInstituteSignPatterns']} הצירופים; "
    'גם בה בוצע תיקון BH.', '',
    'Δ הוא ההפרש הראשון–אחרון בכל סדרה, משוקלל בין מכונים בחלונות שונים. '
    'ערך p בודק את השיפוע מכל התצפיות, ולא את הפרש הקצוות. '
    'BH נעשה בנפרד למשפחות של שלושת הגושים, מפלגות, גוש×מכון ומפלגה×מכון.', '',
    'המבחן הראשי מניח חילופיות בזמן תחת השערת האפס ועצמאות בין מכונים. '
    'תלות סדרתית, שינוי שיטה או זעזועים משותפים עלולים לשבש את ערכי p. '
    'רגישות היפוך הסימן מניחה סימטריה ועצמאות בין מכונים; היא אינה פותרת תלות ביניהם. '
    'מנדטים הם אומדנים מעוגלים שתלויים באחוז חסימה, ולא תשובות גולמיות של מצביעים. '
    'מובהקות אינה הוכחת סיבתיות או תחזית לתוצאת הבחירות.', '',
    f"לכל סדרה {min(len(row['pollIds']) for row in p['byPollster'])}–"
    f"{max(len(row['pollIds']) for row in p['byPollster'])} סקרים בלבד. "
    'אי־מובהקות אינה מוכיחה שלא חל שינוי. תיקון BH הוא נומינלי ותלוי בהנחות על התלות בין בדיקות.',
]
main_sig = [groups[row['group']] for row in p['overall'] if row['qValue'] < .05]
sensitivity_sig = [groups[row['group']] for row in p['overall'] if row['wholeInstituteSignFlipQ'] < .05]
lines = [
    '# מגמות לאחר סגירת הרשימות — איסוף מאומת בלבד', '',
    f"הניתוח עודכן ב־{dated(bloc['asOf'])}. {fieldwork_note}", '', cohort_note, '', change_note, '',
    (f"במבחן הראשי נמצאה מגמה לאחר BH בגושים: {', '.join(main_sig)}. " if main_sig else
     'במבחן הראשי אין מגמת גוש מובהקת לאחר תיקון BH. ')
    + (f"ברגישות לאחר BH נותרו: {', '.join(sensitivity_sig)}." if sensitivity_sig else
       'ברגישות של סדרות שלמות אין מגמת גוש מובהקת לאחר BH.'), '',
    '| גוש | Δ ראשון–אחרון משוקלל | מנדטים לשבוע | p ראשי | q לאחר BH | p ברגישות | q ברגישות |',
    '|---|---:|---:|---:|---:|---:|---:|',
]
for row in p['overall']:
    lines.append(f"| {groups[row['group']]} | {fmt(row['weightedNetDelta'])} | {fmt(row['slopePerWeek'])} | "
                 f"{row['pValue']:.5f} | {row['qValue']:.5f} | {row['wholeInstituteSignFlipP']:.5f} | {row['wholeInstituteSignFlipQ']:.5f} |")
old_groups = {row['group']: row for row in old_bloc['primary']['overall']}
lines += ['', '## בהשוואה לניתוח מ־6.10', '',
          '| גוש | קצב קודם לשבוע | קצב מעודכן לשבוע | q קודם | q מעודכן |', '|---|---:|---:|---:|---:|']
for row in p['overall']:
    old = old_groups[row['group']]
    lines.append(f"| {groups[row['group']]} | {fmt(old['slopePerWeek'])} | {fmt(row['slopePerWeek'])} | {old['qValue']:.5f} | {row['qValue']:.5f} |")
lines += ['', '## כל סדרת סקרים בנפרד', '',
          f"לפני תיקון: {len(p['significantIndividualRaw'])} אותות; לאחר BH על {3*p['nPollsters']} בדיקות: {len(p['significantIndividualBH'])}.", '',
          '| סדרה | גוש | סקרים | Δ ראשון–אחרון | קצב לשבוע | p | q |', '|---|---|---:|---:|---:|---:|---:|']
for series in p['byPollster']:
    for row in series['groups']:
        lines.append(f"| {names[series['pollsterId']]} | {groups[row['group']]} | {row['nPolls']} | {fmt(row['netDelta'], 0)} | "
                     f"{fmt(row['slopePerWeek'])} | {row['pValue']:.4f} | {row['qValue']:.4f} |")
lines += ['', '## דרך החישוב ומגבלות', '',
          'הקואליציה: ליכוד, ש״ס, יהדות התורה, עוצמה יהודית, הציונות הדתית–זהות, עמך ישראל ונעם. '
          'האופוזיציה ללא ערביות: ישר, ביחד, הדמוקרטים וישראל ביתנו; הגדרה נוספת מצרפת את רע״ם. '
          'הנדל–זליכה אינם משויכים לאחד הגושים.', '', *shared_method, '',
          '## שחזור וראיות', '',
          'analysis.json ו־by-pollster.csv כוללים תוצאות ומדגם; audit-strict-full-series-2026-09-28.py מבצע ספירה עצמאית. '
          'archive-2026-10-06 שומר את הבסיס הקודם; artifacts/2026-10-07-comparison/strict-trends-comparison.json מתעד את ההשוואה.', '', access_note, '']
(HERE / 'summary-he.md').write_text('\n'.join(lines), encoding='utf-8')

rows = sorted(party['primary']['overall'], key=lambda row: row['pValue'])
old_parties = {row['partyId']: row for row in old_party['primary']['overall']}
def signal_name(row):
    return f"{row['partyName']} ({'עלייה' if row['slopePerWeek'] > 0 else 'ירידה'})"


nominal = [signal_name(row) for row in rows if row['pValue'] < .05]
corrected = [signal_name(row) for row in rows if row['qValue'] < .05]
robust = [signal_name(row) for row in rows if row['wholeSeriesSignFlipQ'] < .05]
zero = [row['partyName'] for row in rows if row['zeroSeatsThroughout']]
lines = ['# מגמות ברמת המפלגה — לאחר סגירת הרשימות בלבד', '',
         f"הניתוח עודכן ב־{dated(party['asOf'])}. {fieldwork_note}", '', cohort_note, '', change_note, '',
         f"לפני תיקון נמצאו {len(nominal)} אותות: {', '.join(nominal) or 'אין'}. "
         + (f"לאחר BH על 17 מפלגות נותרו: {', '.join(corrected)}. " if corrected else
            'לאחר BH על 17 מפלגות אין מגמה מובהקת. ')
         + (f"ברגישות לאחר BH נותרו: {', '.join(robust)}." if robust else
            'ברגישות של סדרות שלמות אין מפלגה מובהקת לאחר BH.'), '',
         '| מפלגה | Δ ראשון–אחרון משוקלל | מנדטים לשבוע | p ראשי | q לאחר BH | p ברגישות | q ברגישות |',
         '|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
    lines.append(f"| {row['partyName']} | {fmt(row['weightedNetDelta'])} | {fmt(row['slopePerWeek'])} | {row['pValue']:.5f} | "
                 f"{row['qValue']:.5f} | {row['wholeSeriesSignFlipP']:.5f} | {row['wholeSeriesSignFlipQ']:.5f} |")
lines += ['', '## בהשוואה לניתוח מ־6.10', '',
          '| מפלגה | Δ קודם | Δ מעודכן | קצב קודם לשבוע | קצב מעודכן לשבוע | q קודם | q מעודכן |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
for row in rows:
    old = old_parties[row['partyId']]
    lines.append(f"| {row['partyName']} | {fmt(old['weightedNetDelta'])} | {fmt(row['weightedNetDelta'])} | "
                 f"{fmt(old['slopePerWeek'])} | {fmt(row['slopePerWeek'])} | {old['qValue']:.5f} | {row['qValue']:.5f} |")
lines += ['', '## שיטה ומגבלות', '', *shared_method, '',
          f"BH נעשה בנפרד על 17 בדיקות מפלגה ועל {17*party['primary']['nSeries']} בדיקות מפלגה×מכון. "
          f"ברמת מכון נמצאו {len(party['primary']['significantIndividualRaw'])} אותות לפני תיקון ו־"
          f"{len(party['primary']['significantIndividualBH'])} לאחריו.", '',
          f"{', '.join(zero)} קיבלו אפס מנדטים לאורך המדגם; p=1 הוא מוסכמה לסדרה קבועה. "
          'אפס מנדטים אינו אפס תמיכה. אחוזים מתחת לחסימה אינם נבדקים כאן; קפיצה מאפס לארבעה יכולה לנבוע משינוי קטן סביב הסף.', '',
          '## שחזור וראיות', '',
          'party-analysis.json, party-overall.csv, party-by-pollster.csv ו־party-independent.json שומרים תוצאות וספירה עצמאית. '
          'קובצי ביקורת האיסוף שומרים את הראיות וההחרגות. archive-2026-10-06 משמר את הבסיס הקודם; '
          'artifacts/2026-10-07-comparison/strict-trends-comparison.json שומר את ההשוואה.', '', access_note, '']
(HERE / 'party-summary-he.md').write_text('\n'.join(lines), encoding='utf-8')
print('Rendered October 7 bloc and party summaries with October 6 comparison.')
