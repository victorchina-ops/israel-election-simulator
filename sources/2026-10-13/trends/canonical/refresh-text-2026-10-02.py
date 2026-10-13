"""Refresh dated strict report renderers without changing the statistical design."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
bloc=HERE/'build-summary.py'
text=bloc.read_text(encoding='utf-8-sig')
text=text.replace('archive-2026-09-30/analysis.json','archive-2026-10-01/analysis.json')
text=text.replace('source = next(row for row in eligible if row["pollsterId"] == "tatika" and row["publicationDate"] == "2026-10-01")', 'prior_ids = {row["pollId"] for row in prior["cohort"]}\nadded = [row for row in eligible if row["pollId"] not in prior_ids]\nadded_links = ", ".join(f"[{names[row[\'pollsterId\']]}]({row[\'sourceUrl\']})" for row in added)')
start=text.index('    f"הניתוח עודכן')
end=text.index('    "",\n    "## חלון הזמנים"',start)
text=text[:start]+'''    f"הניתוח עודכן ב־{dated(r['asOf'])} עם שלושה סקרים מאומתים: {added_links}. "
    + (f"במבחן הפרמוטציות הראשי התקבל אות לאחר תיקון לריבוי בדיקות בגושים: {', '.join(main_sig)}. " if main_sig else "במבחן הראשי לא נותרה מגמת גוש מובהקת לאחר תיקון לריבוי בדיקות. ")
    + "יש לקרוא את התוצאות לצד בדיקת הרגישות של היפוך כיוון סדרות שלמות; אין להציג מובהקות נומינלית כהוכחה חד־משמעית לשינוי באוכלוסייה.",
'''+text[end:]
text=text.replace('בהשוואה לניתוח השמור מ־30.9','בהשוואה לניתוח השמור מ־1.10')
text=text.replace('המשקלים, הגדרת הגושים וששת הסקרים שהוחרגו נותרו זהים; השינוי במדגם המחמיר הוא סקר טאטיקה המאומת בלבד.', 'המשקלים, הגדרת הגושים וששת הסקרים שהוחרגו נותרו זהים; נוספו סקרי חדשות 14 ו־i24 מ־1.10 וסקר מעריב מ־2.10.')
text=text.replace('    "אף סדרה אינה מובהקת לפני התיקון.",', '    f"מספר ממצאים ברמת סדרה לפני תיקון: {len(p[\'significantIndividualRaw\'])}; לאחר BH: {len(p[\'significantIndividualBH\'])}.",')
text=text.replace('archive-2026-09-30 שומר את נתוני הבסיס והניתוח הקודם; comparison-2026-10-01.json משווה את שני המצבים.', 'archive-2026-10-01 שומר את כל קובצי האיסוף והניתוח הקודם; artifacts/2026-10-02-comparison/strict-trends-comparison.json משווה את שני המצבים.')
text=text.replace('[IsraelPolls](https://x.com/IsraelPolls?s=20) לא היה נגיש בבדיקה הנוכחית, ולכן הגרפיקה והטבלאות ההיסטוריות שלו לא נבדקו.', '[IsraelPolls](https://x.com/IsraelPolls?s=20) נפתח בבדיקה הנוכחית; גרפיקות המנדטים והטבלאות ההיסטוריות של הסקרים החדשים נבדקו מול המקורות המקוריים. כלי קריאת הרשת נכשל, אך גישת HTTP ישירה הצליחה.')
bloc.write_text(text,encoding='utf-8')

party=HERE/'build-party-summary.py'
text=party.read_text(encoding='utf-8-sig')
text=text.replace('archive-2026-09-30/party-analysis.json','archive-2026-10-01/party-analysis.json')
start=text.index('    "הניתוח עודכן')
end=text.index('    f"יש {len(nominal)}',start)
text=text[:start]+'''    f"הניתוח עודכן ב־{dated(report['asOf'])} עם סקרי חדשות 14 ו־i24 מ־1.10 ומעריב מ־2.10. "
'''+text[end:]
text=text.replace('בהשוואה לניתוח מ־30.9, השינוי המשוקלל של המילואימניקים והכלכלית עלה', 'בהשוואה לניתוח מ־1.10, השינוי המשוקלל של המילואימניקים והכלכלית השתנה')
text=text.replace('זו תוצאה של הוספת סקר טאטיקה המאומת תוך שמירה על אותם משקלים ושאר הסדרות.', 'ההשוואה שומרת על אותם משקלים ומוסיפה שלושה סקרים עם מועדי איסוף מאומתים.')
text=text.replace('    "לא נותרה מגמה מובהקת ברגישות לאחר תיקון ל־17 מפלגות.",', '    f"מספר המגמות המובהקות ברגישות לאחר תיקון ל־17 מפלגות: {sum(row[\'wholeSeriesSignFlipQ\'] < .05 for row in rows)}.",')
text=text.replace('    "גם ברמת סדרה בודדת אין מפלגה מובהקת לפני תיקון.",', '    f"ממצאים ברמת סדרה בודדת לפני תיקון: {len(primary[\'significantIndividualRaw\'])}; לאחר BH: {len(primary[\'significantIndividualBH\'])}.",')
text=text.replace('archive-2026-09-30 משמר את הניתוח הקודם ו־comparison-2026-10-01.json משווה בין שני המצבים.', 'archive-2026-10-01 משמר את כל קובצי האיסוף והניתוח הקודם; artifacts/2026-10-02-comparison/strict-trends-comparison.json משווה בין שני המצבים.')
text=text.replace('[IsraelPolls](https://x.com/IsraelPolls?s=20) לא היה נגיש בבדיקה הנוכחית; הגרפיקה והטבלאות ההיסטוריות שלו לא נבדקו.', '[IsraelPolls](https://x.com/IsraelPolls?s=20) נפתח בבדיקה הנוכחית, כולל גרפיקות וטבלאות היסטוריות; כלי קריאת הרשת נכשל אך גישת HTTP ישירה הצליחה.')
party.write_text(text,encoding='utf-8')
print('Strict renderers refreshed for October 2 and data-driven significance statements.')
