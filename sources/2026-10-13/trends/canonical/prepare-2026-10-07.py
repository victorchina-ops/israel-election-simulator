"""Freeze the reviewed October 6 analysis and its public bundles before October 7."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
archive = HERE / 'archive-2026-10-06'
for name in ('analysis.json', 'party-analysis.json'):
    assert json.loads((HERE / name).read_text(encoding='utf-8'))['asOf'] == '2026-10-06'
assert not archive.exists(), 'Never overwrite a frozen audit.'
archive.mkdir()
files = {}


def preserve(source, relative):
    destination = archive / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert destination.read_bytes() == source.read_bytes()
    files[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()


for source in HERE.iterdir():
    if source.is_file() and '2026-10-07' not in source.name:
        preserve(source, Path(source.name))
preserve(ROOT / 'data/strict-party-trends.json', Path('published-party-trends.json'))
for label, source_dir in (
    ('public-trends', ROOT / 'github-pages/sources/2026-10-06-trends'),
    ('public-comparison', ROOT / 'github-pages/sources/2026-10-06-comparison'),
):
    assert source_dir.is_dir()
    for source in sorted(source_dir.rglob('*')):
        if source.is_file():
            preserve(source, Path(label) / source.relative_to(source_dir))
(archive / 'manifest.json').write_text(json.dumps({
    'asOf': '2026-10-06', 'frozenBefore': '2026-10-07', 'files': files,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
for filename, checksum in files.items():
    assert hashlib.sha256((archive / filename).read_bytes()).hexdigest() == checksum
print(f'Preserved {len(files)} reviewed strict and public files for October 6.')
