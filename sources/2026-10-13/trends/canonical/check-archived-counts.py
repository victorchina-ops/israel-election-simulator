"""Validate scalar compressed enumeration against the frozen October 1 audit."""
from pathlib import Path
from itertools import permutations
import importlib.util,json,numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('counts',HERE/'independent-compressed-counts.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
old=json.loads((HERE/'archive-2026-10-01/party-analysis.json').read_text(encoding='utf-8-sig'))
blocks=[]
for series in old['primary']['byPollster']:
    y=np.asarray([r['seats'] for r in series['parties']]).T
    orders=np.asarray(list(permutations(range(len(y)))))
    blocks.append(helper.score_blocks(series['timeDaysFromFirst'],y,orders,series['weight']))
observed=np.asarray([r['slopePerWeek'] for r in old['primary']['overall']])
counts,total,sizes=helper.direct_tail_counts(blocks,observed)
assert total==old['primary']['exactCounting']['nPermutations']
assert counts.tolist()==old['primary']['exactCounting']['extremeCounts']
print(json.dumps({'passed':True,'baseline':old['asOf'],'permutations':total,'parties':len(counts),'compressedHalfSizes':sizes}))
