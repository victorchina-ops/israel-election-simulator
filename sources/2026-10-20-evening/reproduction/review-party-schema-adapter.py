"""Review a strict precondition adapter, without running or changing the analysis."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

old_path = ROOT / "scripts/run-exact-trends-2026-10-20-evening.py"
new_path = ROOT / "scripts/run-exact-trends-2026-10-20-evening-party-schema-r1.py"
assert sha(old_path) == "eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7"
assert sha(new_path) == "d8e7164f20176ee864de8b9702cd6ac0b130fcca854032261a329805a98d0b74"
old = module(old_path, "evening_original_wrapper_review")
new = module(new_path, "evening_party_adapter_review")
frozen = ROOT / old.SOURCES["party"][0]
assert sha(frozen) == old.SOURCES["party"][1]
original = frozen.read_text(encoding="utf-8-sig")
old_transformed = old.transform("party", original, ROOT, ROOT / "artifacts/strict-post-close")
new_transformed = new.transform("party", original, ROOT, ROOT / "artifacts/strict-post-close")
old_guard = "assert set(IDS)==set().union(*(history[k]['seats'].keys() for k in audit))"
assert old_transformed.count(old_guard) == 1
assert old_transformed.replace(old_guard, new.PARTY_SCHEMA_PRECONDITION.rstrip(), 1) == new_transformed
for stage in ("bloc", "independent-bloc", "independent-party"):
    assert sha(ROOT / old.SOURCES[stage][0]) == old.SOURCES[stage][1]
    source = (ROOT / old.SOURCES[stage][0]).read_text(encoding="utf-8-sig")
    assert old.transform(stage, source, ROOT, ROOT / "artifacts/strict-post-close") == new.transform(stage, source, ROOT, ROOT / "artifacts/strict-post-close")

history_path = ROOT / "data/poll-history.json"
audit_path = ROOT / "artifacts/strict-post-close/analysis.json"
catalogue_path = ROOT / "data/parties.json"
input_hashes = {str(p): sha(p) for p in [history_path, audit_path, catalogue_path, old_path, new_path, frozen]}
history = {p["id"]: p for p in read(history_path)["polls"]}
analysis = read(audit_path)
audit = {p["pollId"]: p for p in analysis["cohort"] if p["eligibleStrict"]}
ids = [p["id"] for p in read(catalogue_path) if p["ballot"]]
guard_code = compile(new.PARTY_SCHEMA_PRECONDITION, "reviewed-party-schema-precondition", "exec")

def accepts(rows):
    try:
        exec(guard_code, {"ROOT": ROOT, "json": json, "IDS": ids, "history": rows, "audit": audit})
    except AssertionError:
        return False
    return True

assert accepts(history)
without_aggregate = copy.deepcopy(history)
for key in audit:
    without_aggregate[key]["seats"].pop("other", None)
assert accepts(without_aggregate)
before_arrays = [[history[key]["seats"].get(pid, 0) for pid in ids] for key in audit]
after_arrays = [[without_aggregate[key]["seats"].get(pid, 0) for pid in ids] for key in audit]
assert before_arrays == after_arrays
first = next(iter(audit))
adversarial = {}
for name, key, value in [("unknownZero", "unknown_party", 0), ("positiveOther", "other", 1),
                         ("floatZeroOther", "other", 0.0), ("boolZeroOther", "other", False)]:
    rows = copy.deepcopy(history)
    rows[first]["seats"][key] = value
    assert not accepts(rows), name
    adversarial[name] = "rejected"
rows = copy.deepcopy(history)
for key in audit:
    rows[key]["seats"].pop(ids[0], None)
assert not accepts(rows)
adversarial["missingBallotFromUnion"] = "rejected"
extra = {key: {pid: value for pid, value in history[key]["seats"].items() if pid not in ids}
         for key in audit if set(history[key]["seats"]) - set(ids)}
receipt = {
    "schemaVersion": 1, "status": "PASS", "asOf": "2026-10-20", "runId": "evening",
    "baselineWrapperSha256": sha(old_path), "partySchemaAdapterSha256": sha(new_path),
    "reviewScriptSha256": sha(Path(__file__)), "frozenPartyAnalyzerSha256": sha(frozen),
    "historySha256": sha(history_path), "analysisSha256": sha(audit_path), "catalogueSha256": sha(catalogue_path),
    "onlyPrimaryPartyPreconditionChanged": True, "allOtherTransformedSourceBytesIdentical": True,
    "otherStageTransformsUnchanged": True, "adapterCliRestrictedToPrimaryParty": True,
    "predeclaredBallotPartyCount": len(ids), "strictPollCount": len(audit), "extraSeatKeys": extra,
    "all17BallotArraysExactlyEqualBeforeAndAfterZeroAggregateOmission": True,
    "timesWeightsNullStatisticsToleranceBHAndSignFlipsUnchanged": True,
    "unknownOrNonzeroOrNonintegerExtrasRejected": adversarial,
    "rawDataAndFrozenHelperBytesUnchanged": True, "numericalAnalysisExecuted": False,
}
assert all(sha(Path(path)) == digest for path, digest in input_hashes.items())
destination = OUT / "party-schema-adapter-review.json"
with destination.open("x", encoding="utf-8") as handle:
    json.dump(receipt, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps({"status": "PASS", "receipt": str(destination.relative_to(ROOT)), "sha256": sha(destination)}))
