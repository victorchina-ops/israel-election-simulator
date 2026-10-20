"""Independent light review: zero-seat aggregate schema adapter; no analysis execution."""
from pathlib import Path
from datetime import datetime, timezone
import ast, copy, hashlib, json

ROOT = Path.cwd().resolve()
OUT = ROOT / "artifacts/poll-checks/2026-10-20-evening/numeric-compatibility"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
old_path = ROOT / "scripts/run-exact-trends-2026-10-20-evening.py"
new_path = ROOT / "scripts/run-exact-trends-2026-10-20-evening-party-schema-r1.py"
proof_path = OUT / "party-schema-adapter-review.json"
assert sha(old_path) == "eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7"
assert sha(new_path) == "d8e7164f20176ee864de8b9702cd6ac0b130fcca854032261a329805a98d0b74"
assert sha(proof_path) == "dc708e2df4a801f4299fb00244c1556b7d2addcc069ecc249026ba0651843877"
old_ast = ast.parse(old_path.read_text(encoding="utf-8-sig"))
new_ast = ast.parse(new_path.read_text(encoding="utf-8-sig"))
constant = next(n for n in new_ast.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PARTY_SCHEMA_PRECONDITION" for t in n.targets))
guard = ast.literal_eval(constant.value)
assert "type(history[_poll_id]['seats']['other']) is int" in guard
normalized = copy.deepcopy(new_ast)
normalized.body = [n for n in normalized.body if not (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PARTY_SCHEMA_PRECONDITION" for t in n.targets))]
transform = next(n for n in normalized.body if isinstance(n, ast.FunctionDef) and n.name == "transform")
stage_guard = transform.body.pop(0)
assert ast.unparse(stage_guard.test) == "stage == 'party'"
assert len(stage_guard.body) == 1
main = next(n for n in normalized.body if isinstance(n, ast.FunctionDef) and n.name == "main")
cli_guards = [n for n in main.body if isinstance(n, ast.Assert) and ast.unparse(n.test) == "args.stage == 'party'"]
assert len(cli_guards) == 1
main.body.remove(cli_guards[0])
assert ast.dump(normalized, include_attributes=False) == ast.dump(old_ast, include_attributes=False)
def transform_namespace(tree):
    nodes = [copy.deepcopy(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"patch_once", "transform"}]
    ns = {"Path": Path, "PARTY_SCHEMA_PRECONDITION": guard}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "independent-transform-review", "exec"), ns)
    return ns
old_ns, new_ns = transform_namespace(old_ast), transform_namespace(new_ast)
sources_node = next(n for n in old_ast.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SOURCES" for t in n.targets))
sources = ast.literal_eval(sources_node.value)
old_guard = "assert set(IDS)==set().union(*(history[k]['seats'].keys() for k in audit))"
for stage, (rel, digest, output) in sources.items():
    source_path = ROOT / rel
    assert sha(source_path) == digest
    text = source_path.read_text(encoding="utf-8-sig")
    before = old_ns["transform"](stage, text, ROOT, ROOT / "artifacts/strict-post-close")
    after = new_ns["transform"](stage, text, ROOT, ROOT / "artifacts/strict-post-close")
    if stage == "party":
        assert before.count(old_guard) == 1
        assert before.replace(old_guard, guard.rstrip(), 1) == after
    else:
        assert before == after
history_path = ROOT / "data/poll-history.json"
analysis_path = ROOT / "artifacts/strict-post-close/analysis.json"
catalog_path = ROOT / "data/parties.json"
proof = read(proof_path)
for key, path in [("historySha256", history_path), ("analysisSha256", analysis_path), ("catalogueSha256", catalog_path)]:
    assert sha(path) == proof[key]
history = {r["id"]: r for r in read(history_path)["polls"]}
audit = {r["pollId"]: r for r in read(analysis_path)["cohort"] if r["eligibleStrict"]}
catalog = read(catalog_path)
ids = [r["id"] for r in catalog if r["ballot"]]
assert len(ids) == 17 and len(audit) == 55
class MemoryFile:
    def __init__(self, content): self.content = content
    def read_text(self, **kwargs): return json.dumps(self.content)
class MemoryRoot:
    def __init__(self, content): self.content = content
    def __truediv__(self, path):
        assert path == "data/parties.json"
        return MemoryFile(self.content)
compiled = compile(guard, "independent-schema-guard-review", "exec")
def accepts(rows, cat=catalog):
    try:
        exec(compiled, {"ROOT": MemoryRoot(cat), "json": json, "IDS": ids, "history": rows, "audit": audit})
        return True
    except AssertionError:
        return False
cases = {}
assert accepts(history)
cases["actual55PollCohort"] = "accepted"
without = copy.deepcopy(history)
for k in audit: without[k]["seats"].pop("other", None)
assert accepts(without)
cases["originalCompatibleNoAggregate"] = "accepted"
assert [[history[k]["seats"].get(i, 0) for i in ids] for k in audit] == [[without[k]["seats"].get(i, 0) for i in ids] for k in audit]
first = next(iter(audit))
for name, value in [("positive",1),("negative",-1),("floatZero",0.0),("fraction",0.1),("boolFalse",False),("boolTrue",True),("stringZero","0"),("null",None),("list",[]),("mapping",{})]:
    rows = copy.deepcopy(history); rows[first]["seats"]["other"] = value
    assert not accepts(rows), name
    cases["other_"+name] = "rejected"
rows = copy.deepcopy(history); rows[first]["seats"]["unknown"] = 0
assert not accepts(rows)
cases["unknownZeroExtra"] = "rejected"
rows = copy.deepcopy(history)
for k in audit: rows[k]["seats"].pop(ids[0], None)
assert not accepts(rows)
cases["missingBallotFromUnion"] = "rejected"
for name, cat in [("missingOther", [r for r in catalog if r["id"] != "other"]), ("duplicateOther", catalog+[r for r in catalog if r["id"] == "other"])]:
    assert not accepts(history, cat)
    cases["catalog_"+name] = "rejected"
cat = copy.deepcopy(catalog)
next(r for r in cat if r["id"] == "other")["ballot"] = True
assert not accepts(history, cat)
cases["catalogOtherBallotTrue"] = "rejected"
lineage = {}
for stage in ["bloc", "independent-bloc"]:
    p = OUT.parent / "numeric-lineage" / (stage+"-enumeration-lineage.json")
    v = read(p)
    assert v["status"] == "PASS" and v["wrapperSha256"] == sha(old_path)
    assert v["inputHistorySha256"] == sha(history_path)
    lineage[stage] = sha(p)
result = {
    "schemaVersion":1,"status":"PASS","reviewedAtUtc":datetime.now(timezone.utc).isoformat(),
    "reviewerTask":"/root/c13_source_oct15","partyAdapterSha256":sha(new_path),"originalEveningWrapperSha256":sha(old_path),
    "agentProofSha256":sha(proof_path),"historySha256":sha(history_path),"analysisSha256":sha(analysis_path),"catalogueSha256":sha(catalog_path),
    "normalizedAdapterAstEqualsOriginalAfterRemovingOnlyGuardAdditionAndPartyCliRestriction":True,
    "actualPartyTransformDiffOnlyPinnedUnionGuardReplacement":True,"otherThreeStageTransformsByteIdentical":True,
    "predeclared17PartyNumericalArraysExactlyEqualWithAndWithoutZeroAggregate":True,
    "strictCohortPolls":55,"adversarialAndSemanticCases":cases,"caseCount":len(cases),
    "originalPassedBlocLineagesRetained":lineage,"noHeavyAnalysisOrNumericalRecomputation":True,
    "frozenHelpersAndOriginalWrapperUnmodified":True,
    "conclusion":"Narrowly accepts catalogued ballot:false other only at Python integer0; unknown/nonzero/noninteger extras and missing ballot-union coverage fail. Exact17-party arrays and complete transformed numerical code are unchanged. The genuine aggregate percentage is retained in raw data without adding an eighteenth statistical test."
}
out = OUT / "independent-party-schema-adapter-review.json"
with out.open("x", encoding="utf-8") as f: f.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":"PASS","receipt":str(out.relative_to(ROOT)),"sha256":sha(out),"cases":len(cases)}))

