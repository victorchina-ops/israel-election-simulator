"""Advance audited current entry points and publish the October 7 trend bundle."""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert (HERE / 'archive-2026-10-06/analysis.json').exists()
validation = json.loads((HERE / 'party-validation.json').read_text(encoding='utf-8'))
assert validation['passed'] and validation['asOf'] == '2026-10-07'
for name, target in (
    ('build-summary.py', 'build-summaries-2026-10-07.py'),
    ('build-party-summary.py', 'build-summaries-2026-10-07.py'),
    ('validate-current.py', 'validate-current-2026-10-07.py'),
):
    (HERE / name).write_text(
        '"""Current October 7 entry point; earlier implementation is frozen in archive-2026-10-06."""\n'
        'from pathlib import Path\nimport runpy\n\n'
        f"runpy.run_path(str(Path(__file__).with_name('{target}')), run_name='__main__')\n",
        encoding='utf-8')
public = ROOT / 'github-pages/sources/2026-10-07-trends'
public.mkdir(parents=True, exist_ok=True)
copies = {
    HERE / 'analysis.json': 'bloc-analysis.json',
    HERE / 'party-analysis.json': 'party-analysis.json',
    HERE / 'summary-he.md': 'bloc-summary-he.md',
    HERE / 'party-summary-he.md': 'party-summary-he.md',
    HERE / 'party-independent.json': 'party-independent.json',
    HERE / 'party-validation.json': 'party-validation.json',
    ROOT / 'data/strict-party-trends.json': 'party-trends.json',
}
for source, name in copies.items():
    shutil.copy2(source, public / name)
    assert source.read_bytes() == (public / name).read_bytes()
comparison = ROOT / 'artifacts/2026-10-07-comparison/strict-trends-comparison.json'
destination = ROOT / 'github-pages/sources/2026-10-07-comparison/strict-trends-comparison.json'
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(comparison, destination)
assert comparison.read_bytes() == destination.read_bytes()
print(f'Copied {len(copies)} reviewed trend artifacts and the strict before/after comparison.')
