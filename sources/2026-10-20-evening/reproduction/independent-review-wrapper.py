"""Independent read-only evening exact-wrapper compatibility review."""
from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path.cwd().resolve()
ART = ROOT / "artifacts/poll-checks/2026-10-20-evening"
COMP = ART / "numeric-compatibility"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt_path = COMP / "wrapper-compatibility.json"
proof = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
assert sha(receipt_path) == "9796fbaf4bbd72224c512e3dc93e76a1194c2ba4ad313d8dc72c9afeed41b9f3"
old = ROOT / "scripts/run-exact-trends-2026-10-20.py"
before = ART / "before/scripts/run-exact-trends-2026-10-20.py"
new = ROOT / "scripts/run-exact-trends-2026-10-20-evening.py"
assert sha(old) == sha(before) == proof["baselineWrapperSha256"]
assert sha(new) == proof["eveningWrapperSha256"] == "eaa11ad77097b51c40a21ca23a7427a2bffa8a502798a37c12053d05c654fea7"
old_bytes = old.read_bytes()
old_art = b'ART = ROOT / "artifacts/poll-checks/2026-10-20"'
new_art = b'ART = ROOT / "artifacts/poll-checks/2026-10-20-evening"'
assert old_bytes.count(old_art) == 1
assert old_bytes.replace(old_art, new_art, 1) == new.read_bytes()
old_text = old_bytes.decode("utf-8-sig")
normalized = new.read_text(encoding="utf-8-sig").replace(new_art.decode(), old_art.decode(), 1)
assert ast.dump(ast.parse(old_text), include_attributes=False) == ast.dump(ast.parse(normalized), include_attributes=False)
backend = ROOT / proof["backendPath"]
assert sha(backend) == proof["backendSha256"] == "ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035"
manifest = ART / "before/manifest.json"
assert sha(manifest) == proof["checkpointManifestSha256"]
checked_proofs = {}
for rel, expected in proof["existingProofHashes"].items():
    assert sha(ROOT / rel) == expected, rel
    checked_proofs[rel] = expected
source_mapping = next(n.value for n in ast.parse(old_text).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SOURCES" for t in n.targets))
pinned_helpers = ast.literal_eval(source_mapping)
helper_receipt = {}
for name, (rel, expected, output) in pinned_helpers.items():
    assert sha(ROOT / rel) == expected, rel
    helper_receipt[name] = {"path": rel, "sha256": expected}
result = {
    "schemaVersion": 1,
    "status": "PASS",
    "reviewedAtUtc": datetime.now(timezone.utc).isoformat(),
    "reviewerTask": "/root/c13_source_oct15",
    "originalCompatibilityReceiptSha256": sha(receipt_path),
    "baselineWrapperSha256": sha(old),
    "frozenCheckpointWrapperSha256": sha(before),
    "eveningWrapperSha256": sha(new),
    "byteExactExceptOneArtifactDirectoryLiteral": True,
    "normalizedAstIdentical": True,
    "allFourPinnedHelpersUnchanged": helper_receipt,
    "backendUnchangedSha256": sha(backend),
    "allExistingNumericalProofHashesRechecked": checked_proofs,
    "newNumericalTestOrInferenceChange": False,
    "numericalExecutionPerformedByReviewer": False,
    "conclusion": "Evening wrapper changes only artifact output/lineage directory. Primary/independent transforms, cohort, weights, OLS/GLS, exact marginals, tail tolerances, BH and sign-flip procedures are byte-identical. Previous backend equivalence proofs remain applicable; fresh evening numerical inputs still require their ordinary four recomputations and validation."
}
out = COMP / "independent-wrapper-review.json"
assert not out.exists(), "Do not overwrite completed independent review."
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "receipt": str(out.relative_to(ROOT)), "sha256": sha(out)}))

