"""Read-only verification of the exact already staged public release."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT/'github-pages'
ART=ROOT/'artifacts/poll-checks/2026-10-19'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.run(['git','-C',str(REPO),*args],check=True,capture_output=True).stdout
release=read(ART/'publication-receipt.json')
manifest=read(ART/'before/manifest.json')
assert release['status']=='PASS' and release['asOf']=='2026-10-19'
assert git('rev-parse','HEAD').decode().strip()==manifest['publishedHead']
expected={'index.html','README.md','.gitattributes','sources/2026-10-19/release.json'}
expected.update(row['path'] for row in release['files'])
actual=set(git('diff','--cached','--name-only','-z').decode().strip('\0').split('\0'))
assert actual==expected, {'missing':sorted(expected-actual),'extra':sorted(actual-expected)}
assert not git('diff','--cached','--name-only','--diff-filter=D').strip()
# Evidence files intentionally retain their checksum-pinned Windows CRLF bytes.
# Accept CR as line endings while retaining Git's other whitespace checks.
whitespace=subprocess.run(['git','-C',str(REPO),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],capture_output=True)
diagnostics=[line for line in whitespace.stdout.decode('utf-8').splitlines() if not line.startswith('+')]
allowed_blank_eof={line for line in diagnostics if line.endswith('new blank line at EOF.') and line.startswith('sources/2026-10-19/reproduction/compare-poll-update.mjs:')}
if allowed_blank_eof:
    assert sha((ROOT/'scripts/compare-poll-update.mjs').read_bytes()) == manifest['files']['scripts/compare-poll-update.mjs']
assert set(diagnostics)<=allowed_blank_eof, diagnostics
assert whitespace.returncode in {0,2}
rows=[]
for name in sorted(actual):
    local=(REPO/name).read_bytes()
    staged=git('show',':'+name)
    assert staged==local, ('Staged bytes differ',name)
    rows.append({'path':name,'sha256':sha(local),'bytes':len(local)})
for family in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']:
    for name,digest in manifest[family].items():
        assert sha((ROOT/name).read_bytes())==digest, (family,name)
assert sha((ROOT/'dashboard/src/data.json').read_bytes())==release['snapshotSha256']
assert sha((REPO/'index.html').read_bytes())==release['publishedHtmlSha256']
assert read(REPO/'sources/2026-10-19/release.json')==release
assert sha((ART/'source-plan.json').read_bytes())==release['sourcePlanSha256']
report={'status':'PASS','asOf':'2026-10-19','stagedFileCount':len(rows),
    'baselineCommit':manifest['publishedHead'],'publicationReceiptSha256':sha((ART/'publication-receipt.json').read_bytes()),
    'exactAllowedPathSet':True,'stagedBytesEqualPackagedFiles':True,'priorPublicFilesUnchanged':len(manifest['frozenEvidenceHashes']),
    'noDeletedFiles':True,'preservedSourceOnlyBlankEofDiagnostics':diagnostics,'rows':rows}
out=ART/'staged-review.json'
assert not out.exists(),'Preserve dated review'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
