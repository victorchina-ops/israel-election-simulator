"""Check score compression against direct full Cartesian null enumeration."""
import importlib.util
from itertools import permutations, product
from pathlib import Path
import numpy as np

path=Path(__file__).with_name('independent-compressed-counts.py')
spec=importlib.util.spec_from_file_location('compressed',path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
cases=[([0,2.5,7],[[2,0],[2,0],[4,0]],.3),
       ([0,3,6,9],[[1,0],[2,0],[2,0],[3,0]],.5),
       ([0,7],[[6,0],[5,0]],.2)]
compressed=[];full=[];observed=np.zeros(2)
for times,seats,weight in cases:
    t=np.asarray(times);y=np.asarray(seats)
    orders=np.asarray(list(permutations(range(len(t)))))
    x=t-t.mean();coef=7*x/(x@x)
    null=weight*np.einsum('i,pij->pj',coef,y[orders])
    observed+=weight*coef@y
    full.append(null)
    compressed.append(helper.score_blocks(t,y,orders,weight))
counts,total,sizes=helper.direct_tail_counts(compressed,observed)
enumerated=np.asarray([sum(rows) for rows in product(*full)])
expected=np.sum(abs(enumerated)>=abs(observed)-1e-10,axis=0)
assert total==len(enumerated)==288
assert np.array_equal(counts,expected)
assert counts[1]==total
assert any(len(block[0])<int(block[1].sum()) for blocks in compressed for block in blocks)
print({'passed':True,'permutations':total,'counts':counts.tolist(),'compressedHalfSizes':sizes})
