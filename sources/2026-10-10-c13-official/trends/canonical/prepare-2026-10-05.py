"""Preserve the reviewed October 4 strict audit before the next poll update."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
archive = HERE / 'archive-2026-10-04'
assert json.loads((HERE / 'analysis.json').read_text(encoding='utf-8'))['asOf'] == '2026-10-04'
assert json.loads((HERE / 'party-analysis.json').read_text(encoding='utf-8'))['asOf'] == '2026-10-04'
assert not archive.exists(), 'Do not overwrite a frozen audit.'
archive.mkdir()
files = {}
for source in HERE.iterdir():
    if not source.is_file() or '2026-10-05' in source.name:
        continue
    destination = archive / source.name
    shutil.copy2(source, destination)
    assert destination.read_bytes() == source.read_bytes()
    files[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
snapshot = ROOT / 'data/strict-party-trends.json'
shutil.copy2(snapshot, archive / 'published-party-trends.json')
files['published-party-trends.json'] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
(archive / 'manifest.json').write_text(json.dumps({
    'asOf': '2026-10-04', 'frozenBefore': '2026-10-05', 'files': files,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Preserved {len(files)} reviewed strict files for October 4.')
