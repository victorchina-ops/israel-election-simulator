"""Freeze the inspected illustration and bind its displayed probabilities to the final replay."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-13'
SOCIAL=ROOT/'outputs/social/2026-10-13-poll-update'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
comparison=read(ART/'model-comparison.json')
assert read(ART/'model-comparison-validation.json')['status']=='PASS'
def probability(phase,pid):return next(r['passProbability'] for r in comparison[phase]['parties'] if r['id']==pid)
values={phase:{pid:probability(phase,pid) for pid in ['winter','hendel']} for phase in ['before','after']}
assert values=={'before':{'winter':.5308,'hendel':.2839},'after':{'winter':.4273,'hendel':.4302}}
preview=read(ART/'forecast-preview.json')
for pid in ['winter','hendel']:
    assert next(p['passProbability'] for p in preview['result']['parties'] if p['id']==pid)==values['after'][pid]
cfg=comparison['after']['config'];assert cfg['weightMode']=='quality' and cfg['iterations']==10000
assert all(cfg[key] is False for key in ['includeChannel14','signalNoiseEnabled','pollCorrelationEnabled'])
assert comparison['before']['asOf']=='2026-10-12' and comparison['after']['asOf']=='2026-10-13'
png=SOCIAL/'threshold-two-parties-illustrated.png'
with Image.open(png) as im:assert im.format=='PNG';dimensions=im.size
assert dimensions[0]>=1000 and dimensions[1]>=1000
tweet=(SOCIAL/'tweet.he.txt').read_text(encoding='utf-8')
assert 'https://victorchina-ops.github.io/israel-election-simulator/' in tweet
inputs=[ROOT/'outputs/social/2026-10-13/winter-hendel-four-scenarios-illustrated.png',
        ROOT/'dashboard/src/content/assets/party-logos/winter.png',ROOT/'dashboard/src/content/assets/party-logos/hendel.png']
receipt={'status':'PASS','asOf':'2026-10-13','tool':'built-in image_gen','operation':'edit-existing-illustrated-poster-with-verified-logo-inserts',
 'prompt':'illustrated-prompt.txt','promptSha256':sha(SOCIAL/'illustrated-prompt.txt'),
 'output':png.name,'outputSha256':sha(png),'dimensions':dimensions,
 'generationDefaultPath':'C:/Users/User/.codex/generated_images/01a0952c-a40b-7b01-b019-621f0cee2656/exec-5a9b2f65-6a39-4f20-b232-b417ca936954.png',
 'cleanupPrompt':'illustrated-cleanup-prompt.txt','cleanupPromptSha256':sha(SOCIAL/'illustrated-cleanup-prompt.txt'),
 'intermediateDraftSha256':sha(ART/'social/threshold-two-parties-illustrated-v1.png'),
 'inputImages':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in inputs],
 'values':values,'displayedWholePercentages':{'before':{'winter':53,'hendel':28},'after':{'winter':43,'hendel':43}},
 'modelComparisonSha256':sha(ART/'model-comparison.json'),'visualInspectionCompleted':True,
 'visualChecks':['Exact43/43 current and53/28 earlier numbers','Dates13Oct2026/current and12Oct2026/earlier model separate',
 'Published sources namedi24/Channel16/WallaLazar','Model probabilities explicitly distinguished from poll vote shares',
 'Historical accuracy/noChannel14/turnout2022 labelled','Recognizable party-name logos associated with corresponding cards; tiny generated slogan removed',
 'No old four-case percentages/mandates remain','No joint-event or significance claim','Credit and simulator link readable','Both characters outside entrance; no certainpass/fail implied'],
 'socialDraftOnly':True,'tweetsPublished':False}
for path in [SOCIAL/'generation-and-visual-receipt.json',ART/'social/render-checks.json']:
    path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists()
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','dimensions':dimensions,'outputSha256':sha(png),'values':values}))
