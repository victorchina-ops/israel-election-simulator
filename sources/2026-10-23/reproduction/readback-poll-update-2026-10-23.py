"""Compare published23Oct bytes with the complete reviewed local package."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1];DAY='2026-10-23';ART=ROOT/'artifacts/poll-checks'/DAY;REPO=ROOT/'github-pages'
BASE='https://victorchina-ops.github.io/israel-election-simulator/';PREFIX='sources/'+DAY+'/'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda b:hashlib.sha256(b).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--commit',required=True);args=parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.commit)
    release=read(ART/'publication-receipt.json');plan=read(ART/'source-plan.json')
    assert release['asOf']==plan['asOf']==DAY and release['newPollCount']==len(plan['polls'])
    paths=sorted({'index.html','README.md','.gitattributes',PREFIX+'release.json'}|{row['path'] for row in release['files']})
    def fetch(path):
        request=urllib.request.Request(BASE+urllib.parse.quote(path,safe='/')+'?release='+args.commit,headers={'User-Agent':'Election-Simulator-Release-Check','Cache-Control':'no-cache'})
        with urllib.request.urlopen(request,timeout=40) as response:body,status=response.read(),response.status
        assert status==200 and body==(REPO/path).read_bytes(),('Public byte mismatch',path,status)
        return {'path':path,'status':status,'sha256':sha(body),'bytes':len(body)},body
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(fetch,paths))
    bodies={row['path']:body for row,body in results};public=lambda name:json.loads(bodies[PREFIX+name].decode('utf-8-sig'))
    current,history=public('current-polls.json'),public('poll-history.json')
    assert current['asOf']==history['asOf']==DAY
    assert len(current['polls'])==release['activePolls'] and len(history['polls'])==release['historyPolls']
    expected={read(ROOT/s['candidatePath'])['id'] for s in plan['polls']}
    assert expected<={p['id'] for p in current['polls']}
    assert len(history['polls'])==len(read(ART/'before/data/poll-history.json')['polls'])+len(plan['polls'])
    assert all(sum(p['seats'].values())==120 for p in current['polls'])
    for name in ['strict-party-trends.json','strict-party-trends-without-channel14.json','poll-correlation.json']:assert public(name)['asOf']==DAY
    assert public('strict-party-trends.json')['coverage']['pollCount']==release['eligibleFull']
    assert public('strict-party-trends-without-channel14.json')['coverage']['pollCount']==release['eligibleWithout14']
    assert public('release.json')==release and public('source-plan.json')==plan
    html=bodies['index.html'];assert sha(html)==release['publishedHtmlSha256'] and release['snapshotSha256'].encode() in html
    assert not re.search(rb'<meta\b[^>]*\bname\s*=\s*["\x27]data-app-local-thread["\x27]',html,re.I)
    assert b'01a0952c-a40b-7b01-b019-621f0cee2656' not in html
    report={'status':'PASS','asOf':DAY,'commit':args.commit,'url':BASE,'filesVerified':len(results),'publicBytesMatchPackagedFiles':True,
        'activePolls':release['activePolls'],'historyPolls':release['historyPolls'],'defaultStrictPolls':release['eligibleWithout14'],
        'fullStrictPolls':release['eligibleFull'],'newObservationIds':sorted(expected),'snapshotSha256':release['snapshotSha256'],
        'htmlSha256':sha(html),'validatorSha256':sha(Path(__file__).read_bytes()),'rows':[row for row,body in results]}
    out=ART/'public-readback.json';assert not out.exists();out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))


if __name__=='__main__':main()
