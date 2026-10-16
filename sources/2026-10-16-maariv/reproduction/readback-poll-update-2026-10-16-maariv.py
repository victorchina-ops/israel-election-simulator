"""Verify the October16 public release bytes, factual source scope and model inputs."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import re
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-16"
RELEASE = "2026-10-16-maariv"
ART = ROOT / "artifacts/poll-checks" / RELEASE
REPO = ROOT / "github-pages"
BASE = "https://victorchina-ops.github.io/israel-election-simulator/"
PREFIX = "sources/" + RELEASE + "/"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda body: hashlib.sha256(body).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{40}", args.commit)
    release = read(ART / "publication-receipt.json")
    plan = read(ART / "source-plan.json")
    assert release["asOf"] == plan["asOf"] == DAY
    assert release["newPollCount"] == len(plan["polls"]) == 1
    paths = ["index.html", "README.md", PREFIX + "release.json"]
    paths += [row["path"] for row in release["files"]]
    paths += [p.relative_to(REPO).as_posix() for p in (REPO / PREFIX).rglob("*") if p.is_file()]
    paths = sorted(set(paths))

    def fetch(path):
        request = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/") + "?release=" + args.commit,
            headers={"User-Agent": "Election-Simulator-Release-Check", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=40) as response:
            body, status = response.read(), response.status
        local = (REPO / path).read_bytes()
        assert status == 200 and body == local, ("Public mismatch", path, status, sha(body), sha(local))
        return {"path": path, "status": status, "sha256": sha(body), "bytes": len(body)}, body

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, paths))
    bodies = {row["path"]: body for row, body in results}
    public_json = lambda name: json.loads(bodies[PREFIX + name].decode("utf-8-sig"))
    current, history = public_json("current-polls.json"), public_json("poll-history.json")
    assert current["asOf"] == history["asOf"] == DAY
    assert len(current["polls"]) == release["activePolls"]
    assert len(history["polls"]) == release["historyPolls"]
    expected = {read(ROOT / s["candidatePath"])["id"] for s in plan["polls"]}
    assert {spec['pollsterId'] for spec in plan['polls']} == {'lazar'}
    assert expected <= {p['id'] for p in current['polls']}
    assert len(current['polls'])==release['activePolls'] and len(history['polls'])==release['historyPolls']
    before=json.loads((ART/'before/data/poll-history.json').read_text(encoding='utf-8-sig'))
    assert len(history['polls'])==len(before['polls'])+len(plan['polls'])
    for poll in current["polls"]:
        assert sum(poll["seats"].values()) == 120
    for name in ["strict-party-trends.json", "strict-party-trends-without-channel14.json", "poll-correlation.json"]:
        assert public_json(name)["asOf"] == DAY
    assert public_json("strict-party-trends-without-channel14.json")["coverage"]["pollCount"] == release["eligibleWithout14"]
    assert public_json("strict-party-trends.json")["coverage"]["pollCount"] == release["eligibleFull"]
    assert public_json("release.json") == release
    assert public_json("source-plan.json") == plan
    assert release["fullArticleBodiesExcludedFromNewRelease"] is True
    assert release["compiledTo120DatasetExcludedFromNewRelease"] is True
    html = bodies["index.html"]
    assert sha(html) == release["publishedHtmlSha256"]
    assert release["snapshotSha256"].encode() in html
    assert not re.search(rb'<meta\b[^>]*\bname\s*=\s*["\x27]data-app-local-thread["\x27]', html, re.I)
    assert b"01a0952c-a40b-7b01-b019-621f0cee2656" not in html
    report = {"status": "PASS", "asOf": DAY, "commit": args.commit, "url": BASE,
        "filesVerified": len(results), "publicBytesMatchPackagedFiles": True,
        "activePolls": release["activePolls"], "historyPolls": release["historyPolls"],
        "defaultStrictPolls": release["eligibleWithout14"], "fullStrictPolls": release["eligibleFull"],
        "newObservationIds": sorted(expected), "snapshotSha256": release["snapshotSha256"], "htmlSha256": sha(html),
        "validatorSha256": sha(Path(__file__).read_bytes()),
        "localThreadMetaAbsent": True, "localThreadIdentifierAbsent": True,
        "rows": [row for row, body in results]}
    output = ART / "public-readback.json"
    assert not output.exists(), "Preserve previous readback; do not overwrite it."
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
