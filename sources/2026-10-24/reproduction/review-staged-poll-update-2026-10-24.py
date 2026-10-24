"""Review exact staged24Oct paths and checksum-bound original formatting."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1];DAY='2026-10-24';ART=ROOT/'artifacts/poll-checks'/DAY;REPO=ROOT/'github-pages'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.run(['git','-C',str(REPO),*args],check=True,capture_output=True).stdout


def main():
    release=read(ART/'publication-receipt.json');manifest=read(ART/'before/manifest.json');plan=read(ART/'source-plan.json')
    assert release['status']=='PASS' and release['asOf']==DAY
    assert git('rev-parse','HEAD').decode().strip()==manifest['publishedHead']
    expected={'index.html','README.md','.gitattributes','sources/'+DAY+'/release.json'}|{r['path'] for r in release['files']}
    actual=set(git('diff','--cached','--name-only','-z').decode().strip('\0').split('\0'))
    assert actual==expected,{'missing':sorted(expected-actual),'extra':sorted(actual-expected)}
    assert not git('diff','--cached','--name-only','--diff-filter=D').strip()
    run=subprocess.run(['git','-C',str(REPO),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],capture_output=True)
    diagnostics=[line for line in run.stdout.decode('utf-8').splitlines() if line and not line.startswith('+')]
    assert not run.stderr and run.returncode==(2 if diagnostics else 0)
    assert len(diagnostics)==len(set(diagnostics))
    allowed_hashes=dict(manifest['files'])
    for spec in plan['polls']:
        for item in spec['publicFiles']:allowed_hashes[item['sourcePath']]=item['sha256']
    for item in plan.get('sourceReview',{}).get('publicFiles',[]):allowed_hashes[item['sourcePath']]=item['sha256']
    for item in release['additionalSourceEvidence']:
        assert item['publicPath'] in expected
        assert sha((ROOT/item['sourcePath']).read_bytes())==sha((REPO/item['publicPath']).read_bytes())==item['sha256']
        allowed_hashes[item['sourcePath']]=item['sha256']
    pinned={row['path']:row['sha256'] for row in release['files']};allowed=[]
    for row in release['whitespaceEvidence']:
        assert allowed_hashes.get(row['sourcePath'])==row['sha256']
        assert sha((ROOT/row['sourcePath']).read_bytes())==sha((REPO/row['path']).read_bytes())==sha(git('show',':'+row['path']))==pinned[row['path']]==row['sha256']
        assert all(line.startswith(row['path']+':') and line.endswith(('new blank line at EOF.','trailing whitespace.')) for line in row['diagnostics'])
        allowed.extend(row['diagnostics'])
    assert set(diagnostics)==set(allowed),{'unapproved':sorted(set(diagnostics)-set(allowed)),'missing':sorted(set(allowed)-set(diagnostics))}
    rows=[]
    for name in sorted(actual):
        body=(REPO/name).read_bytes();assert body==git('show',':'+name)
        if name in pinned:assert sha(body)==pinned[name]
        rows.append({'path':name,'sha256':sha(body),'bytes':len(body)})
    for group in ['authorContentHashes','protectedRuntimeHashes','frozenEvidenceHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']:
        for rel,digest in manifest[group].items():assert sha((ROOT/rel).read_bytes())==digest
    assert sha((REPO/'index.html').read_bytes())==release['publishedHtmlSha256']
    assert read(REPO/'sources'/DAY/'release.json')==release
    report={'status':'PASS','asOf':DAY,'stagedFileCount':len(rows),'baselineCommit':manifest['publishedHead'],
        'publicationReceiptSha256':sha((ART/'publication-receipt.json').read_bytes()),'exactAllowedPathSet':True,
        'stagedBytesEqualPackagedFiles':True,'noDeletedFiles':True,'preservedExactPinnedWhitespaceDiagnostics':diagnostics,
        'validatorSha256':sha(Path(__file__).read_bytes()),'rows':rows}
    out=ART/'staged-review.json';assert not out.exists();out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))


if __name__=='__main__':main()
