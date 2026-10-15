"""Bind the visually inspected original illustration to source-only turnout facts.

These descriptive figures do not alter model turnout or establish significance.
Run after model comparison to bind this social package to the same release.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/poll-checks/2026-10-15'
SOCIAL = ROOT / 'outputs/social/2026-10-15-poll-update'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
aux_path = ART / 'tv-primary/c13-auxiliary-facts.json'
aux = read(aux_path)
assert aux['sampleSizeTotal'] == 1018 and aux['subgroupSampleSizes'] is None
assert aux['notMandateInput'] is True
intent = aux['voteIntentCertainty']
assert intent['oppositionPct'] == 84 and intent['coalitionPct'] == 76
assert intent['isActualTurnoutEstimate'] is False
candidate_path = ART / 'tv-primary/reviewed-c13-poll.json'
candidate = read(candidate_path)
assert candidate['date'] == '2026-10-14' and candidate['fieldworkStart'] == candidate['fieldworkEnd'] == '2026-10-13'
assert candidate['sampleSize'] == 1018 and candidate['publishedPreviousBlocSeats']['coalition'] == 55
assert candidate['sourceBlocSeats']['coalition'] == 51
assert read(ART / 'model-comparison-validation.json')['status'] == 'PASS'
image = SOCIAL / 'turnout-intention-illustrated.png'
raw = image.read_bytes()
assert raw[:8] == b'\x89PNG\r\n\x1a\n'
width, height = struct.unpack('>II', raw[16:24])
assert width >= 1000 and height >= 1200
tweet = (SOCIAL / 'tweet.he.txt').read_text(encoding='utf-8')
for text in ['84%', '76%', '51', '55', 'מובהקותו לא נבדקה', 'https://victorchina-ops.github.io/israel-election-simulator/']:
    assert text in tweet
receipt = {
    'status':'PASS', 'asOf':'2026-10-15', 'generator':'built-in image_gen',
    'output':image.name, 'outputSha256':sha(image), 'width':width, 'height':height,
    'prompt':'prompt.txt', 'promptSha256':sha(SOCIAL / 'prompt.txt'), 'cleanupPrompt':None,
    'tweet':'tweet.he.txt', 'tweetSha256':sha(SOCIAL / 'tweet.he.txt'),
    'sourceAuxiliaryFactsPath':aux_path.relative_to(ROOT).as_posix(), 'sourceAuxiliaryFactsSha256':sha(aux_path),
    'candidateSha256':sha(candidate_path), 'sourceUrl':aux['sourceUrl'],
    'publicationDate':'2026-10-14', 'fieldworkDate':'2026-10-13',
    'finding':{'oppositionDefiniteVotePct':84,'coalitionDefiniteVotePct':76,'descriptiveGapPercentagePoints':8},
    'sampleSizeWholeSurvey':1018, 'subgroupSampleSizes':None,
    'significanceTested':False, 'actualTurnoutForecast':False, 'weightedModelResult':False,
    'modelTurnoutSettingsUnchanged':True, 'modelComparisonSha256':sha(ART / 'model-comparison.json'),
    'visualInspectionCompleted':True,
    'visualReview':['Hebrew headline, group labels and 84%/76% numbers read correctly.',
        'Eight percentage points, publication/fieldwork dates, whole-sample 1,018 and author credit are legible.',
        'Image explicitly says stated intent, not actual turnout; significance untested; subgroup sizes unpublished.',
        'Original painted civic illustration; neutral equally dignified ballot characters; ample margins, no clipping.'],
    'postedAutomatically':False
}
out = ART / 'social/render-checks.json'
out.parent.mkdir(parents=True,exist_ok=True)
body = (json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
if out.exists():
    assert out.read_bytes() == body, 'Preserve dated review receipt'
else:
    out.write_bytes(body)
print(json.dumps({'status':'PASS','output':image.name,'dimensions':[width,height],'sourceGapPercentagePoints':8}))
