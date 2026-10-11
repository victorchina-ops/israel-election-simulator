"""Preserve the initial Oct11 ingestion and mark derived Other as model-only.

Creates a distinct reviewed revision; never overwrites frozen source evidence
or the initial ingestion/publication receipts.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-11"
PUBLIC = ROOT / "github-pages/sources/2026-10-11-kan"
SUB = PUBLIC / "model-only-r1"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location("kan_oct11_ingester", ROOT / "scripts/ingest-kan-2026-10-11.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
manifest = module.frozen_check()
candidate, hashes = module.candidate_check()
initial = read(ART / "ingestion-receipt.json")
assert read(ART / "ingestion-validation.json")["status"] == "PASS"
assert not SUB.exists(), "Existing reviewed revision is immutable"
for rel, digest in initial["changedCanonicalFiles"].items():
    assert sha(ROOT / rel) == digest, rel
for name, digest in initial["publicEvidenceFiles"].items():
    assert sha(PUBLIC / name) == digest, name
preserved = {p.relative_to(PUBLIC).as_posix(): sha(p) for p in PUBLIC.iterdir() if p.is_file()}
current = read(ROOT / "data/current-polls.json")
history = read(ROOT / "data/poll-history.json")
sources = read(ROOT / "data/sources.json")
active = next(row for row in current["polls"] if row["id"] == module.ID)
old = copy.deepcopy(active)
assert "modelOnlyPercentageIds" not in active
active["modelOnlyPercentageIds"] = ["other"]
active["validationSourceUrl"] = module.PUBLIC_BASE + "model-only-r1/reviewed-poll.json"
active["secondarySourceUrls"] += [module.PUBLIC_BASE + "model-only-r1/reviewed-poll.json", module.PUBLIC_BASE + "model-only-r1/revision-receipt.json"]
assert active["percentages"] == old["percentages"] and active["reportedPercentages"] == old["reportedPercentages"]
archived = next(row for row in history["polls"] if row["id"] == module.HISTORY_ID)
archived["modelOnlyPercentageIds"] = ["other"]
archived["validationSourceUrl"] = active["validationSourceUrl"]
archived["archiveSourceUrl"] = active["validationSourceUrl"]
archived["secondarySourceUrls"] = copy.deepcopy(active["secondarySourceUrls"])
source = next(row for row in sources["sources"] if row.get("id") == "kantar")
source["secondarySourceUrls"] = copy.deepcopy(active["secondarySourceUrls"])
SUB.mkdir(parents=True)
module.write_new(SUB / "reviewed-poll.json", active)
module.write_new(SUB / "ingested-poll.json", active)
for name, data in [("current-polls", current), ("poll-history", history), ("sources", sources)]:
    (ROOT / f"data/{name}.json").write_bytes(module.encoded(data))
assert all(sha(PUBLIC / name) == digest for name, digest in preserved.items())
receipt = {**initial, "phase": "applied-model-only-r1-awaiting-independent-review", "revisionId": "model-only-r1",
           "reason": "Mark documented named-party sum Other1.2 as model-only; prevent reportedSupport fallback from labeling it as published support.",
           "initialIngestionReceiptSha256": sha(ART / "ingestion-receipt.json"),
           "initialValidationSha256": sha(ART / "ingestion-validation.json"),
           "initialPublicEvidenceHashesPreserved": preserved,
           "publishedValuesUnchanged": True, "modelOnlyPercentageIds": ["other"],
           "changedCanonicalFiles": {rel: sha(ROOT / rel) for rel in module.MUTABLE},
           "normalizedRecordPublicPath": "model-only-r1/reviewed-poll.json",
           "publicEvidenceFiles": {p.relative_to(PUBLIC).as_posix(): sha(p) for p in PUBLIC.rglob("*") if p.is_file()}}
module.write_new(ART / "ingestion-receipt-model-only-r1.json", receipt)
module.write_new(SUB / "revision-receipt.json", receipt)
module.frozen_check()
print(json.dumps({"status": "PASS", "revisionId": "model-only-r1", "publishedValuesUnchanged": True, "initialPublicEvidenceFilesPreserved": len(preserved)}))
