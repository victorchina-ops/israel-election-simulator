"""Freeze the completed16Oct release before the19Oct audit of18Oct polls."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-19'
BASELINE='2026-10-16'
ART=ROOT/'artifacts/poll-checks'/DAY
BEFORE=ART/'before'
PRIOR=ROOT/'artifacts/poll-checks/2026-10-16-maariv'
EXPECTED_HEAD='d6435c05d84f1bee751e4b7c8603b92bef498d74'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def manifest():
    current,history=[read(ROOT/p) for p in ['data/current-polls.json','data/poll-history.json']]
    assert current['asOf']==history['asOf']==BASELINE
    assert len(current['polls'])==len({p['pollsterId'] for p in current['polls']})==8
    assert len(history['polls'])==len({p['id'] for p in history['polls']})==125
    assert all(sum(p['seats'].values())==120 for p in current['polls'])
    complete,published,readback=[read(PRIOR/p) for p in ['completed.json','publication-receipt.json','public-readback.json']]
    assert complete['status']==published['status']==readback['status']=='PASS'
    assert complete['receipts']['release']==sha(PRIOR/'publication-receipt.json')
    assert complete['receipts']['publicReadback']==sha(PRIOR/'public-readback.json')
    assert complete['commit']==readback['commit']==EXPECTED_HEAD
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'github-pages',text=True).strip()
    assert head==EXPECTED_HEAD
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT/'github-pages',text=True).strip()
    assert sha(ROOT/'github-pages/index.html')==published['publishedHtmlSha256']==readback['htmlSha256']
    assert sha(ROOT/'dashboard/src/data.json')==sha(ROOT/'dashboard-snapshot.json')==published['snapshotSha256']
    config=read(ROOT/'artifacts/dashboard-baseline.json')['config']
    assert config['asOf']==BASELINE and config['weightMode']=='quality'
    assert published['featuresChatGPT'] is False
    for key in ['includeChannel14','pollCorrelationEnabled','signalNoiseEnabled']:
        assert published[key] is complete['defaultConfiguration'][key] is config[key] is False
    previous=read(PRIOR/'before/manifest.json')
    categories=['authorContentHashes','protectedRuntimeHashes','frozenConditionalAndArtisticHashes','reviewedExactHelpers']
    groups={key:previous[key] for key in categories}
    assert [len(groups[k]) for k in categories]==[117,234,14,4]
    for values in groups.values():
        for rel,digest in values.items():assert sha(ROOT/rel)==digest,rel
    assert groups['reviewedExactHelpers']==published['reviewedExactHelpersUnchanged']
    public={p.relative_to(ROOT).as_posix():sha(p) for base in ['github-pages/sources','github-pages/updates'] for p in (ROOT/base).rglob('*') if p.is_file()}
    for rel,digest in previous['frozenEvidenceHashes'].items():assert public[rel]==digest,rel
    for row in published['files']:assert sha(ROOT/'github-pages'/row['path'])==row['sha256'],row['path']
    for row in readback['rows']:assert sha(ROOT/'github-pages'/row['path'])==row['sha256'],row['path']
    assert len(public)>=len(previous['frozenEvidenceHashes'])+len(published['files'])
    fixed=['AGENTS.md','dashboard/src/data.json','dashboard-snapshot.json','artifacts/dashboard-baseline.json','dashboard/protected-runtime.json','github-pages/index.html','github-pages/README.md','github-pages/.gitattributes']
    paths={ROOT/p for p in fixed}
    paths.update((ROOT/'data').glob('*.json'))
    paths.update(p for p in (ROOT/'scripts').iterdir() if p.is_file())
    paths.update(p for p in (ROOT/'artifacts/strict-post-close').iterdir() if p.is_file())
    paths.update(p for p in PRIOR.rglob('*') if p.is_file() and not p.is_relative_to(PRIOR/'before'))
    paths.update(ROOT/rel for values in groups.values() for rel in values)
    paths.update(ROOT/rel for rel in public)
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
    return dict(baselineAsOf=BASELINE,baselineVersion=current['version'],updateDate=DAY,runId='reviewed',activePollCount=8,historyPollCount=125,publishedHead=head,publishedSnapshotSha256=published['snapshotSha256'],files=files,**groups,frozenEvidenceHashes=public,exactHelperReview=previous['exactHelperReview'],authorContentHashSource=previous['authorContentHashSource'],publishedReleaseReceipt={'source':(PRIOR/'publication-receipt.json').relative_to(ROOT).as_posix(),'sha256':sha(PRIOR/'publication-receipt.json')},scope='Completed16Oct release frozen before19Oct audit; source publication dates remain18Oct when independently verified. No previous release or evidence is overwritten.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--freeze',action='store_true')
    args=parser.parse_args();value=manifest();body=encoded(value);digest=hashlib.sha256(body).hexdigest()
    assert not (BEFORE/'manifest.json').exists(),'Never overwrite a completed checkpoint'
    assert not BEFORE.exists() or not any(BEFORE.iterdir()),'Do not reuse a partial checkpoint'
    ART.mkdir(parents=True,exist_ok=True)
    if args.freeze:
        preflight=read(ART/'checkpoint-preflight.json')
        assert preflight['status']=='PASS' and preflight['proposedManifestSha256']==digest
        for rel,expected in value['files'].items():
            target=BEFORE/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target)
            assert sha(target)==expected
        assert all(sha(ROOT/p)==h for p,h in value['files'].items())
        (BEFORE/'manifest.json').write_bytes(body)
    result={'status':'PASS','asOf':DAY,'baselineAsOf':BASELINE,'mode':'freeze' if args.freeze else 'check','runId':'reviewed','activePollCount':8,'historyPollCount':125,'publishedHead':value['publishedHead'],'proposedManifestSha256':digest,'manifestSha256':sha(BEFORE/'manifest.json') if args.freeze else None,'files':len(value['files']),'authorFiles':len(value['authorContentHashes']),'protectedRuntimeFiles':len(value['protectedRuntimeHashes']),'frozenEvidenceFiles':len(value['frozenEvidenceHashes']),'frozenConditionalAndArtisticFiles':len(value['frozenConditionalAndArtisticHashes']),'reviewedExactHelpers':value['reviewedExactHelpers']}
    output=ART/('checkpoint-freeze.json' if args.freeze else 'checkpoint-preflight.json')
    if output.exists():assert output.read_bytes()==encoded(result)
    else:output.write_bytes(encoded(result))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
