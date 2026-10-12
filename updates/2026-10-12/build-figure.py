"""Original simple infographic: published coalition seats, one common scale."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'artifacts/poll-checks/2026-10-12-evening/social'
OUT=ROOT/'outputs/social/2026-10-12'
ART.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'artifacts/research/python-deps'))
from bidi.algorithm import get_display
from PIL import Image,ImageDraw,ImageFont
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
n12=read(ART.parent/'tv-primary/reviewed-n12-poll.json')
c14=read(ART.parent/'tv-primary/reviewed-c14-poll.json')
assert n12['date']==c14['date']=='2026-10-12'
coalition=['likud','shas','utj','otzma','rz_zehut','winter','noam']
rows=[{'label':'חדשות 12','seats':sum(p['seats'].get(k,0) for k in coalition),'source':p['sourceUrl'],'publisher':p['publisher']} for p in [n12]]
rows.append({'label':'חדשות 14','seats':sum(c14['seats'].get(k,0) for k in coalition),'source':c14['sourceUrl'],'publisher':c14['publisher']})
assert [r['seats'] for r in rows]==[49,61]
assert all(r['seats']==p['sourceBlocSeats']['coalition'] for r,p in zip(rows,[n12,c14]))
assert all(sum(p['seats'].values())==120 for p in [n12,c14])
W,H,S=1200,850,2
COL={'paper':'#F7F4EE','ink':'#21384B','muted':'#536878','red':'#BB493E','track':'#E7E4DE','white':'#FFFFFF','rule':'#C8C5BE'}
im=Image.new('RGB',(W*S,H*S),COL['paper']);d=ImageDraw.Draw(im)
REG=Path('C:/Windows/Fonts/arial.ttf');BOLD=Path('C:/Windows/Fonts/arialbd.ttf')
labels=[];marks=[]
def text(logical,x,y,size=26,color='ink',bold=False,align='right',rtl=True,role='text'):
 v=get_display(logical,base_dir='R') if rtl else logical
 f=ImageFont.truetype(str(BOLD if bold else REG),size*S);b=d.textbbox((0,0),v,font=f);width,height=b[2]-b[0],b[3]-b[1]
 left=x*S-width if align=='right' else x*S-width/2 if align=='center' else x*S
 top=y*S;bounds=[left/S,top/S,(left+width)/S,(top+height)/S]
 assert 42<=bounds[0] and bounds[2]<=W-42 and 22<=bounds[1] and bounds[3]<=H-22,(logical,bounds)
 d.text((left-b[0],top-b[1]),v,font=f,fill=COL.get(color,color));labels.append({'logical':logical,'role':role,'bounds':bounds,'sizePx':size})
def rect(b,color,radius=0):
 b=[round(x*S) for x in b]
 if radius:d.rounded_rectangle(b,radius=radius*S,fill=COL.get(color,color))
 else:d.rectangle(b,fill=COL.get(color,color))
def line(points,color='rule',width=2):d.line([(x*S,y*S) for x,y in points],fill=COL.get(color,color),width=width*S)
text('סקרים ושקרים',1134,34,26,'red',True,role='brand')
text('שני סקרים. פער של 12 מנדטים.',1134,86,51,'ink',True,role='headline')
text('גוש הקואליציה · שתי תוצאות שפורסמו באותו ערב',1134,159,30,'muted',role='scope')
ORIGIN=1062;SPAN=990
majorityX=ORIGIN-SPAN*61/120
for row,y in zip(rows,[265,437]):
 # Original ballot-box icon, with publisher number printed on the ballot.
 number=row['label'].split()[-1]
 rect([1080,y-2,1130,y+37],'white',4)
 text(number,1105,y+4,22,'red',True,align='center',rtl=False,role='ballot-label')
 d.polygon([(x*S,z*S) for x,z in [(1072,y+32),(1136,y+32),(1148,y+43),(1083,y+43)]],fill=COL['track'])
 rect([1083,y+43,1148,y+74],'white',4)
 line([(1099,y+38),(1126,y+38)],'ink',3)
 text(row['label'],1062,y,35,'ink',True,role='publisher')
 text(str(row['seats']),72,y-12,69,'red',True,align='left',rtl=False,role='published-coalition-seats')
 text('מנדטים',179,y+15,23,'muted',align='left',role='unit')
 barY=y+76
 rect([72,barY,ORIGIN,barY+31],'track',15)
 endpoint=ORIGIN-SPAN*row['seats']/120
 rect([endpoint,barY,ORIGIN,barY+31],'red',15)
 marks.append({'publisher':row['publisher'],'seats':row['seats'],'originX':ORIGIN,'endpointX':endpoint,'widthPx':SPAN*row['seats']/120,'barY':barY})
for y in range(322,551,14):line([(majorityX,y),(majorityX,min(y+7,550))],'ink',2)
text('61 — רוב בכנסת',majorityX,227,22,'ink',align='center',role='majority-reference')
for value in [0,60,120]:
 x=ORIGIN-SPAN*value/120
 line([(x,568),(x,577)])
 text(str(value),x,586,18,'muted',align='center',rtl=False,role='axis')
text('פער בין סוקרים אינו מגמה לאורך זמן.',1134,644,31,'ink',True,role='takeaway')
text('בתמונה: מנדטים שפורסמו בסקרים, לא הסתברויות ולא תוצאת המודל.',1134,693,23,'muted',role='published-v-model')
text('באתר: שקלול לפי דיוק היסטורי; ערוץ 14 מוחרג כברירת מחדל.',1134,731,23,'muted',role='site-default')
line([(66,775),(1134,775)])
text('פרסום ואיסוף: 12.10.2026 | מקורות: N12 / מדגם, ערוץ 14 / NEXT DATA',1134,795,21,'muted',role='dates-source')
text('ויקטור רינה בן דוד',66,809,18,'muted',align='left',role='credit')
png=OUT/'two-polls-one-evening.png'
im.resize((W,H),Image.Resampling.LANCZOS).save(png,optimize=True,dpi=(144,144))
PUBLIC='https://victorchina-ops.github.io/israel-election-simulator/'
tweet=('שני סקרים באותו ערב: 49 מנדטים לקואליציה בחדשות 12, מול 61 בערוץ 14 — פער של 12 מנדטים. '
       'פער בין סוקרים אינו מגמה לאורך זמן. שני הסקרים נוספו לאתר; ברירת המחדל נשארת שקלול לפי דיוק היסטורי, ללא ערוץ 14. הנתונים והתרחישים:\n'+PUBLIC)
weighted=sum(1 if ord(c)<=0x10ff or 0x2000<=ord(c)<=0x200d or 0x2010<=ord(c)<=0x201f or 0x2032<=ord(c)<=0x2037 else 2 for c in re.sub(r'https?://\S+','',tweet))+23
assert weighted<=280,weighted
(OUT/'tweet.he.txt').write_text(tweet+'\n',encoding='utf-8')
evidence={'asOf':'2026-10-12','arePublishedPollResults':True,'areSimulatedProbabilities':False,'areModelForecasts':False,'comparison':'Two institutes, same publication/fieldworkdate; not a time trend or significance test.','sameCoalitionPartyDefinition':coalition,'publishedSeats':rows,'plotDomainSeats':[0,120],'majoritySeats':61,'differenceSeats':12,'sourceCandidateHashes':{p.name:sha(p) for p in [ART.parent/'tv-primary/reviewed-n12-poll.json',ART.parent/'tv-primary/reviewed-c14-poll.json']},'C14SourceLeftIncludesHendel':True,'statisticalSignificanceClaim':None,'tweetPublished':False,'publicSimulatorUrl':PUBLIC}
(OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa={'status':'PASS','imageSha256':sha(png),'imageSizePx':[W,H],'textBounds':labels,'allTextBoundsWithinCanvas':True,'barGeometry':marks,'commonScaleAndOrigin':True,'lengthRatioMatchesPublishedValues':True,'tweetWeightedCharacters':weighted,'visualInspectionCompleted':False}
assert abs(marks[0]['widthPx']/marks[1]['widthPx']-49/61)<1e-12
(ART/'render-checks.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'png':str(png),'tweetWeightedCharacters':weighted,'seats':[r['seats'] for r in rows]}))
