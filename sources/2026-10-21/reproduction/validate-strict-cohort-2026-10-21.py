"""Validate the actual21Oct cohort for correlation inputs; no p/q verdicts.

Requires both fresh primary analyses and their current strict snapshot. This
source/date/eligibility check never substitutes for the independent numeric audit.
"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1];DAY='2026-10-21';ART=ROOT/'artifacts/poll-checks'/DAY;STRICT=ROOT/'artifacts/strict-post-close'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    paths=['data/current-polls.json','data/poll-history.json','data/strict-party-trends.json','data/parties.json',
        'artifacts/strict-post-close/analysis.json','artifacts/strict-post-close/party-analysis.json',
        'artifacts/poll-checks/2026-10-21/source-plan.json','artifacts/poll-checks/2026-10-21/ingestion-validation.json']
    paths+=['artifacts/strict-post-close/'+n for n in ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json','c14-i24-fieldwork.json','c16-tatika-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']]
    hashes={p:sha(ROOT/p) for p in paths}
    current,history,snapshot,parties,bloc,party,plan,ingestion=[read(ROOT/p) for p in paths[:8]]
    assert all(d['asOf']==DAY for d in [current,history,snapshot,bloc,party,plan,ingestion])
    assert ingestion['status']=='PASS' and ingestion['sourcePlanSha256']==hashes[paths[6]]
    assert bloc['cohort']==party['cohort']
    assert bloc['historySha256']==party['historySha256']==hashes['data/poll-history.json']
    assert snapshot['provenance']['analysisSha256']==hashes['artifacts/strict-post-close/party-analysis.json']
    assert snapshot['provenance']['historySha256']==hashes['data/poll-history.json']
    manifest=read(ART/'before/manifest.json')
    assert len(current['polls'])==manifest['activePollCount']==ingestion['activePollCount']
    assert len(history['polls'])==manifest['historyPollCount']+len(plan['polls'])==ingestion['historyPollCount']
    archive={p['id']:p for p in history['polls']};cohort={p['pollId']:p for p in bloc['cohort']}
    assert len(archive)==len(history['polls']) and len(cohort)==len(bloc['cohort'])
    assert set(cohort)=={p['id'] for p in history['polls'] if p['date']>=bloc['closure']['firstEligibleFieldworkDate']}
    old={p['pollId']:p for p in read(ART/'before/artifacts/strict-post-close/analysis.json')['cohort']}
    assert all(cohort[k]==v for k,v in old.items())
    expected={};verified=[];unknown=[]
    for spec in plan['polls']:
        candidate=read(ROOT/spec['candidatePath']);assert sha(ROOT/spec['candidatePath'])==spec['candidateSha256']
        key='history_'+candidate['id']+'_current';expected[key]=spec['strictEligible']
        row=cohort[key]
        assert row['publicationDate']==candidate['date'] and row['pollsterId']==candidate['pollsterId']
        assert row['fieldworkStart']==candidate.get('fieldworkStart') and row['fieldworkEnd']==candidate.get('fieldworkEnd')
        assert row['eligibleStrict'] is spec['strictEligible']
        if spec['strictEligible']:
            assert candidate.get('fieldworkVerified') is True and spec.get('fieldworkEvidence')
            for evidence in spec['fieldworkEvidence']:assert sha(ROOT/evidence['file'])==evidence['sha256']
            verified.append(key)
        else:unknown.append(key)
    assert set(cohort)==set(old)|set(expected)
    audits=[]
    for rel in paths[8:]:
        value=read(ROOT/rel);audits.extend(value.get('rows',value.get('polls',[])))
    audited={r['pollId']:r for r in audits};assert len(audited)==len(audits) and set(audited)==set(cohort)
    for key,row in cohort.items():
        audit=audited[key];poll=archive[key]
        assert row['publicationDate']==poll['date']==audit['publicationDate']
        assert row['eligibleStrict']==bool(audit.get('eligibleStrict',audit.get('includeInStrictPostClose',False)))
        assert row['fieldworkStart']==audit.get('fieldworkStart') and row['fieldworkEnd']==audit.get('fieldworkEnd')
        if row['eligibleStrict']:assert bloc['closure']['firstEligibleFieldworkDate']<=row['fieldworkStart']<=row['fieldworkEnd']<=row['publicationDate']
    eligible=[r for r in cohort.values() if r['eligibleStrict']]
    selected=[r for r in eligible if r['pollsterId']!='next_data']
    assert len(eligible)==snapshot['coverage']['pollCount']==ingestion['fullStrict']['polls']
    assert len(selected)==ingestion['defaultWithoutChannel14']['polls']
    assert len(cohort)-len(eligible)==ingestion['fullStrict']['unknownFieldworkExcluded']
    snapshot_rows={r['pollId']:r for r in snapshot['cohort']};assert set(snapshot_rows)==set(cohort)
    for key,row in cohort.items():
        for field in ['pollsterId','publicationDate','fieldworkStart','fieldworkEnd','eligibleStrict']:assert snapshot_rows[key][field]==row[field]
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    result={'status':'PASS','asOf':DAY,'scope':'Source/date/eligibility cohort validation only; no numerical significance verdict',
        'activePolls':len(current['polls']),'historyPolls':len(history['polls']),'candidates':len(cohort),'strictEligible':len(eligible),
        'strictWithoutChannel14':len(selected),'unknownFieldworkExcluded':len(cohort)-len(eligible),
        'newEligiblePollIds':verified,'newExcludedPollIds':unknown,'inputHashes':hashes,'validatorSha256':sha(Path(__file__))}
    out=ART/'cohort-only-validation.json';body=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if out.exists():assert out.read_bytes()==body
    else:out.write_bytes(body)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
