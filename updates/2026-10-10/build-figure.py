from pathlib import Path
import hashlib, json, re, sys
from datetime import datetime, timezone

ROOT = Path(r'C:/Users/User/Documents/ChatGPT/סקרים ושקרים').resolve()
ART = (ROOT / 'artifacts/poll-checks/2026-10-10/social').resolve()
OUT = (ROOT / 'outputs/social/2026-10-10').resolve()
for target in (ART, OUT):
    assert target.is_relative_to(ROOT), 'Output must stay in project'
    target.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'artifacts/research/python-deps'))
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

URL = 'https://www.mako.co.il/news-politics/2026_q4/Article-2497091942121a1026.htm'
PUBLIC = 'https://victorchina-ops.github.io/israel-election-simulator/'
SRC = ROOT / 'artifacts/poll-checks/2026-10-10/root-run2'
source_text = (SRC / 'n12-opinion-2026-10-09.txt').read_text(encoding='utf-8')
assert 'כולל המפלגות הערביות' in source_text and '50%' in source_text
assert 'כולל מפלגתו של וינטר' in source_text and '35%' in source_text
assert '09.10.26, 21:28' in source_text and 'שפרסמנו אמש' in source_text

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for suffix in ('html', 'txt'):
    source_path = SRC / ('n12-opinion-2026-10-09.' + suffix)
    local_path = ART / source_path.name
    if local_path.exists():
        assert sha(local_path) == sha(source_path), 'Existing source evidence changed'
    else:
        local_path.write_bytes(source_path.read_bytes())

W, H, S = 1200, 820, 2
COL = {'paper': '#F8F6F1', 'ink': '#172D41', 'muted': '#586574',
       'blue': '#315C7B', 'gold': '#B87726', 'track': '#E9E4DB', 'rule': '#CFC9BE'}
im = Image.new('RGB', (W*S, H*S), COL['paper'])
draw = ImageDraw.Draw(im)
FONT_REG = Path(r'C:/Windows/Fonts/arial.ttf')
FONT_BOLD = Path(r'C:/Windows/Fonts/arialbd.ttf')
labels, marks = [], []

def font(size, bold=False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size*S)

def text(logical, x, y, size, color='ink', bold=False, align='right', bidi=True, role='text'):
    visual = get_display(logical, base_dir='R') if bidi else logical
    f = font(size, bold)
    box = draw.textbbox((0,0), visual, font=f)
    width, height = box[2]-box[0], box[3]-box[1]
    left = x*S - width if align == 'right' else x*S
    top = y*S
    draw.text((left-box[0], top-box[1]), visual, font=f, fill=COL.get(color,color))
    bounds = [left/S, top/S, (left+width)/S, (top+height)/S]
    assert bounds[0] >= 45 and bounds[2] <= W-45, (logical,bounds)
    assert bounds[1] >= 25 and bounds[3] <= H-20, (logical,bounds)
    labels.append({'logicalText': logical, 'visualText': visual, 'sizePx':size,
                   'color':COL.get(color,color), 'role':role, 'bounds':bounds})

def rect(box, fill):
    draw.rectangle(tuple(round(v*S) for v in box), fill=COL.get(fill,fill))

text('סקרים ושקרים',1128,42,26,'blue',True,role='brand')
text('סקר גושים ≠ סקר מנדטים',1128,94,54,'ink',True,role='headline')
text('סקר אולפן שישי • שיעור התמיכה שפורסם',1128,164,29,'muted',role='subtitle')

BAR_X, BAR_WIDTH, BAR_HEIGHT = 72, 1056, 34
rows = [
    {'label':'גוש מתנגדי נתניהו', 'scope':'כולל המפלגות הערביות',
     'sharePct':50, 'color':'blue', 'labelY':236, 'scopeY':280, 'valueY':221, 'barY':321},
    {'label':'גוש נתניהו', 'scope':'כולל מפלגתו של וינטר',
     'sharePct':35, 'color':'gold', 'labelY':380, 'scopeY':424, 'valueY':365, 'barY':465},
]
for row in rows:
    text(row['label'],1128,row['labelY'],38,'ink',True,role='bloc-label')
    text(row['scope'],1128,row['scopeY'],27,'muted',role='bloc-scope')
    text(str(row['sharePct'])+'%',72,row['valueY'],76,row['color'],True,
         align='left',bidi=False,role='published-share')
    y = row['barY']
    rect([BAR_X,y,BAR_X+BAR_WIDTH,y+BAR_HEIGHT], 'track')
    end = BAR_X + BAR_WIDTH*row['sharePct']/100
    rect([BAR_X,y,end,y+BAR_HEIGHT],row['color'])
    marks.append({'bloc':row['label'], 'valuePct':row['sharePct'], 'originX':BAR_X,
                  'endX':end, 'widthPx':end-BAR_X, 'y':y, 'heightPx':BAR_HEIGHT})

# A common 0–100% scale, with a visible shared zero origin.
rect([72,510,1128,511], 'rule')
for pct in (0,50,100):
    x = BAR_X + BAR_WIDTH*pct/100
    rect([x,506,x+1,516],'rule')
    label = str(pct)+'%'
    align = 'left' if pct == 0 else 'right'
    label_x = x if pct != 50 else x+17
    text(label,label_x,523,18,'muted',align=align,bidi=False,role='axis-tick')

