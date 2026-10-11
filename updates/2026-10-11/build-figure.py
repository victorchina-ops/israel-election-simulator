"""Original threshold illustration from the audited browser-model replay."""
from pathlib import Path
import hashlib,json,math,re,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'artifacts/poll-checks/2026-10-11/social'
OUT=ROOT/'outputs/social/2026-10-11'
ART.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'artifacts/research/python-deps'))
from bidi.algorithm import get_display
from PIL import Image,ImageDraw,ImageFont
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=read(ART.parent/'model-comparison.json')
assert report['status']=='passed' and report['onlyControlDateDiffers']
assert report['before']['asOf']=='2026-10-10' and report['after']['asOf']=='2026-10-11'
cfg=report['after']['config']
assert cfg['weightMode']=='quality' and cfg['includeChannel14'] is False
assert cfg['signalNoiseEnabled'] is False and cfg['pollCorrelationEnabled'] is False
poll=next(p for p in read(ROOT/'data/current-polls.json')['polls'] if p['id']=='kantar_2026-10-11')
assert poll['seats']['winter']==poll['seats']['hendel']==4
W,H,S=1200,1000,2
COL={'paper':'#F8F5EF','ink':'#18334A','muted':'#596A77','blue':'#2379A6','coral':'#C25A40','track':'#E4E8E9','white':'#FFFFFF','gold':'#E6B352','rule':'#D9D9D3'}
im=Image.new('RGB',(W*S,H*S),COL['paper']);draw=ImageDraw.Draw(im)
FONT_REG=Path('C:/Windows/Fonts/arial.ttf');FONT_BOLD=Path('C:/Windows/Fonts/arialbd.ttf')
labels=[];marks=[]
def text(logical,x,y,size=28,color='ink',bold=False,align='right',rtl=True,role='text'):
 visual=get_display(logical,base_dir='R') if rtl else logical
 f=ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG),size*S)
 b=draw.textbbox((0,0),visual,font=f);width,height=b[2]-b[0],b[3]-b[1]
 left=x*S-width if align=='right' else x*S-width/2 if align=='center' else x*S
 top=y*S;bounds=[left/S,top/S,(left+width)/S,(top+height)/S]
 assert 42<=bounds[0] and bounds[2]<=W-42 and 22<=bounds[1] and bounds[3]<=H-22,(logical,bounds)
 draw.text((left-b[0],top-b[1]),visual,font=f,fill=COL.get(color,color))
 labels.append({'logicalText':logical,'visualText':visual,'sizePx':size,'bounds':bounds,'role':role})
def box(bounds,fill,outline=None,radius=0,width=1):
 b=[round(v*S) for v in bounds]
 if radius:draw.rounded_rectangle(b,radius=radius*S,fill=COL.get(fill,fill),outline=COL.get(outline,outline),width=width*S)
 else:draw.rectangle(b,fill=COL.get(fill,fill),outline=COL.get(outline,outline),width=width*S)
def line(points,color,width=2):draw.line([(x*S,y*S) for x,y in points],fill=COL.get(color,color),width=width*S)
text('סקרים ושקרים',1134,36,27,'blue',True,role='brand')
text('אחוז החסימה: כמה בטוח לעבור?',1134,89,49,'ink',True,role='headline')
text('בכאן שניהם על 4 מנדטים. מה אומר שקלול הסקרים?',1134,159,30,'muted',role='published-v-model')

for pid,name,cx,color in [('winter','וינטר · עמך ישראל',862,'blue'),('hendel','הנדל–זליכה',338,'coral')]:
 after=next(p for p in report['after']['parties'] if p['id']==pid)
 before=next(p for p in report['before']['parties'] if p['id']==pid)
 prob=after['passProbability'];assert 0<=prob<=1
 box([cx-238,228,cx+238,703],'white',radius=30)
 # Stylized ballot and transparent box are original geometry, not a candidate portrait.
 box([cx-61,260,cx+40,335],'paper','rule',radius=6,width=2)
 line([(cx-36,278),(cx+18,278)],color,5)
 line([(cx-36,298),(cx+5,298)],color,4)
 draw.polygon([(int(x*S),int(y*S)) for x,y in [(cx-85,325),(cx+60,325),(cx+83,342),(cx-65,342)]],fill=COL['track'])
 box([cx-65,342,cx+83,394],'paper',color,radius=5,width=2)
 line([(cx-22,334),(cx+24,334)],'ink',3)
 text(name,cx,416,34,color,True,align='center',role='party')
 # Each circle encodes an actual 0–100% model probability, starting at12o'clock.
 ring=[(cx-84)*S,478*S,(cx+84)*S,646*S]
 draw.arc(ring,start=0,end=360,fill=COL['track'],width=12*S)
 if prob>0:draw.arc(ring,start=-90,end=-90+360*prob,fill=COL[color],width=12*S)
 text(f'{100*prob:.1f}%',cx,525,49,color,True,align='center',rtl=False,role='model-probability')
 text('סיכוי לעבור במודל',cx,584,23,'muted',align='center',role='model-label')
 text(f'לפני העדכון: {100*before["passProbability"]:.1f}%',cx,661,25,'muted',align='center',role='previous-model-probability')
 marks.append({'partyId':pid,'modelPassPct':100*prob,'previousModelPassPct':100*before['passProbability'],'ringSweepDegrees':360*prob,'publishedKanSeats':4})

