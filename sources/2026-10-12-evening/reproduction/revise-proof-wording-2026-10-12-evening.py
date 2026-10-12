"""Correct one N12 evidence paraphrase without altering reported sample numbers.

Preserve the initial receipt/extract byte-for-byte and record the corrected proof
in a distinct revision. The original says initial sample500, not planned500.
"""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/poll-checks/2026-10-12-evening"
PUBLIC = ROOT / "github-pages/sources/2026-10-12-evening"
REVISION = PUBLIC / "n12/proof-wording-r1"
BASE = "https://victorchina-ops.github.io/israel-election-simulator/sources/2026-10-12-evening/n12/"
NEW_QUOTE = "מועד איסוף הנתונים:12.10.2026; גודל המדגם ההתחלתי:500; גודל המדגם בפועל:509; מספר האנשים שהתבקשו לענות:2,521; אינטרנט וטלפון; דגימת שכבות ובתוך השכבות דגימה אקראית."
FILES = ["data/current-polls.json", "data/poll-history.json", "data/sources.json",
         "data/survey-documents-2026-09-14.json", "artifacts/strict-post-close/n12-kan-c13-fieldwork.json",
         "artifacts/strict-post-close/c14-i24-fieldwork.json"]
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
encoded = lambda d: (json.dumps(d,ensure_ascii=False,indent=2)+"\n").encode("utf-8")


def main():
    assert not REVISION.exists(), "Do not overwrite reviewed correction"
    initial = read(ART / "ingestion-receipt.json")
    assert initial["status"] == "PASS"
    for rel,digest in initial["changedCanonicalFiles"].items():
        assert sha(ROOT / rel) == digest, rel
    for rel,digest in initial["publicEvidenceFiles"].items():
        assert sha(PUBLIC / rel) == digest, rel
    values = [read(ROOT / rel) for rel in FILES]
    current,history,sources,documents,audit,c14audit = values
    poll = next(p for p in current["polls"] if p["id"] == "midgam_geva_2026-10-12")
    before_poll = copy.deepcopy(poll)
    poll["secondarySourceUrls"] = [u for u in poll["secondarySourceUrls"] if u != BASE + "source-extract.txt"]
    poll["secondarySourceUrls"] += [BASE+"proof-wording-r1/source-extract.txt",
                                    BASE+"proof-wording-r1/reviewed-poll.json",
                                    BASE+"proof-wording-r1/revision-receipt.json"]
    poll["validationSourceUrl"] = BASE+"proof-wording-r1/reviewed-poll.json"
    historical = next(p for p in history["polls"] if p["id"] == "history_midgam_geva_2026-10-12_current")
    historical["secondarySourceUrls"] = copy.deepcopy(poll["secondarySourceUrls"])
    historical["validationSourceUrl"] = historical["archiveSourceUrl"] = poll["validationSourceUrl"]
    next(p for p in history["coverage"] if p["pollsterId"] == "midgam_geva")["validationSourceUrl"] = poll["validationSourceUrl"]
    history["supplementalSourceUrls"] = [u for u in history["supplementalSourceUrls"] if u != BASE+"source-extract.txt"]
    history["supplementalSourceUrls"] += [u for u in poll["secondarySourceUrls"] if u not in history["supplementalSourceUrls"]]
    next(s for s in sources["sources"] if s.get("id") == "midgam_geva")["secondarySourceUrls"] = copy.deepcopy(poll["secondarySourceUrls"])
    row = next(p for p in audit["rows"] if p["pollId"] == historical["id"])
    old_quote = row["evidenceParagraph"]
    assert "התכנון הראשוני" in old_quote
    row["evidenceParagraph"] = NEW_QUOTE
    row["evidence"][0]["quote"] = NEW_QUOTE
    row["evidence"][0]["quoteKind"] = "label-preserving-methodology-paraphrase"
    assert poll["initialSampleSize"] == before_poll["initialSampleSize"] == 500
    assert poll["sampleSize"] == before_poll["sampleSize"] == 509
    REVISION.mkdir(parents=True)
    text = (PUBLIC / "n12/source-extract.txt").read_text(encoding="utf-8")
    assert old_quote in text
    (REVISION / "source-extract.txt").write_bytes(text.replace(old_quote,NEW_QUOTE).encode("utf-8"))
    (REVISION / "reviewed-poll.json").write_bytes(encoded(poll))
    (REVISION / "ingested-poll.json").write_bytes(encoded(poll))
    for rel,value in zip(FILES,values):
        (ROOT / rel).write_bytes(encoded(value))
    correction = {"status":"PASS","asOf":"2026-10-12","revision":"proof-wording-r1",
                  "reason":"Original N12 label is initial sample500, not planned sample500. No reported number or numerical model input changes.",
                  "oldParaphrase":old_quote,"correctedParaphrase":NEW_QUOTE,
                  "sourceExtractSha256":sha(REVISION / "source-extract.txt"),
                  "initialIngestionReceiptSha256":sha(ART / "ingestion-receipt.json"),
                  "initialSourceExtractSha256":sha(PUBLIC / "n12/source-extract.txt"),
                  "initialPublicEvidenceHashes":initial["publicEvidenceFiles"],
                  "publishedDataUnchanged":True}
    (REVISION / "revision-receipt.json").write_bytes(encoded(correction))
    receipt = {**initial,"phase":"applied-proof-wording-r1-awaiting-independent-review",
               "revision":"proof-wording-r1","supersedesInitialReceiptSha256":sha(ART / "ingestion-receipt.json"),
               "changedCanonicalFiles":{rel:sha(ROOT / rel) for rel in FILES},
               "publicEvidenceFiles":{p.relative_to(PUBLIC).as_posix():sha(p) for p in sorted(PUBLIC.rglob('*')) if p.is_file()}}
    (ART / "ingestion-receipt-proof-wording-r1.json").write_bytes(encoded(receipt))
    print(json.dumps({"status":"PASS","revision":"proof-wording-r1","initialSampleSize":500,"sampleSize":509,
                      "receipt":"artifacts/poll-checks/2026-10-12-evening/ingestion-receipt-proof-wording-r1.json"}))


if __name__ == "__main__":
    main()
