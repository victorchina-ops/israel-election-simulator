"""Prepare date-specific helpers for a Maagar poll with unverified fieldwork."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

def write(name, value):
    (HERE / name).write_text(value, encoding='utf-8', newline='\n')

def advance(value):
    return value.replace('2026-10-05', '2026-10-06').replace('2026-10-04', '2026-10-05')

comparison = advance((HERE / 'compare-2026-10-05.py').read_text(encoding='utf-8'))
comparison = comparison.replace('October 5 N12 addition with the frozen October 4 strict audit',
    'October 6 Maagar addition with the frozen October 5 strict audit')
comparison = comparison.replace('history_midgam_geva_2026-10-06_current', 'history_maagar_mochot_2026-10-06_current')
comparison = comparison.replace("== 'midgam_geva'", "== 'maagar_mochot'")
comparison = comparison.replace('N12 October 5 is included only when original-source fieldwork dates are verified.',
    'Maagar October 6 stays excluded because its fieldwork interval is unverified; strict estimates stay unchanged.')
write('compare-2026-10-06.py', comparison)

summaries = advance((HERE / 'build-summaries-2026-10-05.py').read_text(encoding='utf-8'))
summaries = summaries.replace('October 4 audit', 'October 5 audit').replace('October 5 bloc', 'October 6 bloc')
summaries = summaries.replace('history_midgam_geva_2026-10-06_current', 'history_maagar_mochot_2026-10-06_current')
summaries = summaries.replace('סקר חדשות 12 / מדגם מ־5.10', 'סקר ערוץ 16 / מאגר מוחות מ־6.10')
summaries = summaries.replace('סקר חדשות 12 מ־5.10', 'סקר ערוץ 16 מ־6.10')
summaries = summaries.replace('סקר חדשות 12 החדש', 'סקר ערוץ 16 החדש')
summaries = summaries.replace('בהפרסום המקורי', 'במקורות שנבדקו')
summaries = summaries.replace('בהשוואה לניתוח מ־4.10', 'בהשוואה לניתוח מ־5.10')
summaries = summaries.replace('5.10.2026; אין להסיק', '6.10.2026; אין להסיק')
summaries = summaries.replace('October 4 comparison.', 'October 5 comparison.')
summaries = summaries.replace('ההחרגה אינה קביעה שהאיסוף קדם לסגירת הרשימות.',
    'ההחרגה אינה קביעה שהאיסוף קדם לסגירת הרשימות. מועד המדידה המאומת האחרון נשאר 5.10, אף שתאריך העדכון הוא 6.10.')
write('build-summaries-2026-10-06.py', summaries)

validation = advance((HERE / 'validate-current-2026-10-05.py').read_text(encoding='utf-8'))
validation = validation.replace('October 5', 'October 6')
validation = validation.replace('== 36', '== 37').replace('36 - expected_polls', '37 - expected_polls')
validation = validation.replace('history_midgam_geva_2026-10-06_current', 'history_maagar_mochot_2026-10-06_current')
validation = validation.replace("== 'midgam_geva'", "== 'maagar_mochot'")
validation = validation.replace("assert new['eligibleStrict'] and new['fieldworkStart'] == new['fieldworkEnd'] == '2026-10-06'",
    "assert not new['eligibleStrict'] and new['fieldworkStart'] is None and new['fieldworkEnd'] is None")
validation = validation.replace("(42_998_169_600 if new['eligibleStrict'] else 10_749_542_400)", "42_998_169_600")
validation = validation.replace("'newN12EligibleStrict'", "'newMaagarEligibleStrict'")
write('validate-current-2026-10-06.py', validation)

packager = advance((HERE / 'refresh-reproducers-2026-10-05.py').read_text(encoding='utf-8'))
packager = packager.replace('October 5 entry', 'October 6 entry')
write('refresh-reproducers-2026-10-06.py', packager)
print('Prepared October 6 comparison/render/validation/package helpers.')
