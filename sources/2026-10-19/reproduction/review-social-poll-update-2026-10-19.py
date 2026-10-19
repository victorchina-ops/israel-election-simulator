"""Bind an actually visually inspected19Oct illustration to its approved replay.

The completed view_image inspection is recorded for the specific pinned PNG.
This script verifies unchanged pixels and factual bindings; it is not an OCR or
automated visual inspection and never replaces the root render receipt.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-19'
SOCIAL=ROOT/'outputs/social/2026-10-19'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VISUALLY_REVIEWED_PNG='c7167d5b34bd182222629f11e7e530c123ada83ab9dd608213d33a4b9b6061d1'


def main():
    render=read(ART/'social/render-checks.json')
    assert sha(ART/'social/render-checks.json')=='e98c98bb3268ddba87b62766333fc612a74f59eaaf191b085541a2e05c3a12b3'
    assert render['status']=='PASS' and render['asOf']=='2026-10-19'
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
    assert comparison['after']['asOf']=='2026-10-19'
    image=SOCIAL/render['output']
    assert sha(image)==render['outputSha256']==VISUALLY_REVIEWED_PNG
    raw=image.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack('>II',raw[16:24]);assert (width,height)==(1122,1402)
    for key in ['prompt','cleanupPrompt']:
        assert Path(render[key]).name==render[key]
        assert sha(SOCIAL/render[key])==render[key+'Sha256']
    data=read(SOCIAL/'model-data.json')
    assert data['modelComparisonFile']==render['modelComparisonFile']
    assert data['modelComparisonSha256']==render['modelComparisonSha256']
    assert data['asOf']=='2026-10-19' and data['latestPollPublicationDate']=='2026-10-18'
    selected={p['pollsterId'] for p in comparison['after']['pollWeights']}
    assert len(selected)==data['selectedInstitutes']==7 and 'next_data' not in selected
    assert {p['pollsterId'] for p in data['selectedPolls']}==selected
    expected={'winter':{'pass':'28.7%','mean':'1.2'},'hendel':{'pass':'47.6%','mean':'2.1'}}
    actual={}
    for pid in expected:
        p=next(p for p in comparison['after']['parties'] if p['id']==pid)
        assert data['parties'][pid]['passPct']==100*p['passProbability']
        assert data['parties'][pid]['meanSeats']==p['mean']
        assert f"{100*p['passProbability']:.1f}%"==expected[pid]['pass']
        assert f"{p['mean']:.1f}"==expected[pid]['mean']
        actual[pid]={'passPct':100*p['passProbability'],'unconditionalMeanSeats':p['mean'],'displayed':expected[pid]}
    tweet=(SOCIAL/'tweet.he.txt').read_text(encoding='utf-8-sig')
    for text in ['28.7%','47.6%','ללא ערוץ 14','לא אחוזי התמיכה בסקר','https://victorchina-ops.github.io/israel-election-simulator/']:
        assert text in tweet
    assert render['automaticTweetPosted'] is False
    receipt={'status':'PASS','asOf':'2026-10-19','image':image.name,'imageSha256':sha(image),'dimensions':[width,height],
        'visualInspectionCompleted':True,'inspectionMethod':'Independent release reviewer opened this exact PNG with view_image and read its actual pixels before recording these observations. No image changes were made.',
        'visualObservations':[
            'Painted Knesset scene and two distinct envelopes support the simple two-party comparison; no crowding or cropped text.',
            'Winter/AmkhaIsrael is red at right; Hendel-Zelekha/Miluimnikim-and-economic is purple at left. Names and values are correctly associated.',
            'Large28.7% and47.6% are explicitly chances to pass;3.25% is separately labelled as the electoral threshold.',
            'Mean seats1.2 and2.1 are separately labelled and the footnote explicitly includes zero-seat failure cases.',
            'Model estimate is distinguished from a published poll and from certainty; no statistical significance claim is present.',
            'Update19.10.2026 is separate from latest data18.10.2026; historical accuracy plus similar-poll discount, noChannel14, latest-per-institute and2022turnout assumptions are legible.',
            'Seven selected publishers are correctly named; credit to ויקטור רינה בן דוד is visible.'
        ],'values':actual,'tweetSha256':sha(SOCIAL/'tweet.he.txt'),
        'renderReceiptSha256':sha(ART/'social/render-checks.json'),'sourcePlanSha256':sha(ART/'source-plan.json'),
        'modelComparisonFile':render['modelComparisonFile'],'modelComparisonSha256':render['modelComparisonSha256'],
        'modelDataSha256':sha(SOCIAL/'model-data.json'),'reviewScriptSha256':sha(Path(__file__)),
        'automaticTweetPosted':False,'modelUiSourceChanged':False}
    path=ART/'social/independent-review.json'
    body=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.exists():assert path.read_bytes()==body,'Preserve dated social review'
    else:path.write_bytes(body)
    print(json.dumps({'status':'PASS','imageSha256':sha(image),'independentReviewSha256':sha(path),'values':actual}))


if __name__=='__main__':main()