text('פער בתמיכה שדווחה: 15 נקודות אחוז',1128,564,29,'ink',True,role='descriptive-gap')
text('אחוזי תמיכה בסקר; אינם מנדטים או הסתברות במודל.',1128,609,25,'muted',role='scope-note')
text('בכתבה אין פירוט מפלגות; הסקר לא צורף לשקלול המנדטים.',1128,643,25,'muted',role='model-exclusion-note')
rect([72,688,1128,689], 'rule')
text('מקור: N12, אולפן שישי | פרסום הכתבה: 9.10.2026 | בדיקה: 10.10.2026',1128,706,21,'muted',role='source-date')
text(URL,72,742,16,'muted',align='left',bidi=False,role='source-url')
text('ימי האיסוף המדויקים וגודל המדגם לא נמסרו בכתבה.',1128,769,20,'muted',role='missing-methodology')
text('ויקטור רינה בן דוד',72,779,18,'muted',align='left',role='credit')

assert marks[0]['originX'] == marks[1]['originX'] == 72
assert abs(marks[0]['widthPx']/marks[1]['widthPx'] - 50/35) < 1e-12
assert rows[0]['sharePct'] - rows[1]['sharePct'] == 15
png = OUT / 'n12-bloc-shares.png'
im.resize((W,H), Image.Resampling.LANCZOS).save(png, optimize=True, dpi=(144,144))

TWEET = ('סקר גושים ≠ סקר מנדטים: בכתבת אולפן שישי מ־9.10, 50% לגוש מתנגדי נתניהו כולל המפלגות הערביות, '
         'מול 35% לגוש נתניהו כולל וינטר. בכתבה לא פורסם פירוט לפי מפלגה, ולכן לא נוסף סקר מנדטים למודל. הסימולטור:\n' + PUBLIC)
# Twitter/X standard weight: URLs count as 23; Hebrew and ordinary Latin count as 1.
def weight(c):
    n = ord(c)
    return 1 if n <= 0x10FF or 0x2000 <= n <= 0x200D or 0x2010 <= n <= 0x201F or 0x2032 <= n <= 0x2037 else 2
weighted = sum(weight(c) for c in re.sub(r'https?://\S+', '', TWEET)) + 23
assert weighted <= 280, weighted
(OUT / 'tweet.he.txt').write_text(TWEET + '\n', encoding='utf-8')

source_evidence = {
    'schemaVersion':1, 'originalUrl':URL, 'archivedAtReviewDate':'2026-10-10',
    'articlePublishedAtIsrael':'2026-10-09T21:28:00+03:00',
    'firstSurveyPublicationDate':None,
    'dateLimitation':'Article body says the survey was published yesterday; article publication is not treated as verified first poll publication or fieldwork.',
    'fieldworkStart':None, 'fieldworkEnd':None, 'sampleSize':None,
    'sourceFiles':[{'path':str(ART / ('n12-opinion-2026-10-09.'+ext)), 'sha256':sha(ART / ('n12-opinion-2026-10-09.'+ext))} for ext in ('html','txt')],
    'publishedBlocShares':[{'label':r['label'],'scope':r['scope'],'sharePct':r['sharePct']} for r in rows],
    'descriptiveDifferencePercentagePoints':15,
    'questionWordingPublished':None, 'exactPercentageDenominatorPublished':None,
    'noPartyVectorInReadArticle':True, 'includedInMandateAggregate':False,
    'independentOfModel':True, 'areSeatCounts':False, 'areModelProbabilities':False,
    'fullResponsePartitionShown':False, 'undecidedOmitted':'11% is reported separately and is not used to complete the 50/35 display.',
    'significanceClaimMade':False, 'testPerformed':None,
    'sourceValidation':'Read archived original article, checked bloc inclusions and shares, and independent copy QA.',
    'publicSimulatorUrl':PUBLIC,
}
(ART / 'figure-source-evidence.json').write_text(json.dumps(source_evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT / 'evidence.json').write_text(json.dumps(source_evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa = {
    'schemaVersion':1,'builtAtUtc':datetime.now(timezone.utc).isoformat(),
    'imagePath':str(png),'imageSizePx':[W,H],'imageSha256':sha(png),
    'renderer':'Pillow supersampled2x, python-bidi, local Arial fonts',
    'fontFiles':[{'path':str(p),'sha256':sha(p)} for p in (FONT_REG,FONT_BOLD)],
    'chartScalePct':[0,100],'commonOriginX':72,'barGeometry':marks,
    'textBounds':labels,'allTextBoundsWithinCanvas':True,
    'barLengthRatioMatchesPublishedShareRatio':True,
    'tweetWeightedCharacters':weighted,'tweetCodepoints':len(TWEET),
    'tweetPublished':False,'sitePublished':False,'canonicalDataEdited':False,
    'visualInspectionCompleted':False,
}
(ART / 'render-checks.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ART / 'README.txt').write_text('Reproduce with the bundled Python runtime:\n'
    'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe '
    'artifacts/poll-checks/2026-10-10/social/build-figure.py\n'
    'Existing local artifacts/research/python-deps supplies python-bidi. No package installation or network needed.\n'
    'Source copy, logical text, exact geometry, font hashes and output hashes are retained here.\n', encoding='utf-8')
print(json.dumps({'png':str(png),'tweet':str(OUT/'tweet.he.txt'),'weightedCharacters':weighted,
                  'pngSha256':sha(png),'labels':len(labels),'renderChecks':str(ART/'render-checks.json')}))