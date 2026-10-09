"""Exercise provenance guards on disposable copies, never canonical data."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'poll-correlation' / '2026-10-09'
FILES = ['data/poll-history.json', 'data/current-polls.json',
         'data/strict-party-trends.json', 'data/parties.json',
         'data/poll-correlation.json']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(directory, script, *args):
    return subprocess.run([sys.executable, '-X', 'utf8', str(directory / 'scripts' / script), *args],
                          cwd=directory, capture_output=True, text=True, encoding='utf-8')


def require_success(result):
    assert result.returncode == 0, result.stderr


def main():
    before = {name: sha(ROOT / name) for name in FILES}
    OUT.mkdir(parents=True, exist_ok=True)
    assert OUT.resolve().is_relative_to(ROOT.resolve())
    with tempfile.TemporaryDirectory(prefix='guard-fixture-', dir=OUT) as temp:
        fixture = Path(temp)
        assert fixture.resolve().is_relative_to(OUT.resolve())
        for name in FILES:
            destination = fixture / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        for script in ['build-poll-correlation.py', 'audit-poll-correlation.py']:
            destination = fixture / 'scripts' / script
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'scripts' / script, destination)
        date = json.loads((fixture / 'data' / 'poll-correlation.json').read_text(encoding='utf-8'))['asOf']
        require_success(run(fixture, 'build-poll-correlation.py', '--as-of', date))
        require_success(run(fixture, 'audit-poll-correlation.py', '--as-of', date))
        frozen = fixture / 'artifacts' / 'poll-correlation' / date / 'reviewed'
        old = {p.name: (sha(p), p.stat().st_mtime_ns) for p in frozen.iterdir() if p.is_file()}
        require_success(run(fixture, 'build-poll-correlation.py', '--as-of', date))
        require_success(run(fixture, 'audit-poll-correlation.py', '--as-of', date))
        assert old == {p.name: (sha(p), p.stat().st_mtime_ns) for p in frozen.iterdir() if p.is_file()}
        operational = fixture / 'data' / 'poll-correlation.json'
        old_operational = sha(operational)
        history_path = fixture / 'data' / 'poll-history.json'
        history = json.loads(history_path.read_text(encoding='utf-8-sig'))
        history['notes'].append('Synthetic source-metadata revision for provenance-guard testing only.')
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        rejected = run(fixture, 'build-poll-correlation.py', '--as-of', date)
        assert rejected.returncode != 0 and 'distinct --run-id' in rejected.stderr
        assert sha(operational) == old_operational
        assert old == {p.name: (sha(p), p.stat().st_mtime_ns) for p in frozen.iterdir() if p.is_file()}
        require_success(run(fixture, 'build-poll-correlation.py', '--as-of', date, '--run-id', 'revision-1'))
        require_success(run(fixture, 'audit-poll-correlation.py', '--as-of', date, '--run-id', 'revision-1'))
        assert sha(operational) != old_operational
        assert old == {p.name: (sha(p), p.stat().st_mtime_ns) for p in frozen.iterdir() if p.is_file()}
        bad_id = run(fixture, 'build-poll-correlation.py', '--as-of', date, '--run-id', '..\\escape')
        assert bad_id.returncode != 0 and 'safe directory name' in bad_id.stderr
        wrong_date = run(fixture, 'audit-poll-correlation.py', '--as-of', '2026-10-10', '--run-id', 'revision-1')
        assert wrong_date.returncode != 0 and 'match the reviewed profile date' in wrong_date.stderr
        revision = fixture / 'artifacts' / 'poll-correlation' / date / 'revision-1'
        audit_path = revision / 'independent-audit.json'
        changed_audit = json.loads(audit_path.read_text(encoding='utf-8'))
        changed_audit['syntheticChangedReceiptForGuardTest'] = True
        audit_path.write_text(json.dumps(changed_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tampered_sha = sha(audit_path)
        audit_rejected = run(fixture, 'audit-poll-correlation.py', '--as-of', date, '--run-id', 'revision-1')
        assert audit_rejected.returncode != 0 and 'never overwritten' in audit_rejected.stderr
        assert sha(audit_path) == tampered_sha
        validation_path = revision / 'validation.json'
        changed_validation = json.loads(validation_path.read_text(encoding='utf-8'))
        changed_validation['syntheticChangedReceiptForGuardTest'] = True
        validation_path.write_text(json.dumps(changed_validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        validation_sha = sha(validation_path)
        current_sha = sha(operational)
        build_rejected = run(fixture, 'build-poll-correlation.py', '--as-of', date, '--run-id', 'revision-1')
        assert build_rejected.returncode != 0 and 'Frozen artifact differs' in build_rejected.stderr
        assert sha(validation_path) == validation_sha and sha(operational) == current_sha
    assert before == {name: sha(ROOT / name) for name in FILES}
    receipt = {'status': 'passed', 'scope': 'Disposable fixture copies only; canonical files never edited.',
               'canonicalHashesUnchanged': before,
               'identicalFrozenRunsReusedWithoutMtimeChanges': True,
               'sameDayChangedSourceRejectedBeforePromotion': True,
               'newRunIdRetainsEarlierEvidence': True,
               'unsafeRunIdRejected': True,
               'mismatchedAuditDateRejected': True,
               'changedIndependentReceiptNotOverwritten': True,
               'changedValidationReceiptRejectedBeforePromotion': True}
    target = OUT / 'provenance-guard-check.json'
    encoded = (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if target.exists() and target.read_bytes() != encoded:
        raise RuntimeError('Existing guard-check receipt differs; use a newly dated review artifact.')
    if not target.exists():
        target.write_bytes(encoded)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