text('4 מנדטים בסקר אחד אינם הבטחה לעבור ביום הבחירות.',1134,745,29,'ink',True,role='takeaway')
text('תוצאת מודל · משקלי דיוק היסטורי · ללא ערוץ 14 · השתתפות בסיס 2022',1134,799,23,'muted',role='assumptions')
text('10,000 הדמיות; אחוזים חסרים של מפלגות עוברות משוחזרים לצורך המודל.',1134,838,22,'muted',role='reconstruction')
line([(66,882),(1134,882)],'rule')
text('נתוני המודל: 11.10.2026 | לפני העדכון: 10.10.2026',1134,903,22,'muted',role='model-dates')
text('סקר כאן: 11.10.2026 · קנטאר / דודי חסיד · מקור: IsraelPolls',1134,938,21,'muted',role='source')
text('ויקטור רינה בן דוד',66,960,18,'muted',align='left',role='credit')
png=OUT/'threshold-chances.png'
im.resize((W,H),Image.Resampling.LANCZOS).save(png,optimize=True,dpi=(144,144))
winter,hendel=marks
PUBLIC='https://victorchina-ops.github.io/israel-election-simulator/'
tweet=(f'סקר כאן החדש: וינטר והנדל–זליכה עם 4 מנדטים כל אחד. בשקלול לפי דיוק היסטורי, ללא ערוץ 14, '
       f'סיכויי המעבר במודל: וינטר {winter["modelPassPct"]:.1f}%, הנדל–זליכה {hendel["modelPassPct"]:.1f}%. '
       '4 מנדטים בסקר אינם הבטחה לעבור בבחירות. הנתונים וההנחות:\n'+PUBLIC)
weighted=sum(1 if ord(c)<=0x10ff or 0x2000<=ord(c)<=0x200d or 0x2010<=ord(c)<=0x201f or 0x2032<=ord(c)<=0x2037 else 2 for c in re.sub(r'https?://\S+','',tweet))+23
assert weighted<=280,weighted
(OUT/'tweet.he.txt').write_text(tweet+'\n',encoding='utf-8')
evidence={'asOf':'2026-10-11','beforeModelAsOf':'2026-10-10','comparisonSha256':sha(ART.parent/'model-comparison.json'),'currentDataSha256':sha(ROOT/'data/current-polls.json'),'sourceUrl':poll['sourceUrl'],'historyTableUrl':'https://x.com/IsraelPolls/status/2109340303660552420','method':'Identical browser model replay, historicalaccuracyweights, latestselectedpollperinstitute,7activeinstitutes withoutChannel14,10000 trials seed20260912,baseline2022turnout. Original passingpartypercentagesunpublished and reconstructed.', 'marks':marks,'statisticsClaim':None,'areModelProbabilities':True,'arePublishedVoteShares':False,'publicSimulatorUrl':PUBLIC,'tweetPublished':False}
(OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa={'status':'PASS','builtAtUtc':datetime.now(timezone.utc).isoformat(),'imageSizePx':[W,H],'imageSha256':sha(png),'renderer':'Original Pillow drawing with supersampling and bidi; no external media','textBounds':labels,'allTextBoundsWithinCanvas':True,'marks':marks,'tweetWeightedCharacters':weighted,'visualInspectionCompleted':False}
(ART/'render-checks.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'png':str(png),'tweetWeightedCharacters':weighted,'marks':marks},ensure_ascii=False))
