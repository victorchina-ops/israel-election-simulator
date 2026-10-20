"""Bind independently inspected evening PNG pixels to the official replay.

Without --finalize, validate official source/prompt/tweet bindings only. The
final social release receipt requires the separately supplied render hash.
This does not perform automated visual inspection or rerun the model.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/poll-checks/2026-10-20-evening'
SOCIAL = ROOT / 'outputs/social/2026-10-20-evening'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PNG_SHA = 'fbbf460b86379be466be6280f59e634c3b67538ebd62a36f8b4aa864c20e477a'
VISUAL_SHA = 'acff5a75343a5017a13c31591f56268b6903428e17fd55eae2766eecdbae4048'
MATCH_SHA = 'f3d114b08ff5c1c6069b73009195baa73414ddaef66b54c695470b3c849e7823'
TWEET_SHA = 'b1d46477e2ab63b91714722f11b180a7d06cb64feaaf6bf4a55a716489589def'


def freeze(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    assert not path.exists() or path.read_bytes() == body, 'Preserve immutable social review'
    if not path.exists():
        path.write_bytes(body)


def source_checks():
    visual_path = ART / 'social/preliminary-visual-review-model-preview.json'
    match_path = ART / 'official-preview-replay-match.json'
    assert sha(visual_path) == VISUAL_SHA and sha(match_path) == MATCH_SHA
    visual, match = read(visual_path), read(match_path)
    assert visual['status'] == 'PASS-VISUAL-MODEL-PREVIEW-ONLY'
    assert all(visual['pixelChecks'].values())
    assert match['status'] == 'PASS' and match['asOf'] == '2026-10-20'
    assert match['imageSha256'] == visual['pngSha256'] == PNG_SHA
    assert sha(ROOT / 'dashboard/src/data.json') == match['officialSnapshotSha256']
    official_path = ART / 'model-comparison-similarity.after-replay.json'
    preview_path = ART / 'model-working/model-comparison-similarity.after-replay.json'
    assert sha(official_path) == match['officialReplaySha256']
    assert sha(preview_path) == match['isolatedReplaySha256']
    official, preview = read(official_path), read(preview_path)
    assert official['input'] == preview['input'] and official['config'] == preview['config']
    official_result, preview_result = dict(official['result']), dict(preview['result'])
    official_result.pop('generatedAt'); preview_result.pop('generatedAt')
    assert official_result == preview_result
    review_path = ART / 'model-comparisons-independent-review.json'
    assert sha(review_path) == match['officialIndependentModelReviewSha256']
    assert read(review_path)['status'] == 'PASS'
    assert sha(ART / 'source-plan.json') == match['sourcePlanSha256']
    comparison_path = ART / 'model-comparison-similarity.json'
    comparison = read(comparison_path)
    assert comparison['status'] == 'passed'
    assert comparison['after']['config'] == official['config']
    cfg = official['config']
    assert cfg['asOf'] == '2026-10-20' and cfg['weightMode'] == 'quality'
    assert cfg['pollCorrelationEnabled'] is True
    assert cfg['includeChannel14'] is cfg['signalNoiseEnabled'] is False
    assert cfg['partyBlocs']['winter'] == 'a' and cfg['partyBlocs']['hendel'] == 'other'
    assert cfg['partyBlocs']['joint'] == cfg['partyBlocs']['raam'] == 'other'
    assert official['input']['turnout']['year'] == 2022
    baseline_rates = {g['id']: g['turnoutPct'] for g in official['input']['turnout']['groups'] if g['turnoutPct'] is not None}
    assert set(baseline_rates) == {'arab_localities','haredi_three_cities','remaining_localities'}
    assert cfg['turnout'] == baseline_rates
    assert all(v == 1 for v in cfg['blocMultipliers'].values())
    image = SOCIAL / 'threshold-probabilities.png'
    assert sha(image) == PNG_SHA
    raw = image.read_bytes(); assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    dimensions = list(struct.unpack('>II', raw[16:24]))
    assert dimensions == visual['dimensions'] == [1122, 1402]
    prompt, original_prompt = SOCIAL / 'image-prompt.txt', SOCIAL / 'image-prompt-original.txt'
    assert sha(prompt) == match['promptSha256']
    assert sha(original_prompt) == match['originalGenerationPromptSha256']
    assert prompt.read_text(encoding='utf-8') == original_prompt.read_text(encoding='utf-8')
    assert match['promptUnicodeTextIdenticalAfterUniversalNewlineNormalization'] is True
    assert match['promptRawBytesIdentical'] is False
    assert prompt.read_bytes() != original_prompt.read_bytes()
    data = read(SOCIAL / 'model-data.json')
    assert data['modelComparisonFile'] == 'model-comparison-similarity.json'
    assert data['modelComparisonSha256'] == sha(comparison_path)
    assert data['sourcePlanSha256'] == match['sourcePlanSha256']
    assert data['independentModelReviewSha256'] == sha(review_path)
    assert data['configuration'] == cfg and data['release'] == 'evening'
    assert data['asOf'] == data['latestPollPublicationDate'] == '2026-10-20'
    selected = {p['pollsterId'] for p in comparison['after']['pollWeights']}
    assert len(selected) == data['selectedInstitutes'] == 7 and 'next_data' not in selected
    assert {p['pollsterId'] for p in data['selectedPolls']} == selected
    assert {p['publisher'] for p in data['selectedPolls']} == {'חדשות 12','חדשות 13','כאן 11','i24NEWS','ערוץ 16','זמן ישראל','וואלה'}
    groups = {g['id']: g for g in comparison['after']['reportingGroups']}
    assert data['meanSeats'] == {k: g['stats']['mean'] for k, g in groups.items()}
    assert math.isclose(sum(data['meanSeats'].values()), 120, abs_tol=1e-12)
    assert set(groups['arab']['partyIds']) == {'joint','raam'}
    assigned = [p for g in groups.values() for p in g['partyIds']]
    assert len(assigned) == len(set(assigned))
    values = {}
    for pid in ['winter','hendel']:
        party = next(p for p in comparison['after']['parties'] if p['id'] == pid)
        replay_party = next(p for p in official['result']['parties'] if p['id'] == pid)
        hist = replay_party['hist']; n = cfg['iterations']
        assert sum(hist) == n and sum(hist[1:4]) == 0
        assert math.isclose(sum(k*c for k,c in enumerate(hist))/n, party['mean'], abs_tol=1e-12)
        assert math.isclose(sum(hist[4:])/n, party['passProbability'], abs_tol=1e-12)
        exact = {'passPct': 100*party['passProbability'], 'meanSeats': party['mean']}
        assert data['parties'][pid] == exact
        displayed = {'passPct': f"{exact['passPct']:.1f}%", 'meanSeats': f"{exact['meanSeats']:.1f}"}
        assert data['displayed'][pid] == displayed
        assert f"{visual['visibleValues'][pid+'PassPct']:.1f}%" == displayed['passPct']
        assert f"{visual['visibleValues'][pid+'UnconditionalMeanSeats']:.1f}" == displayed['meanSeats']
        values[pid] = {**exact, 'displayed': displayed}
    assert data['meanSeats']['other'] == data['parties']['hendel']['meanSeats']
    assert data['thresholdPct'] == visual['visibleValues']['legalVoteThresholdPct'] == 3.25
    assert data['meanMandatesIncludeZeroSeatFailures'] is True
    tweet_path = SOCIAL / 'tweet.he.txt'; assert sha(tweet_path) == TWEET_SHA
    tweet = tweet_path.read_text(encoding='utf-8-sig').strip()
    url = 'https://victorchina-ops.github.io/israel-election-simulator/'
    for text in [f"{data['meanSeats']['a']:.1f}", f"{data['meanSeats']['b']:.1f}", values['winter']['displayed']['passPct'], values['hendel']['displayed']['passPct'], 'ללא 14', 'אומדן מודל', 'וינטר עם נתניהו', 'הערביות והנדל–זליכה בנפרד', url]:
        assert text in tweet
    chars = len(tweet) - len(url) + 23
    assert chars == data['tweetTwitterWeightedCharacters'] <= 280 and tweet.count(url) == 1
    assert data['automaticTweetPosted'] is False
    return {'status':'PASS-PENDING-RENDER','asOf':'2026-10-20','image':image.name,'imageSha256':PNG_SHA,'dimensions':dimensions,
        'visualInspectionCompleted':True,'visualPixelReceiptSha256':VISUAL_SHA,'officialReplayMatchSha256':MATCH_SHA,
        'officialReplaySha256':sha(official_path),'modelComparisonFile':comparison_path.name,'modelComparisonSha256':sha(comparison_path),
        'sourcePlanSha256':sha(ART/'source-plan.json'),'independentModelReviewSha256':sha(review_path),
        'meanSeats':data['meanSeats'],'values':values,'modelDataSha256':sha(SOCIAL/'model-data.json'),
        'tweetSha256':sha(tweet_path),'tweetTwitterWeightedCharacters':chars,'promptSha256':sha(prompt),
        'originalGenerationPromptSha256':sha(original_prompt),'promptUnicodeTextIdenticalAfterNewlineNormalization':True,
        'promptRawBytesIdentical':False,'reviewScriptSha256':sha(Path(__file__)),
        'inspectionMethod':'Independent view_image inspection of this exact PNG recorded before official replay equality was established; no automated pixel-reading claim.',
        'singleImageGenerationNoCleanup':True,'automaticTweetPosted':False,'modelUiSourceChanged':False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--finalize', action='store_true')
    parser.add_argument('--render-sha256')
    args = parser.parse_args()
    receipt = source_checks()
    freeze(ART/'social/official-source-pixel-review.json', receipt)
    if not args.finalize:
        assert args.render_sha256 is None
        print(json.dumps({'status':'PASS-PENDING-RENDER','sourcePixelReviewSha256':sha(ART/'social/official-source-pixel-review.json')}))
        return
    assert args.render_sha256 and len(args.render_sha256) == 64
    render_path = ART/'social/render-checks.json'
    assert sha(render_path) == args.render_sha256
    render = read(render_path)
    assert render['status'] == 'PASS' and render['visualInspectionCompleted'] is True
    assert render['asOf'] == '2026-10-20' and render['automaticTweetPosted'] is False
    assert render['output'] == receipt['image'] and render['outputSha256'] == PNG_SHA
    assert render['prompt'] == 'image-prompt.txt' and render['promptSha256'] == receipt['promptSha256']
    assert not render.get('cleanupPrompt')
    for key in ['modelComparisonFile','modelComparisonSha256','sourcePlanSha256','independentModelReviewSha256']:
        assert render[key] == receipt[key]
    browser_path = ART/'browser-local/report.json'
    assert render['browserLocalReportSha256'] == sha(browser_path)
    assert read(browser_path)['status'] == 'passed'
    receipt = {**receipt,'status':'PASS','renderReceiptSha256':sha(render_path),
        'officialSourcePixelReviewSha256':sha(ART/'social/official-source-pixel-review.json')}
    freeze(ART/'social/independent-review.json', receipt)
    print(json.dumps({'status':'PASS','independentReviewSha256':sha(ART/'social/independent-review.json'),'imageSha256':PNG_SHA}))


if __name__ == '__main__':
    main()
