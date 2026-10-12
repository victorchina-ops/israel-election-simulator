"""Compare the three October 2 additions with the frozen October 1 strict audit."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BEFORE=HERE/'archive-2026-10-01'
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))

def compare(filename,key,fields):
    old,new=read(BEFORE/filename),read(HERE/filename)
    assert old['asOf']=='2026-10-01' and new['asOf']=='2026-10-02'
    assert old['normalizedHistoricalWeights']==new['normalizedHistoricalWeights']
    a={r['pollId']:r for r in old['cohort']};b={r['pollId']:r for r in new['cohort']}
    added=sorted(set(b)-set(a))
    assert len(added)==3 and set(a)<=set(b)
    assert all(a[p]==b[p] for p in a)
    assert {b[p]['pollsterId'] for p in added}=={'next_data','direct_polls','lazar'}
    assert all(b[p]['eligibleStrict'] for p in added)
    axes={}
    for axis in ['primary','publicationDateSensitivity']:
        x,y=old[axis],new[axis]
        assert y['nPolls']==x['nPolls']+3 and y['nDeltas']==x['nDeltas']+3
        xx={r['pollsterId']:r for r in x['byPollster']};yy={r['pollsterId']:r for r in y['byPollster']}
        assert set(xx)==set(yy)
        for pid in xx:
            extra=[p for p in added if b[p]['pollsterId']==pid]
            assert yy[pid]['pollIds']==xx[pid]['pollIds']+extra
        first={r[key]:r for r in x['overall']};last={r[key]:r for r in y['overall']}
        axes[axis]={'counts':{'beforePolls':x['nPolls'],'afterPolls':y['nPolls'],
            'beforeDeltas':x['nDeltas'],'afterDeltas':y['nDeltas'],
            'beforePermutations':x['exactCounting']['nPermutations'],'afterPermutations':y['exactCounting']['nPermutations']},
            'results':[{key:k,**{f:{'before':first[k][f],'after':last[k][f],'change':last[k][f]-first[k][f]} for f in fields}} for k in first]}
    return {'addedPolls':[b[p] for p in added],'axes':axes}

bloc=compare('analysis.json','group',['weightedNetDelta','slopePerWeek','pValue','qValue','wholeInstituteSignFlipP','wholeInstituteSignFlipQ'])
party=compare('party-analysis.json','partyId',['weightedNetDelta','slopePerWeek','pValue','qValue','wholeSeriesSignFlipP','wholeSeriesSignFlipQ'])
assert bloc['addedPolls']==party['addedPolls']
report={'baseline':'2026-10-01','updated':'2026-10-02',
    'design':'Same strict fieldwork rule, party/bloc definitions and historical-quality weights; three original-source-verified fieldwork additions.',
    'addedPolls':bloc['addedPolls'],'blocs':bloc['axes'],'parties':party['axes']}
out=ROOT/'artifacts/2026-10-02-comparison';out.mkdir(exist_ok=True)
(out/'strict-trends-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'addedPollIds':[r['pollId'] for r in report['addedPolls']], 'counts':report['blocs']['primary']['counts']}))
