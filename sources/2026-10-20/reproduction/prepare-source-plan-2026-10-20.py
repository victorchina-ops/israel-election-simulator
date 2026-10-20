"""Freeze the reviewed Oct20 four-poll source plan; never edits canonical data."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/poll-checks/2026-10-20'
DAY = '2026-10-20'
MANIFEST_SHA = '1b508593083afa9ca1b0e35dc8d45c6cd54aad8d3a511619228a2179af57c937'
HEAD = '769317e59fcfe29e610d24dc4944cdbc6ff8188f'


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path, public_name=None):
    p = ROOT / path
    result = {'sourcePath':path, 'publicName':public_name or p.name, 'sha256':sha(p)}
    assert p.resolve().is_relative_to(ART.resolve())
    assert 'local-only' not in p.name.lower() and 'localonly' not in p.name.lower()
    assert p.suffix.lower() not in {'.html','.htm'}
    return result


def frozen_write(path, value):
    content = (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.exists():
        assert path.read_bytes() == content, ('Immutable output differs',str(path))
    else:
        path.write_bytes(content)


manifest = ART / 'before/manifest.json'
assert sha(manifest) == MANIFEST_SHA
assert read(manifest)['historyPollCount'] == 128
assert read(ART / 'checkpoint-freeze.json')['status'] == 'PASS'
tv = 'artifacts/poll-checks/2026-10-20/source-main-tv/'
pr = 'artifacts/poll-checks/2026-10-20/source-kan-i24-print/'
x = 'artifacts/poll-checks/2026-10-20/source-israelpolls/'
root_coverage = 'artifacts/poll-checks/2026-10-20/source-root-coverage.json'
assert sha(ROOT / root_coverage) == '0730d864f9a110ecbbf0d002ec68642719a7cdad81c9058a193790e8ba00c21c'
safe = read(ROOT / (tv+'source-public-freeze-receipt-r1.json'))
assert sha(ROOT / (tv+'source-public-freeze-receipt-r1.json')) == '6ce6274a37cb6b2e74680d11e7e8154564b8b1bcc9b198636c483d3826ad44f2'
for entry in safe['files']:
    assert sha(ROOT / (tv+entry['fileName'])) == entry['sha256']
safe_names = {e['fileName'] for e in safe['files']}

configs = [
    dict(pollsterId='midgam_geva',folder='n12',candidate=tv+'reviewed-midgam-geva-poll.json',
         digest='82f8c61eda20fa28da3e5e47965289fe2a41f691c4a302e2bfc3afdfd8443424',
         seats={'yashar':24,'likud':21,'beyachad':14,'democrats':9,'yisrael_beiteinu':8,'utj':7,'joint':9,'shas':8,'otzma':8,'rz_zehut':7,'raam':5,'winter':0,'hendel':0,'gantz':0,'haredi_public':0},
         pct={'winter':2.8,'hendel':2.1,'gantz':1.4,'haredi_public':0.2},blocs={'coalition':51,'opposition':55,'arab_parties':14,'hendel':0},n=507,
         eligible=True,proof=tv+'n12-verification-summary.json',extract=tv+'n12-reviewed-facts.txt',
         local=tv+'n12-article-local-only.html',quote='מועד איסוף הנתונים: 19.10.2026',xproof=x+'n12-2026-10-19-reviewed-source-facts.json'),
    dict(pollsterId='hamadad_consortium',folder='c13',candidate=tv+'reviewed-hamadad-consortium-poll-r1.json',
         digest='43321eb4375131091c84e83fcc46ca7ac906a7de2e3316caf47ec68c6b04ae01',
         seats={'yashar':20,'likud':18,'beyachad':14,'democrats':9,'yisrael_beiteinu':8,'utj':7,'joint':9,'shas':7,'otzma':7,'rz_zehut':7,'raam':6,'winter':4,'hendel':4,'gantz':0,'haredi_public':0},
         pct={'haredi_public':1.0},blocs={'coalition':50,'opposition':51,'arab_parties':15,'hendel':4},n=1016,
         eligible=False,proof=tv+'c13-verification-summary-r1.json',extract=tv+'c13-reviewed-facts-r1.txt',
         xproof=x+'c13-2026-10-19-reviewed-source-facts.json',graphic=tv+'c13-original-seat-graphic.webp'),
    dict(pollsterId='next_data',folder='c14',candidate=tv+'reviewed-next-data-poll.json',
         digest='95347e71159dbcdc26675fd7fac9065682dbc0fc10da46fec880715a26391bf7',
         seats={'likud':30,'yashar':19,'beyachad':10,'democrats':10,'shas':10,'utj':8,'rz_zehut':7,'otzma':7,'yisrael_beiteinu':6,'joint':8,'raam':5,'winter':0,'hendel':0,'noam':0,'haredi_public':0},
         pct={'hendel':2.6,'winter':2.2,'noam':1.5,'haredi_public':0.3},blocs={'coalition':62,'opposition':45,'arab_parties':13},n=454,
         eligible=True,proof=tv+'c14-verification-summary.json',extract=tv+'c14-reviewed-facts.txt',
         local=tv+'c14-article-local-only.html',quote='נערך היום, 19 באוקטובר 2026',xproof=x+'c14-2026-10-19-reviewed-source-facts.json'),
    dict(pollsterId='lazar',folder='walla',candidate=pr+'reviewed-lazar-poll.json',
         digest='f5203cbf7443eebbfa42526fb43ec75cfe8ff69ddb31f6624444ee864b6c6bfc',
         seats={'yashar':23,'likud':19,'beyachad':14,'democrats':9,'yisrael_beiteinu':8,'shas':8,'utj':7,'otzma':8,'rz_zehut':6,'joint':8,'raam':6,'hendel':4,'winter':0},
         pct={'winter':2.9},blocs={'coalition':48,'opposition':54,'arab_parties':14,'hendel':4},n=601,
         eligible=True,proof=pr+'lazar-verification-summary.json',extract=pr+'walla-reviewed-facts.txt',
         local=pr+'reader-receipts-local-only.json',quote='הסקר נערך ב-19 באוקטובר 2026'),
]
polls=[]
public_sources=[]
for c in configs:
    p = read(ROOT / c['candidate'])
    assert sha(ROOT / c['candidate']) == c['digest']
    assert p['pollsterId'] == c['pollsterId'] and p['seats'] == c['seats'] and sum(c['seats'].values()) == 120
    assert p['reportedPercentages'] == c['pct'] and p['sourceBlocSeats'] == c['blocs'] and sum(c['blocs'].values()) == 120
    assert p['sampleSize'] == c['n'] and p['fieldworkVerified'] is c['eligible']
    paths=[c['candidate'],c['extract'],c['proof']]
    if 'xproof' in c:
        paths.append(c['xproof'])
    if 'graphic' in c:
        paths.append(c['graphic'])
    if c['pollsterId'] == 'next_data':
        paths += [tv+'source-coverage-summary.json',tv+'source-public-freeze-receipt-r1.json']
    if c['pollsterId'] == 'lazar':
        paths += [pr+'graphic-download-receipt.json']
    for path in paths:
        if path.startswith(tv) and Path(path).name != 'source-public-freeze-receipt-r1.json':
            assert Path(path).name in safe_names
    public_files=[ref(path) for path in paths]
    public_files.append(ref(c['candidate'],'frozen-reviewed-candidate.json'))
    evidence=[]
    if c['eligible']:
        assert p['fieldworkStart'] == p['fieldworkEnd'] == '2026-10-19'
        local = ROOT / c['local']
        text = re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',local.read_text('utf-8')))
        assert c['quote'] in text
        evidence=[{'file':c['proof'],'sha256':sha(ROOT/c['proof']),'quote':c['quote'],'sourceUrl':p['sourceUrl'],
                   'evidenceScope':'Concise exact date wording read in the original publisher. Public factual proof independently records the verified date; full original reader receipt remains local.',
                   'quoteVerifiedInLocalOriginalReceipt':{'file':c['local'],'sha256':sha(local)}}]
    else:
        assert p['fieldworkStart'] is None and p['fieldworkEnd'] is None
    polls.append({'pollsterId':c['pollsterId'],'folder':c['folder'],'candidatePath':c['candidate'],'candidateSha256':c['digest'],
                  'expectedSeats':c['seats'],'expectedReportedPercentages':c['pct'],'expectedSourceBlocSeats':c['blocs'],
                  'expectedSampleSize':c['n'],'strictEligible':c['eligible'],'fieldworkEvidence':evidence,'publicFiles':public_files})
    limitations=[]
    if c['pollsterId']=='hamadad_consortium':
        limitations=['Original graphic Likud18 accepted; article prose17 conflicts. Graphic total120 and coalition50 agree. Exact Haredi Public1.0% is separately attributed to the reviewed IsraelPolls historical table; all other exact shares remain missing. Fieldwork remains unknown; no date imputation and no strict trend inclusion.']
    if c['pollsterId']=='next_data':
        limitations=['Gantz absent from the original report; no old percentage inherited or measured zero invented. Named Ahi0.5% retained and mapped to model other only; raw other remains missing. Collection method and sampling error/confidence remain missing. Original graphic read live but raw download403; no archived image bytes claimed. Channel14 remains excluded by default.']
    if c['pollsterId']=='midgam_geva':
        limitations=['Data collected before the Gantz withdrawal announcement; original Gantz1.4% retained without redistribution. Supplementary intention-to-vote answers do not automatically change model turnout defaults. Original numerical graphic not separately archived or visually verified.']
    if c['pollsterId']=='lazar':
        limitations=['Two original graphic links retained but download/cache failures prevent an image archive or visual-verification claim; full vector verified in original article text. Prior Walla comparison is a poll described as fielded12October, not the active Maariv16October record being replaced. Confidence level and other exact percentages remain missing.']
    public_sources.append({'publisher':p['publisher']+' / '+p['pollster'],'urls':[p['sourceUrl']],
                           'status':'Original publisher numerical body read; bounded source review and independent numerical cross-check retained.',
                           'publicationDate':p['date'],'publicationTime':p.get('publicationTime'),
                           'fieldworkStart':p['fieldworkStart'],'fieldworkEnd':p['fieldworkEnd'],'sampleSize':p['sampleSize'],
                           'strictEligible':c['eligible'],'limitations':limitations,
                           'proof':{'path':c['folder']+'/'+Path(c['proof']).name,'sha256':sha(ROOT/c['proof'])}})

summary={'asOf':DAY,'status':'reviewed','scope':'Bounded factual source verification for three19October observations and one20October observation; audit date is not publication date. No exhaustive nationwide absence claim.',
         'fullCopyrightedArticleBodiesExcluded':True,'compiledTo120DatasetExcluded':True,
         'newObservationIds':[read(ROOT/c['candidate'])['id'] for c in configs],
         'observationPublicationDates':['2026-10-19','2026-10-20'],
         'sources':public_sources+[
             {'publisher':'IsraelPolls','urls':['https://x.com/IsraelPolls?s=20'],'status':'Fresh profile, three numerical graphics and historical tables read; primary publication metadata independently reviewed. C13 HarediPublic1.0% comes from the dated historical table, explicitly secondary.',
              'receipt':{'file':x+'scan-receipt.json','sha256':sha(ROOT/(x+'scan-receipt.json'))}},
             {'publisher':'Kan11 and i24NEWS','status':'Fresh original home and politics/poll indexes read. Latest inspected entries remain Kan1110393 and i2481805, both18October observations already retained; no additional complete vector verified in this bounded scope.',
              'coverageReceipt':{'file':pr+'scan-receipt.json','sha256':sha(ROOT/(pr+'scan-receipt.json'))}},
             {'publisher':'Channel16, IsraelHayom, ZmanIsrael','status':'Fresh direct primary home and politics/election/poll-index checks recorded in root coverage. No additional complete vector verified in inspected links. Channel16 player unavailable and archive/home date conflict retained; reader copies sometimes lag live pages.',
              'coverageReceipt':{'file':root_coverage,'sha256':sha(ROOT/root_coverage)}},
             {'publisher':'Maariv','status':'Existing browser safety restriction respected; reader errors retained. No successful current original check or absence claim, and no bypass. New Walla/Lazar observation is a distinct accessible original publication.'}],
         'deduplication':['Kan18October publication with19October page update remains one observation.','i24late X repost remains18October publication, not a new19October sample.','Walla383957955 republishes Kan18October; Walla383958175 is a separately fielded Lazar poll published20October.','Historical table replies, weekly summaries, Gantz-withdrawal scenario calculations and attitude questions are not independent new poll observations.'],
         'accessLimitations':['Maariv original source safety restriction and reader errors respected.','Channel16 player unavailable; neither full broadcast review nor nationwide absence established.','Walla original graphic download/cache failures retained; article-text verification is separate.','C14 graphic read live but not locally archived; no image hash claimed.','Some reader index copies lag live primary homepages.'],
         'gantzWithdrawalHandling':'Retain measured pre-withdrawal N12/C13 source data and all missing values; do not redistribute support without a published observation or explicit scenario.',
         'missingValuesAreNotZero':True,'compiledForecastsIngested':False,'supplementarySourceDiscovery':{'To120':'Not used as an independent poll or percentage source in this update.'}}
summary_path=ART/'primary-source-public-summary.json'
frozen_write(summary_path,summary)
plan={'status':'reviewed','asOf':DAY,'baselineAsOf':'2026-10-19','baselineRelease':'2026-10-19',
      'checkpointManifestSha256':MANIFEST_SHA,'baselinePublishedHead':HEAD,'observationPublicationDates':['2026-10-19','2026-10-20'],
      'publicCopyrightScopeReviewed':True,'publicEvidenceScope':'Original numerical graphic where archived, independently paraphrased facts, concise verified date quotations, source URLs/statuses and hashes only. Full authored articles, full reader bodies and compiled To120 data stay local.',
      'polls':polls,'sourceReview':{'requiredIsraelPollsUrl':'https://x.com/IsraelPolls?s=20','pollGraphicsAndHistoricalTablesChecked':True,
                                 'sameObservationRepostsNotCounted':True,'publicationVersusFieldwork':'N12/C13/C14 published19October; Walla published20October. N12/C14/Walla collection19October explicitly verified; C13 collection remains unknown. Audit20October.',
                                 'sourceDiscoveryLocalReceipt':x+'scan-receipt.json','sourceDiscoveryLocalSha256':sha(ROOT/(x+'scan-receipt.json')),
                                 'otherPublisherCoverage':{'file':root_coverage,'sha256':sha(ROOT/root_coverage),'publicName':'root-publisher-coverage.json'},
                                 'kanI24PrintCoverage':{'file':pr+'scan-receipt.json','sha256':sha(ROOT/(pr+'scan-receipt.json')),'publicName':'kan-i24-print-coverage.json'},
                                 'primarySourcePublicSummary':{'file':summary_path.relative_to(ROOT).as_posix(),'sha256':sha(summary_path)},
                                 'sourceClassification':'All four original publisher bodies read. C13 exact HarediPublic percentage has explicit secondary IsraelPolls attribution; source conflict retained.',
                                 'gantzWithdrawalHandling':summary['gantzWithdrawalHandling'],
                                 'channel14DefaultExclusionPreserved':True,'historicalAccuracyWeightsUnchanged':True,
                                 'reviewedExactPythonIntegerHelpersPreserved':True,'compiledForecastsIngested':False}}
path=ART/'source-plan.json'
frozen_write(path,plan)
print(json.dumps({'status':'PASS','asOf':DAY,'polls':len(polls),'sourcePlanSha256':sha(path),'primarySourcePublicSummarySha256':sha(summary_path),'candidateHashes':{p['pollsterId']:p['candidateSha256'] for p in polls},'strictEligible':{p['pollsterId']:p['strictEligible'] for p in polls}},ensure_ascii=False))
