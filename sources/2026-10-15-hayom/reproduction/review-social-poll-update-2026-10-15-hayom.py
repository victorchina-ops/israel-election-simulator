"""Validate source/model distinctions and inspected Winter illustration."""
from pathlib import Path
import hashlib
import json
import math
import struct

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-15-hayom'
SOCIAL=ROOT/'outputs/social/2026-10-15-hayom'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
poll=read(ART/'source/reviewed-kantar-poll.json')
assert poll['id']=='kantar_2026-10-15' and poll['reportedPercentages']['winter']==3.0
assert poll['sampleSize']==551 and poll['fieldworkStart']=='2026-10-14' and poll['fieldworkEnd']=='2026-10-15'
comparison=read(ART/'model-comparison.json')
assert read(ART/'model-comparison-validation.json')['status']=='PASS'
after=comparison['after']
winter=next(p for p in after['parties'] if p['id']=='winter')
assert math.isclose(winter['passProbability'],.1891,rel_tol=0,abs_tol=1e-12)
assert round(100*winter['passProbability'],1)==18.9
assert after['config']['weightMode']=='quality' and after['config']['includeChannel14'] is False
assert after['config']['pollCorrelationEnabled'] is False and after['config']['signalNoiseEnabled'] is False
assert len(after['pollWeights'])==7 and all(p['pollsterId']!='next_data' for p in after['pollWeights'])
image=SOCIAL/'winter-threshold-illustrated.png'
raw=image.read_bytes()
assert raw[:8]==b'\x89PNG\r\n\x1a\n'
width,height=struct.unpack('>II',raw[16:24])
assert width>=1000 and height>=1200
tweet=(SOCIAL/'tweet.he.txt').read_text(encoding='utf-8')
for text in ['3.0%','18.9%','דיוק היסטורי','ללא ערוץ 14','הנחות המודל','https://victorchina-ops.github.io/israel-election-simulator/']:
    assert text in tweet
url=tweet.strip().splitlines()[-1]
assert len(tweet.strip())-len(url)+23<=280
receipt={
    'status':'PASS','asOf':'2026-10-15','runId':'hayom','generator':'built-in image_gen',
    'output':image.name,'outputSha256':sha(image),'width':width,'height':height,
    'prompt':'prompt.txt','promptSha256':sha(SOCIAL/'prompt.txt'),'cleanupPrompt':None,
    'tweet':'tweet.he.txt','tweetSha256':sha(SOCIAL/'tweet.he.txt'),
    'sourceUrl':poll['sourceUrl'],'candidateSha256':sha(ART/'source/reviewed-kantar-poll.json'),
    'sourcePublicationDate':'2026-10-15','fieldworkStart':'2026-10-14','fieldworkEnd':'2026-10-15','sampleSize':551,
    'modelDataDate':'2026-10-15','includesLatestIsraelHayomPoll':True,
    'reportedSupportPct':3.0,'modelPassProbabilityPct':100*winter['passProbability'],'displayedModelPassProbabilityPct':18.9,
    'modelElectoralThresholdPct':3.25,'historicalAccuracyWeighting':True,'channel14Included':False,'activeSelectedInstitutes':7,
    'modelTurnoutAssumption':'2022 baseline','statisticalSignificanceClaim':False,'provenForecastCalibrationClaim':False,
    'modelComparisonSha256':sha(ART/'model-comparison.json'),'visualInspectionCompleted':True,
    'visualReview':['Hebrew headline and party name read correctly;18.9% clearly labeled as weighted-model crossing probability.',
        'Separate card explicitly assigns3.0% to support in IsraelHayom poll; threshold3.25% on doorway plaque.',
        'Footer distinguishes probability from support; historical accuracy,7institutes,no14,turnout2022 and conditional nature readable.',
        'Model date and source fieldwork14–15Oct,n551,site URL and author credit visible; no invented slogans or clipping.'],
    'postedAutomatically':False}
out=ART/'social/render-checks.json'
out.parent.mkdir(parents=True,exist_ok=True)
body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
if out.exists():
    assert out.read_bytes()==body,'Preserve dated review'
else:
    out.write_bytes(body)
print(json.dumps({'status':'PASS','output':image.name,'dimensions':[width,height],'publishedSupportPct':3.0,'modelPassProbabilityPct':100*winter['passProbability']}))
