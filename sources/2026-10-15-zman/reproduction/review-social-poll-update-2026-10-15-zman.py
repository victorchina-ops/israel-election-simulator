"""Bind the inspected illustration to two published polls, not model probabilities."""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-15-zman'
SOCIAL=ROOT/'outputs/social/2026-10-15-zman'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate_path=ART/'source/reviewed-tatika-poll.json'
new=read(candidate_path)
old=next(p for p in read(ART/'before/data/current-polls.json')['polls'] if p['pollsterId']=='tatika')
assert old['date']=='2026-10-08' and new['date']=='2026-10-15'
ids=['yashar','beyachad','yisrael_beiteinu','democrats']
assert old['seats']['yashar']==24 and new['seats']['yashar']==26
assert sum(old['seats'][p] for p in ids)==55 and sum(new['seats'][p] for p in ids)==54
assert new['fieldworkStart']=='2026-10-14' and new['fieldworkEnd']=='2026-10-15' and new['sampleSize']==500
assert new['sourceBlocSeats']['opposition']==54 and new['sourceBlocSeats']['unassigned']==4
assert read(ART/'model-comparison-validation.json')['status']=='PASS'
image=SOCIAL/'party-up-bloc-down-illustrated.png'
raw=image.read_bytes()
assert raw[:8]==b'\x89PNG\r\n\x1a\n'
width,height=struct.unpack('>II',raw[16:24])
assert width>=1000 and height>=1200
tweet=(SOCIAL/'tweet.he.txt').read_text(encoding='utf-8')
for text in ['24','26','55','54','2.8%','לא הוכחה למגמה','https://victorchina-ops.github.io/israel-election-simulator/']:
    assert text in tweet
receipt={'status':'PASS','asOf':'2026-10-15','runId':'zman','generator':'built-in image_gen',
    'output':image.name,'outputSha256':sha(image),'width':width,'height':height,
    'prompt':'prompt.txt','promptSha256':sha(SOCIAL/'prompt.txt'),
    'cleanupPrompt':'cleanup-prompt.txt','cleanupPromptSha256':sha(SOCIAL/'cleanup-prompt.txt'),
    'tweet':'tweet.he.txt','tweetSha256':sha(SOCIAL/'tweet.he.txt'),
    'candidateSha256':sha(candidate_path),'earlierPollId':old['id'],'laterPollId':new['id'],
    'earlierPollDate':old['date'],'laterPollDate':new['date'],
    'sourceUrls':[old['sourceUrl'],new['sourceUrl']],
    'rawPublishedSeatComparison':{'yashar':[24,26],'fixedOppositionExcludingHendelAndArabs':[55,54]},
    'groupMembership':ids,'significanceClaimMade':False,'weightedModelResult':False,
    'notMeasuredVoterTransfers':True,'modelComparisonSha256':sha(ART/'model-comparison.json'),
    'visualInspectionCompleted':True,
    'visualReview':['All figures26/24/+2 and54/55/−1 and8Octvs15Oct dates visually verified.',
        'Party shown as part of larger bloc; footer defines four-party grouping and separates Hendel and Arab lists.',
        'Source,14–15Oct fieldwork,n500,credit and caution that two polls are not proof of trend are legible.',
        'Cleanup removed all invented step slogans; stone surfaces now blank. Data labels unchanged.',
        'Painterly civic artwork with clear Hebrew, generous margins and no clipping.'],
    'initialDraftLocalOnly':'artifacts/poll-checks/2026-10-15-zman/social/initial-draft-local-only.png',
    'postedAutomatically':False}
out=ART/'social/render-checks.json'
body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():
    assert out.read_bytes()==body,'Preserve dated review'
else:
    out.write_bytes(body)
print(json.dumps({'status':'PASS','output':image.name,'dimensions':[width,height],'rawSeatComparisons':receipt['rawPublishedSeatComparison']}))
