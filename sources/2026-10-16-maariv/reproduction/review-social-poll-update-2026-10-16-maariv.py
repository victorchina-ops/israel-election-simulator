"""Bind the inspected Maariv illustration to raw reported bloc comparisons.

Run after visually inspecting the final PNG. The8October comparison is a
user-supplied report column, not the previous active13October model input.
"""
from pathlib import Path
import hashlib
import json
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-16-maariv'
SOCIAL=ROOT/'outputs/social/2026-10-16-maariv'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(ART/'source-plan.json')
assert plan['status']=='reviewed' and plan['asOf']=='2026-10-16'
assert len(plan['polls'])==1 and plan['polls'][0]['pollsterId']=='lazar'
spec=plan['polls'][0]
candidate_path=ROOT/spec['candidatePath']
assert sha(candidate_path)==spec['candidateSha256']
poll=read(candidate_path)
assert poll['id']=='lazar_2026-10-16' and poll['sourceTier']=='secondary-aggregator'
assert poll['firstPublisherPublicationVerified'] is False
assert poll['firstPublisherPublicationDate'] is None and poll['firstPublisherArticleUrl'] is None
assert poll['date']=='2026-10-16' and poll['fieldworkStart'] is None and poll['fieldworkEnd'] is None and poll['sampleSize'] is None
assert poll['sourceBlocSeats']=={'coalition':51,'opposition':51,'arab_parties':14,'hendel':4}
assert poll['publishedPreviousPollDate']=='2026-10-08'
assert poll['publishedPreviousBlocSeats']=={'coalition':52,'opposition':52,'arab_parties':12,'hendel':4}
assert poll['publishedPreviousComparisonProvenance']['sourceKind']=='user-provided-original-report-image-only'
assert poll['publishedPreviousComparisonProvenance']['verifiedInIsraelPollsImages'] is False
assert sum(poll['seats'].values())==120
assert not any(pid in poll['reportedPercentages'] for pid in ['winter','hendel'])
before=next(p for p in read(ART/'before/data/current-polls.json')['polls'] if p['pollsterId']=='lazar')
assert poll['replacesPollId']==before['id'] and before['date']=='2026-10-13'
assert read(ART/'model-comparison-validation.json')['status']=='PASS'
image=SOCIAL/'bloc-tie-arab-gain-illustrated.png'
raw=image.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
width,height=struct.unpack('>II',raw[16:24]);assert width>=1000 and height>=1200
tweet=(SOCIAL/'tweet.he.txt').read_text(encoding='utf-8')
for text in ['51','14','52','12','8.10','16.10','https://victorchina-ops.github.io/israel-election-simulator/']:
    assert text in tweet,text
assert len(re.sub(r'https?://\S+','x'*23,tweet.strip()))<=280
prompt=SOCIAL/'prompt.txt'
assert 'FINAL TARGETED EDIT' in prompt.read_text(encoding='utf-8')
receipt={
    'status':'PASS','asOf':'2026-10-16','runId':'reviewed','generator':'built-in image_gen',
    'output':image.name,'outputSha256':sha(image),'width':width,'height':height,
    'prompt':prompt.name,'promptSha256':sha(prompt),
    'cleanupPrompt':prompt.name,'cleanupPromptSha256':sha(prompt),'cleanupPromptSection':'FINAL TARGETED EDIT',
    'tweet':'tweet.he.txt','tweetSha256':sha(SOCIAL/'tweet.he.txt'),
    'candidatePath':spec['candidatePath'],'candidateSha256':sha(candidate_path),
    'sourceUrl':poll['sourceUrl'],'sourceTier':poll['sourceTier'],
    'checkedAndFirstObservedDate':'2026-10-16','firstPublisherPublicationDateVerified':False,
    'sourceRepostPublishedAtUtc':poll['sourceRepostPublishedAtUtc'],
    'fieldworkVerified':False,'sampleSize':None,
    'comparisonLabel':'8October column in the user-supplied numerical report',
    'comparisonDate':'2026-10-08','comparisonUserReportOnly':True,
    'rawReportedBlocComparison':{key:[poll['publishedPreviousBlocSeats'][key],poll['sourceBlocSeats'][key]] for key in ['coalition','opposition','arab_parties','hendel']},
    'winterAssignedToCoalition':True,'hendelSeparate':True,
    'activeModelReplacementPollId':before['id'],'activeModelReplacementDate':before['date'],
    'notModelBeforeAfterComparison':True,'notMeasuredVoterTransfers':True,
    'weightedModelResultShown':False,'statisticalSignificanceClaim':False,
    'modelComparisonSha256':sha(ART/'model-comparison.json'),
    'visualInspectionCompleted':True,
    'visualReview':[
        'Each bloc has a clear current value and8October report-column comparison: coalition52→51, opposition52→51, Arab lists12→14, Hendel4→4.',
        'Current51/51/14/4 and earlier52/52/12/4 both sum120; Winter is included with coalition and Hendel is separate.',
        '16October is explicitly a checked/observed date, not a verified first-publisher date; comparison is identified as a report column.',
        'Caption distinguishes raw poll data from model forecast and trend test; no significance or measured voter-transfer claim appears.',
        'Source attribution, simulator link and small author credit are legible; painterly artwork has no data-label clipping or invented slogans.',
        'Final targeted edit, recorded in the FINAL TARGETED EDIT section of prompt.txt, removed unintended book titles/slogan while retaining all main numbers.',
    ],
    'postedAutomatically':False,
}
out=ART/'social/render-checks.json';out.parent.mkdir(parents=True,exist_ok=True)
body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
if out.exists():assert out.read_bytes()==body,'Preserve immutable social review.'
else:out.write_bytes(body)
print(json.dumps({'status':'PASS','output':image.name,'dimensions':[width,height],'rawBlocComparison':receipt['rawReportedBlocComparison']}))
