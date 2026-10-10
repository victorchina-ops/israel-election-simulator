"""Create date-specific trend helpers without altering the statistical method."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

def write(name, value):
    (HERE / name).write_text(value, encoding='utf-8', newline='\n')

comparison = (HERE / 'compare-2026-10-04.py').read_text(encoding='utf-8')
comparison = comparison.replace('October 4 Kan addition with the frozen October 2 strict audit',
    'October 5 N12 addition with the frozen October 4 strict audit')
comparison = comparison.replace("'2026-10-04'", "'2026-10-05'")
comparison = comparison.replace("'2026-10-02'", "'2026-10-04'")
comparison = comparison.replace('archive-2026-10-02', 'archive-2026-10-04')
comparison = comparison.replace('history_kantar_2026-10-04_current', 'history_midgam_geva_2026-10-05_current')
comparison = comparison.replace("== 'kantar'", "== 'midgam_geva'")
comparison = comparison.replace('Kan October 4', 'N12 October 5')
comparison = comparison.replace('artifacts/2026-10-04-comparison', 'artifacts/2026-10-05-comparison')
write('compare-2026-10-05.py', comparison)

summaries = (HERE / 'build-summaries-2026-10-04.py').read_text(encoding='utf-8')
summaries = summaries.replace('October 2', 'October 4').replace('October 4 bloc', 'October 5 bloc')
summaries = summaries.replace("'2026-10-04'", "'2026-10-05'")
summaries = summaries.replace("'2026-10-02'", "'2026-10-04'")
summaries = summaries.replace('archive-2026-10-02', 'archive-2026-10-04')
summaries = summaries.replace('history_kantar_2026-10-04_current', 'history_midgam_geva_2026-10-05_current')
summaries = summaries.replace('סקר כאן / קנטאר מ־4.10', 'סקר חדשות 12 / מדגם מ־5.10')
summaries = summaries.replace('סקר כאן מ־4.10', 'סקר חדשות 12 מ־5.10')
summaries = summaries.replace('סקר כאן החדש', 'סקר חדשות 12 החדש')
summaries = summaries.replace('קטע השידור המקורי', 'הפרסום המקורי')
summaries = summaries.replace('בהשוואה לניתוח מ־2.10', 'בהשוואה לניתוח מ־4.10')
summaries = summaries.replace('artifacts/2026-10-04-comparison', 'artifacts/2026-10-05-comparison')
summaries = summaries.replace('4.10.2026', '5.10.2026')
write('build-summaries-2026-10-05.py', summaries)

validation = (HERE / 'validate-current-2026-10-04.py').read_text(encoding='utf-8')
validation = validation.replace('October 4', 'October 5').replace('2026-10-04', '2026-10-05')
validation = validation.replace('== 35', '== 36').replace('35 - expected_polls', '36 - expected_polls')
validation = validation.replace('history_kantar_2026-10-05_current', 'history_midgam_geva_2026-10-05_current')
validation = validation.replace("== 'kantar'", "== 'midgam_geva'")
validation = validation.replace("'newKanEligibleStrict'", "'newN12EligibleStrict'")
validation = validation.replace("expected_polls = 28 + int(new['eligibleStrict'])", "assert new['eligibleStrict'] and new['fieldworkStart'] == new['fieldworkEnd'] == '2026-10-05'\nexpected_polls = 29")
write('validate-current-2026-10-05.py', validation)

packager = (HERE / 'refresh-reproducers-2026-10-04.py').read_text(encoding='utf-8')
packager = packager.replace('archive-2026-10-02', 'archive-2026-10-04')
packager = packager.replace('2026-10-04.py', '2026-10-05.py')
packager = packager.replace('October 4 entry', 'October 5 entry')
packager = packager.replace('sources/2026-10-04', 'sources/2026-10-05')
packager = packager.replace('artifacts/2026-10-04-comparison', 'artifacts/2026-10-05-comparison')
write('refresh-reproducers-2026-10-05.py', packager)
print('Prepared four October 5 compare/render/validate/package helpers.')
