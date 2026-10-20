"""Freeze three independently reviewed evening20Oct observations before ingestion."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-20-evening'
DAY='2026-10-20'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text('utf-8-sig'))
def write(p,v):
 b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 if p.exists():assert p.read_bytes()==b,('Frozen evidence differs',str(p))
 else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def ref(p,name=None):
 assert p.resolve().is_relative_to(ART.resolve()) and 'local-only' not in p.name and p.suffix not in ['.html','.htm']
 return {'sourcePath':p.relative_to(ROOT).as_posix(),'publicName':name or p.name,'sha256':sha(p)}
manifest=ART/'before/manifest.json'
assert sha(manifest)=='e33c92802d6f8af5497c11279dc9ebcf84de2aea9d75dc92cc8ad9ccddfb6363'
assert read(manifest)['historyPollCount']==132 and read(ART/'checkpoint-freeze.json')['status']=='PASS'
configs=[
 ('maagar_mochot','c16','source-c16/reviewed-maagar-poll.json','source-c16/maagar-verification-summary.json','source-c16/c16-reviewed-facts.txt',2026,{'haredi_public':.6,'other':.2},{'coalition':50,'opposition':52,'arab_parties':14,'hendel':4},'2026-10-19','נערך אתמול והיום וכלל 2,026 משיבים'),
 ('direct_polls','i24','source-i24/reviewed-direct-poll.json','source-i24/i24-verification-summary.json','source-i24/reviewed-primary-facts.txt',521,{'winter':3.1,'hendel':2.6},{'coalition':58,'opposition':48,'arab_parties':14},'2026-10-20','בתאריך ה-20 באוקטובר 2026'),
 ('next_data','c14','source-c14/reviewed-next-data-poll.json','source-c14/c14-verification-summary.json','source-c14/c14-reviewed-facts.txt',2116,{'hendel':2.5,'winter':1.9,'noam':.9,'haredi_public':.9},{'coalition':62,'opposition':44,'arab_parties':14},'2026-10-20','נערך היום 20 באוקטובר 2026'),
]
expected_seats={
 'maagar_mochot':{'yashar':21,'likud':18,'beyachad':15,'democrats':9,'otzma':9,'joint':9,'utj':7,'yisrael_beiteinu':7,'shas':6,'rz_zehut':6,'raam':5,'winter':4,'hendel':4,'haredi_public':0,'other':0},
 'direct_polls':{'likud':26,'yashar':20,'beyachad':12,'otzma':9,'democrats':9,'shas':8,'utj':8,'joint':8,'yisrael_beiteinu':7,'rz_zehut':7,'raam':6,'winter':0,'hendel':0,'haredi_public':0,'noam':0,'israel_first':0},
 'next_data':{'likud':30,'yashar':20,'beyachad':9,'democrats':9,'shas':9,'utj':8,'rz_zehut':7,'otzma':8,'yisrael_beiteinu':6,'joint':8,'raam':6,'winter':0,'hendel':0,'noam':0,'haredi_public':0},
}
polls=[];sources=[]
for pid,folder,cp,pp,fp,n,pcts,blocs,start,quote in configs:
 c,proof,facts=ART/cp,ART/pp,ART/fp;p=read(c)
 assert p['pollsterId']==pid and p['date']==DAY and p['seats']==expected_seats[pid] and sum(p['seats'].values())==120
 assert p['sampleSize']==n and p['reportedPercentages']==pcts and p['sourceBlocSeats']==blocs and sum(blocs.values())==120
 assert p['fieldworkVerified'] is True and p['fieldworkStart']==start and p['fieldworkEnd']==DAY
 assert sha(facts)==p['sourceDocument']['sha256']==p['sourceDocument']['extractSha256']
 files=[c,proof,facts]
 if pid=='maagar_mochot':
  files += [ART/'source-c16'/name for name in read(proof)['safePublicFiles'] if name not in {c.name,proof.name,facts.name}]
  files += [ART/'source-c16/c16-second-clip-independent-review.json']
  field=ART/'source-c16/c16-fieldwork-proof.json'
  assert p['reportedMarginOfErrorPct'] is None and {v['pct'] for v in p['reportedMarginOfErrorConflict']['values']}=={2.1,4.2}
  limitation='Final settled frames in two original clips agree. Intermediate animation counts rejected. Relative collection wording anchored to20Oct clip titles verifies19–20Oct. Conflicting published MOE2.1/4.2 retained; canonical MOE and confidence missing.'
 elif pid=='direct_polls':
  files += [ART/'source-i24/reviewed-primary-candidate.json',ART/'source-i24/israelpolls-i24-facts.json']
  field=proof
  assert p['sourceBlocProseAsPrinted']['opposition']==47 and p['sourceBlocSeats']['opposition']==48
  assert 'gantz' not in p['seats'] and 'other' not in p['reportedPercentages']
  limitation='Primary prose opposition47 conflicts with full120-seat vector and visually reviewed source graphic48; accepted48 independently. Five <1% named bounds are not exact shares; Gantz absent remains missing. No exact aggregate other is imputed.'
 else:
  files += [ART/'source-c14-independent/independent-c14-facts.json']
  field=proof
  assert 'other' not in p['reportedPercentages'] and p['percentages']['other']==.4 and p['modelOnlyPercentageIds']==['other']
  limitation='Original prior-Joint comparison7 conflicts with retained19Oct8; current20Oct8 and full120 vector verified. Named Ahi.4% maps only to model other; raw other remains missing. Collection method/MOE/confidence missing. Channel14 default exclusion preserved.'
 public=[ref(x) for x in dict.fromkeys(files)]+[ref(c,'frozen-reviewed-candidate.json')]
 evidence=[{'file':field.relative_to(ROOT).as_posix(),'sha256':sha(field),'quote':quote,'sourceUrl':p['sourceUrl'],'evidenceScope':limitation}]
 polls.append({'pollsterId':pid,'folder':folder,'candidatePath':c.relative_to(ROOT).as_posix(),'candidateSha256':sha(c),'expectedSeats':expected_seats[pid],'expectedReportedPercentages':pcts,'expectedSourceBlocSeats':blocs,'expectedSampleSize':n,'strictEligible':True,'fieldworkEvidence':evidence,'publicFiles':public})
 sources.append({'publisher':p['publisher']+' / '+p['pollster'],'urls':[p['sourceUrl']],'status':'Original publisher independently verified; complete observation and missingness reviewed.','publicationDate':p['date'],'publicationTime':p.get('publicationTime'),'fieldworkStart':start,'fieldworkEnd':DAY,'sampleSize':n,'strictEligible':True,'limitations':[limitation],'proof':{'path':folder+'/'+proof.name,'sha256':sha(proof)}})
x=ART/'source-israelpolls/scan-receipt.json';coverage=ART/'source-root-coverage.json'
summary={'asOf':DAY,'runId':'evening','status':'reviewed','scope':'Three new original20October observations added after the completed daytime20October release. Bounded scan; no nationwide absence claim.','fullCopyrightedArticleBodiesExcluded':True,'compiledTo120DatasetExcluded':True,'newObservationIds':[read(ROOT/p['candidatePath'])['id'] for p in polls],'observationPublicationDates':[DAY],'sources':sources,'requiredIsraelPolls':{'url':'https://x.com/IsraelPolls?s=20','receiptSha256':sha(x),'status':'Profile, i24 original graphics and history table visually read; no C16 post seen in bounded profile. C16 verified directly from primary search and two clips.','repostTimesNotPollDates':True},'otherPublishers':read(coverage),'deduplication':['Two C16 original video edits are one observation.','i24 X graphics/table are one20October observation.','Walla20October alreadyincluded; N1219October midnightupdate is not anotherpoll.','Channel14 post-withdrawal20October complete vector is genuinely new; not a redistribution scenario.'],'accessLimitations':['Kan11 reader empty; no successful current content/absence claim.','Maariv original inaccessible; restriction respected.','Some primary reader indexes lag current pages.'],'missingValuesAreNotZero':True,'compiledForecastsIngested':False}
write(ART/'primary-source-public-summary.json',summary)
plan={'status':'reviewed','asOf':DAY,'runId':'evening','baselineAsOf':DAY,'baselineRelease':'2026-10-20','checkpointManifestSha256':sha(manifest),'baselinePublishedHead':'c5008c2874363e8fad1698c80b75107013d2c338','observationPublicationDates':[DAY],'publicCopyrightScopeReviewed':True,'publicEvidenceScope':'Concise factual extracts, reviewed numerical source frames, URLs, source-status and hashes only. Full articles, full reader exports and compiled To120 data remain local.','polls':polls,'sourceReview':{'requiredIsraelPollsUrl':'https://x.com/IsraelPolls?s=20','pollGraphicsAndHistoricalTablesChecked':True,'sameObservationRepostsNotCounted':True,'publicationVersusFieldwork':'All published20Oct; C16 collected19–20Oct, i24 andC14 collected20Oct. Same-day evening release distinguished from daytime release.','sourceDiscoveryLocalReceipt':x.relative_to(ROOT).as_posix(),'sourceDiscoveryLocalSha256':sha(x),'otherPublisherCoverage':{'file':coverage.relative_to(ROOT).as_posix(),'sha256':sha(coverage),'publicName':'root-publisher-coverage.json'},'primarySourcePublicSummary':{'file':(ART/'primary-source-public-summary.json').relative_to(ROOT).as_posix(),'sha256':sha(ART/'primary-source-public-summary.json')},'sourceClassification':'All three primary observations verified; C16 independently read in two edits, i24 original graphics/table cross-checked, C14 original body independently read.','channel14DefaultExclusionPreserved':True,'historicalAccuracyWeightsUnchanged':True,'reviewedExactPythonIntegerHelpersPreserved':True,'compiledForecastsIngested':False}}
write(ART/'source-plan.json',plan)
print(json.dumps({'status':'PASS','sourcePlanSha256':sha(ART/'source-plan.json'),'polls':len(polls),'strictEligible':True,'candidates':{p['pollsterId']:p['candidateSha256'] for p in polls}}))
