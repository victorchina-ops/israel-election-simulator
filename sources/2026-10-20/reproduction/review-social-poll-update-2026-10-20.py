"""Bind the actually inspected20Oct image to its preferred similarity-on replay.

This is the factual/hash follow-up to a completed view_image inspection of the
pinned pixels. It does not pretend that automated checks performed visual review.
Only one generation prompt exists; there was no cleanup/edit generation.
"""
from pathlib import Path
import hashlib,json,math,struct

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-20'
SOCIAL=ROOT/'outputs/social/2026-10-20'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VISUALLY_REVIEWED_PNG='60948556b970ea208ad5d288fd5eeb5299608180790999eb6c6eacd97654373d'
EXPECTED_TWEET_SHA256='33b60f6cc2df6d2e36196754c3618c7a06a86cd169b4aff30926583d09dbad3e'
EXPECTED_RENDER_SHA256='4a253afc941ba4d6856fa4af099a82ac95e478d2588798e5b0cba3239a0f54bd'


def main():
    render_path=ART/'social/render-checks.json'
    render=read(render_path)
    assert sha(render_path)==EXPECTED_RENDER_SHA256
    assert render['status']=='PASS' and render['asOf']=='2026-10-20'
    assert render['modelComparisonFile']=='model-comparison-similarity.json'
    comparison=read(ART/render['modelComparisonFile'])
    assert render['modelComparisonSha256']==sha(ART/render['modelComparisonFile'])
    assert render['sourcePlanSha256']==sha(ART/'source-plan.json')
    assert render['independentModelReviewSha256']==sha(ART/'model-comparisons-independent-review.json')
    assert render['browserLocalReportSha256']==sha(ART/'browser-local/report.json')
    cfg=comparison['after']['config']
    assert cfg['weightMode']=='quality' and cfg['pollCorrelationEnabled'] is True
    assert cfg['includeChannel14'] is cfg['signalNoiseEnabled'] is False
    assert cfg['partyBlocs']['winter']=='a' and cfg['partyBlocs']['hendel']=='other'
    assert cfg['partyBlocs']['joint']==cfg['partyBlocs']['raam']=='other'
    assert comparison['after']['asOf']=='2026-10-20'
    image=SOCIAL/render['output']
    assert sha(image)==render['outputSha256']==VISUALLY_REVIEWED_PNG
    raw=image.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack('>II',raw[16:24]);assert (width,height)==(1122,1402)
    assert Path(render['prompt']).name==render['prompt']
    assert sha(SOCIAL/render['prompt'])==render['promptSha256']
    assert not render.get('cleanupPrompt'), 'Single generation has no cleanup prompt'
    data=read(SOCIAL/'model-data.json')
    assert data['modelComparisonFile']==render['modelComparisonFile']
    assert data['modelComparisonSha256']==render['modelComparisonSha256']
    assert data['asOf']==data['latestPollPublicationDate']=='2026-10-20'
    assert data['configuration']==cfg
    selected={p['pollsterId'] for p in comparison['after']['pollWeights']}
    assert len(selected)==data['selectedInstitutes']==7 and 'next_data' not in selected
    assert {p['pollsterId'] for p in data['selectedPolls']}==selected
    assert {p['publisher'] for p in data['selectedPolls']}=={'חדשות 12','חדשות 13','כאן 11','i24NEWS','ערוץ 16','זמן ישראל','וואלה'}
    groups={row['id']:row for row in comparison['after']['reportingGroups']}
    expected_groups={'a':'51.3','b':'53.4','arab':'13.7','other':'1.7'}
    for gid,display in expected_groups.items():
        assert data['meanSeats'][gid]==groups[gid]['stats']['mean']
        assert f"{groups[gid]['stats']['mean']:.1f}"==display
    assert math.isclose(sum(data['meanSeats'].values()),120,rel_tol=0,abs_tol=1e-12)
    assigned=[pid for group in groups.values() for pid in group['partyIds']]
    assert len(assigned)==len(set(assigned))
    assert set(groups['arab']['partyIds'])=={'joint','raam'}
    expected={'winter':{'pass':'29.9%','mean':'1.2'},'hendel':{'pass':'39.0%','mean':'1.7'}}
    actual={}
    for pid in expected:
        p=next(p for p in comparison['after']['parties'] if p['id']==pid)
        assert data['parties'][pid]['passPct']==100*p['passProbability']
        assert data['parties'][pid]['meanSeats']==p['mean']
        assert f"{100*p['passProbability']:.1f}%"==expected[pid]['pass']
        assert f"{p['mean']:.1f}"==expected[pid]['mean']
        actual[pid]={'passPct':100*p['passProbability'],'unconditionalMeanSeats':p['mean'],'displayed':expected[pid]}
    assert data['meanSeats']['other']==data['parties']['hendel']['meanSeats']
    tweet_path=SOCIAL/'tweet.he.txt'
    assert sha(tweet_path)==EXPECTED_TWEET_SHA256
    tweet=tweet_path.read_text(encoding='utf-8-sig').strip()
    url='https://victorchina-ops.github.io/israel-election-simulator/'
    for text in ['51.3','53.4','29.9%','39.0%','ללא 14','אומדן מודל','וינטר עם נתניהו','הערביות והנדל–זליכה בנפרד',url]:assert text in tweet
    weighted_chars=len(tweet)-len(url)+23
    assert weighted_chars<=280 and tweet.count(url)==1
    assert render['automaticTweetPosted'] is data['automaticTweetPosted'] is False
    receipt={'status':'PASS','asOf':'2026-10-20','image':image.name,'imageSha256':sha(image),'dimensions':[width,height],
        'visualInspectionCompleted':True,'inspectionMethod':'Independent reviewer opened this exact PNG with view_image and read its actual pixels before recording these observations. No image or tweet changes were made.',
        'visualObservations':[
            'Painted Knesset scene with two ballot envelopes and simple red/blue comparison is legible without crowded charts.',
            'Opposition53.4 at left and coalition51.3 at right are explicitly model mean mandates. Arab13.7 and Hendel-Zelekha1.7 are separately shown outside the two blocs.',
            'Winter is red at right:29.9% chance to pass and1.2 mean mandates. Hendel-Zelekha is purple at left:39.0% chance and1.7 mean mandates.',
            'Probabilities are explicitly model probabilities, not published vote shares. Mean mandates include failure outcomes; rounded means are labelled.',
            'Winter is assigned to Netanyahu; Arab lists and Hendel-Zelekha remain outside both blocs. No confidence or significance claim is shown.',
            'Historical accuracy plus similar-poll discount is ON, Channel14 excluded, latest observation per institute,2022 turnout baseline, update20.10.2026 and model-conditional interpretation are visible.',
            'All seven selected publishers are correctly named:12,13,Kan11,i24,16,ZmanIsrael,Walla. Small credit to ויקטור רינה בן דוד is legible.'
        ],'meanSeats':data['meanSeats'],'displayedMeanSeats':expected_groups,'values':actual,
        'tweetSha256':sha(tweet_path),'tweetTwitterWeightedCharacters':weighted_chars,
        'renderReceiptSha256':sha(render_path),'sourcePlanSha256':sha(ART/'source-plan.json'),
        'modelComparisonFile':render['modelComparisonFile'],'modelComparisonSha256':render['modelComparisonSha256'],
        'modelDataSha256':sha(SOCIAL/'model-data.json'),'reviewScriptSha256':sha(Path(__file__)),
        'singleImageGenerationNoCleanup':True,'automaticTweetPosted':False,'modelUiSourceChanged':False}
    path=ART/'social/independent-review.json';body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    assert not path.exists() or path.read_bytes()==body,'Preserve dated social review'
    path.write_bytes(body)
    print(json.dumps({'status':'PASS','imageSha256':sha(image),'independentReviewSha256':sha(path),'meanSeats':data['meanSeats'],'values':actual},ensure_ascii=False))


if __name__=='__main__':main()
