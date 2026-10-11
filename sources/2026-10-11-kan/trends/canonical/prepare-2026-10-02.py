"""Preserve the existing test design while refreshing its October 2 inputs."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def edit(path, replacements):
    text = path.read_text(encoding='utf-8-sig')
    for old, new in replacements:
        assert old in text, (str(path), old[:80])
        text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')

party = HERE/'party-independent.py'
text = party.read_text(encoding='utf-8-sig')
text = text.replace('import hashlib\n', 'import hashlib\nimport importlib.util\n')
text = text.replace('OUT = Path(__file__).resolve().parent\n', "OUT = Path(__file__).resolve().parent\nhelper_spec = importlib.util.spec_from_file_location('independent_compressed_counts', OUT/'independent-compressed-counts.py')\nhelper = importlib.util.module_from_spec(helper_spec)\nhelper_spec.loader.exec_module(helper)\n")
text = text.replace('perms=[]\n', 'perms=[]\ncompressed=[]\n')
text = text.replace('    cases=np.asarray([np.linalg.lstsq(design,yy[list(order)],rcond=None)[0][1]\n                      for order in permutations(range(len(polls)))])', '    orders=np.asarray(list(permutations(range(len(polls)))))\n    cases=np.asarray([np.linalg.lstsq(design,yy[order],rcond=None)[0][1]\n                      for order in orders])')
text = text.replace('    perms.append(w*cases)\n', '    perms.append(w*cases)\n    compressed.append(helper.score_blocks(xx, yy, orders, w))\n')
start = text.index('# Enumerate the complete Cartesian distribution')
end = text.index('pv=counts/total', start)
text = text[:start] + "counts,total,compressed_sizes=helper.direct_tail_counts(compressed,obs)\nassert total==math.prod(math.factorial(row['n']) for row in records)\n" + text[end:]
text = text.replace("'nPermutations':total,'nSignPatterns':128,", "'independentCounting':'Independent lstsq slopes and direct bounded scalar Cartesian tails with integer-score multiplicities.',\n        'compressedHalfSizes':compressed_sizes,\n        'nPermutations':total,'nSignPatterns':128,")
party.write_text(text, encoding='utf-8')

bloc = ROOT/'artifacts/audit-strict-full-series-2026-09-28.py'
text = bloc.read_text(encoding='utf-8-sig')
text = text.replace('import json,collections,datetime,itertools,numpy as np', 'import json,collections,datetime,itertools,importlib.util,numpy as np')
text = text.replace("for f in files:", "helper_spec=importlib.util.spec_from_file_location('independent_compressed_counts',R/'artifacts/strict-post-close/independent-compressed-counts.py');helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper);compressed=[]\nfor f in files:")
old = "x-=x.mean();coef=x/(x@x)*7;y="
new = "times=x.copy();x-=x.mean();coef=x/(x@x)*7;y="
assert old in text
text = text.replace(old,new)
text = text.replace("if np.max(np.abs(dist))<1e-12:constant_factor*=len(dist)", "compressed.append(helper.score_blocks(times,y,np.asarray(list(itertools.permutations(range(len(rs))))),weight))\n if np.max(np.abs(dist))<1e-12:constant_factor*=len(dist)")
start = text.index('blocks.sort(key=len,reverse=True)')
end = text.index("report=", start)
text = text[:start] + 'counts,total,compressed_sizes=helper.direct_tail_counts(compressed,obs)\np=counts/total\n' + text[end:]
text = text.replace("(counts*constant_factor).tolist()", "counts.tolist()")
text = text.replace("Independent full Cartesian enumeration in bounded chunks after removing identically-zero bloc permutation factors; no searchsorted counting. Date arithmetic is relative to first fieldwork day to avoid floating point cancellation.", "Independent direct scalar Cartesian enumeration in bounded chunks, preserving exact integer-score permutation multiplicities; no searchsorted counting. Relative fieldwork-day arithmetic avoids cancellation.")
text = text.replace("'individual':individual", "'compressedHalfSizes':compressed_sizes,'individual':individual")
bloc.write_text(text,encoding='utf-8')

edit(ROOT/'artifacts/analyze-strict-post-close-2026-09-28.py', [('Only3–5 observations per institute;', 'Only3–6 observations per institute;')])
edit(HERE/'validate-current.py', [('"2026-10-01"', '"2026-10-02"'), ('== 25', '== 28'), ('89_579_520', '10_749_542_400'), ('"polls": 25', '"polls": 28'), ('"deltas": 18', '"deltas": 21')])
print('Prepared independent audits and current validation expectations.')
