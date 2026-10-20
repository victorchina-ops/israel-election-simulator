"""Package the four October19/20 observations in the October20 audit after independent checks.

Run only after canonical, numerical, replay, browser, visual and social receipts
pass. Existing published sources, content, runtime and artwork are immutable.
New source publication is an explicit factual/graphic allowlist: raw article
bodies, full reader exports and To120 compiled data remain local.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "github-pages"
DAY = "2026-10-20"
RELEASE = "2026-10-20"
ART = ROOT / "artifacts/poll-checks" / RELEASE
PREFIX = "sources/" + RELEASE
SOCIAL = ROOT / "outputs/social/2026-10-20"
EXPECTED = {"midgam_geva", "hamadad_consortium", "next_data", "lazar"}
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def immutable_write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, f"Changed dated receipt: {path}"
    else:
        path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the complete package without writing any file")
    args = parser.parse_args()
    files = {}
    copies, writes = {}, {}
    checkpoint = read(ART / "before/manifest.json")
    plan = read(ART / "source-plan.json")
    assert plan["status"] == "reviewed" and plan["asOf"] == DAY
    assert plan["publicCopyrightScopeReviewed"] is True
    assert {p["pollsterId"] for p in plan["polls"]} == EXPECTED and len(plan["polls"]) == 4
    assert {read(ROOT / p['candidatePath'])['date'] for p in plan['polls']} == {'2026-10-19','2026-10-20'}
    assert not (ART / "publication-receipt.json").exists(), "Preserve the existing dated release."
    assert not (REPO / "updates" / RELEASE).exists(), "Preserve previously published social assets."

    def preserved():
        for group in ["authorContentHashes", "protectedRuntimeHashes", "frozenEvidenceHashes", "frozenConditionalAndArtisticHashes", "reviewedExactHelpers"]:
            for rel, digest in checkpoint[group].items():
                assert sha(ROOT / rel) == sha(ART / "before" / rel) == digest, (group, rel)
        mutable_data={'current-polls.json','poll-history.json','sources.json','survey-documents-2026-09-14.json',
            'strict-party-trends.json','strict-party-trends-without-channel14.json','poll-correlation.json'}
        for path in (ROOT / 'data').glob('*.json'):
            if path.name not in mutable_data:
                rel=path.relative_to(ROOT).as_posix()
                assert sha(path) == checkpoint['files'][rel], ('Unchanged model input', rel)

    def record(dest):
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(dest), "bytes": dest.stat().st_size}

    def copy(source, name):
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        dest = REPO / PREFIX / name
        assert source.is_file(), source
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), f"Dated evidence differs: {dest}"
        if dest in copies:
            assert source.read_bytes() == copies[dest].read_bytes(), ("Duplicate destination differs", dest)
        copies[dest] = source
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(source), "bytes": source.stat().st_size}

    preserved()
    for name in ["ingestion-validation.json", "strict-validation.json", "model-comparison-validation.json", "model-comparisons-independent-review.json"]:
        assert read(ART / name)["status"] == "PASS", name
    ingestion = read(ART / "ingestion-validation.json")
    preflight = read(ART / "ingestion-preflight.json")
    ingest_receipt = read(ART / "ingestion-receipt.json")
    assert sha(ART / "source-plan.json") == ingestion["sourcePlanSha256"] == preflight["sourcePlanSha256"]
    assert ingestion["activePollCount"] == checkpoint["activePollCount"]
    assert ingestion["historyPollCount"] == checkpoint["historyPollCount"] + len(plan["polls"])
    assert ingestion["activePollCount"] == 8 and ingestion["historyPollCount"] == 132
    full_count = ingestion["fullStrict"]["polls"]
    default_count = ingestion["defaultWithoutChannel14"]["polls"]
    unknown_count = ingestion["fullStrict"]["unknownFieldworkExcluded"]
    assert full_count == preflight["expectedStrictEligible"]
    assert default_count == preflight["expectedStrictWithoutChannel14"]
    assert unknown_count == preflight["expectedUnverifiedFieldwork"]
    assert (full_count, ingestion['fullStrict']['series'], ingestion['fullStrict']['deltas']) == (52, 8, 44)
    assert (default_count, ingestion['defaultWithoutChannel14']['series'], ingestion['defaultWithoutChannel14']['deltas']) == (41, 7, 34)
    corr_dir = ROOT / f"artifacts/poll-correlation/{DAY}/reviewed"
    without_dir = ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/reviewed"
    assert read(corr_dir / "independent-audit.json")["status"] == "passed"
    assert read(without_dir / "validation.json")["status"] == "PASS"

    reports = sorted((ART / "browser-local").glob("*/report.json"))
    if (ART / 'browser-local/report.json').exists():
        reports.append(ART / 'browser-local/report.json')
    assert reports, "A fresh local browser report is required."
    local = reports[-1]
    browser = read(local)
    assert browser['status'] == 'passed' and browser['asOf'] == DAY and browser['phase'] == 'local'
    assert browser['browserAutomation'] == 'cua', 'UI verification uses the approved CUA surface, not headless Playwright.'
    assert browser['sourcePlanSha256'] == sha(ART / 'source-plan.json')
    assert browser['officialSourceSnapshotSha256'] == sha(ROOT / 'dashboard/src/data.json')
    assert browser['servedHTMLSha256'] == sha(ROOT / 'dashboard/dist/index.html')
    assert len(browser['checks']) >= 6, 'Record the actual fresh dashboard, poll/trend, threshold, appearance and no-Ask checks.'
    visual = local.parent / "visual-review.json"
    visual_receipt = read(visual)
    assert visual_receipt["status"] == "passed"
    assert visual_receipt["browserReportSha256"] == sha(local)
    assert visual_receipt['visualInspectionCompleted'] is True
    assert len(visual_receipt['reviewedScreenshots']) >= 3, 'Only actual fresh CUA screenshots count as visual evidence.'
    for rel, digest in visual_receipt["reviewedScreenshots"].items():
        assert Path(rel).name == rel and sha(local.parent / rel) == digest
    tests = (ART / "test-results-final.txt").read_text(encoding="utf-8-sig")
    assert re.search(r"fail\s+0(?:\r?\n|$)", tests)
    tests_passed = int(re.search(r"pass\s+(\d+)", tests).group(1))
    assert tests_passed >= 404, 'A zero-test or incomplete run is not a successful full test run.'
    render = read(ART / "social/render-checks.json")
    assert render["status"] == "PASS" and render["visualInspectionCompleted"] is True
    assert render["asOf"] == DAY
    for key in ["output", "prompt"]:
        assert Path(render[key]).name == render[key]
        assert sha(SOCIAL / render[key]) == render[key + "Sha256"]
    if render.get("cleanupPrompt"):
        assert Path(render["cleanupPrompt"]).name == render["cleanupPrompt"]
        assert sha(SOCIAL / render["cleanupPrompt"]) == render["cleanupPromptSha256"]
    social_comparison=render.get('modelComparisonFile','model-comparison.json')
    assert social_comparison in {'model-comparison.json','model-comparison-similarity.json'}
    assert sha(ART / social_comparison) == render["modelComparisonSha256"]
    social_review=read(ART/'social/independent-review.json')
    assert social_review['status']=='PASS' and social_review['visualInspectionCompleted'] is True
    assert social_review['renderReceiptSha256']==sha(ART/'social/render-checks.json')
    assert social_review['imageSha256']==render['outputSha256']
    social_files = sorted(p for p in SOCIAL.iterdir() if p.is_file())
    assert any(p.name == render["output"] and p.suffix.lower() == ".png" for p in social_files)
    assert any(p.name == "tweet.he.txt" for p in social_files)
    assert "https://victorchina-ops.github.io/israel-election-simulator/" in (SOCIAL / "tweet.he.txt").read_text(encoding="utf-8-sig")
    assert all(p.suffix.lower() in {".png", ".txt", ".json"} for p in social_files)

    snapshot = read(ROOT / "dashboard/src/data.json")
    assert snapshot["dataAsOf"] == DAY and snapshot["buildStatus"] == "complete"
    assert snapshot["features"]["chatGPT"] is False
    cfg = {r["key"]: r["value"] for r in snapshot["queries"]["model_configuration"]["rows"]}
    assert cfg["weightMode"] == "quality"
    assert all(cfg[k] is False for k in ["includeChannel14", "signalNoiseEnabled", "pollCorrelationEnabled"])
    assert cfg['partyBlocs']['winter'] == 'a' and cfg['partyBlocs']['hendel'] == 'other'
    comparison = read(ART / "model-comparison.json")
    assert comparison["status"] == "passed" and comparison["onlyControlDateDiffers"]
    assert {p["pollsterId"] for p in comparison["pollChanges"] if p["changed"]} == EXPECTED
    active=read(ROOT / "data/current-polls.json")["polls"]
    selected_ids={p['pollsterId'] for p in active if p['pollsterId']!='next_data'}
    selected_institutes = len(selected_ids)
    assert len(comparison["after"]["pollWeights"]) == selected_institutes
    assert {p['pollsterId'] for p in comparison['after']['pollWeights']} == selected_ids
    assert all(p["pollsterId"] != "next_data" for p in comparison["after"]["pollWeights"])
    similarity = read(ART / 'model-comparison-similarity.json')
    independent_review = read(ART / 'model-comparisons-independent-review.json')
    assert independent_review['sourcePlanSha256']==sha(ART/'source-plan.json')
    assert independent_review['snapshotSha256']==sha(ROOT/'dashboard/src/data.json')
    for name in ['model-comparison','model-comparison-similarity']:
        assert independent_review['reports'][name]['sha256']==sha(ART/(name+'.json'))
    assert similarity['status']=='passed' and similarity['after']['config']['pollCorrelationEnabled'] is True
    assert similarity['after']['config']['weightMode']=='quality' and similarity['after']['config']['includeChannel14'] is False
    assert similarity['after']['config']['signalNoiseEnabled'] is False
    inputs = {r["key"]: r["value"] for r in snapshot["queries"]["model_input"]["rows"]}
    assert len(inputs["current"]["polls"]) == ingestion["activePollCount"]
    assert len(inputs["history"]["polls"]) == ingestion["historyPollCount"]
    assert inputs["current"] == read(ROOT / "data/current-polls.json")
    assert inputs["history"] == read(ROOT / "data/poll-history.json")
    assert inputs["calibration"] == {**read(ROOT / "data/calibration.json"), "pollCorrelation": read(ROOT / "data/poll-correlation.json")}
    selected = read(ROOT / "data/strict-party-trends-without-channel14.json")
    full = read(ROOT / "data/strict-party-trends.json")
    assert selected["asOf"] == full["asOf"] == DAY
    assert selected["coverage"]["pollCount"] == default_count
    assert full["coverage"]["pollCount"] == full_count

    # Ingestion already copied the explicitly reviewed original graphic/factual
    # files. Reject unaccounted files before extending this new public prefix.
    source_prefix = REPO / PREFIX
    allowed_existing = dict(ingest_receipt["publicEvidenceFiles"])
    allowed_existing.update({"source-plan.json": sha(ART / "source-plan.json"), "ingestion-receipt.json": sha(ART / "ingestion-receipt.json")})
    for p in source_prefix.rglob("*"):
        if p.is_file():
            rel = p.relative_to(source_prefix).as_posix()
            assert rel in allowed_existing and sha(p) == allowed_existing[rel], ("Unreviewed public source file", rel)
            record(p)
    for spec in plan["polls"]:
        for evidence in spec["publicFiles"]:
            public = source_prefix / spec["folder"] / evidence["publicName"]
            assert sha(public) == sha(ROOT / evidence["sourcePath"]) == evidence["sha256"]

    # Explicit factual source summary only. Raw article/reader bodies stay local.
    public_source = ART / 'primary-source-public-summary.json'
    root_summary = read(public_source)
    assert root_summary['asOf'] == DAY
    assert root_summary['fullCopyrightedArticleBodiesExcluded'] is True
    if plan.get('sourceReview', {}).get('primarySourcePublicSummary'):
        assert sha(public_source) == plan['sourceReview']['primarySourcePublicSummary']['sha256']
    copy(public_source, 'primary-source-public-summary.json')
    if plan.get('sourceReview', {}).get('otherPublisherCoverage'):
        coverage_spec=plan['sourceReview']['otherPublisherCoverage']
        coverage_path=ROOT / coverage_spec['file']
        assert coverage_path.resolve().is_relative_to(ART.resolve())
        assert sha(coverage_path)==coverage_spec['sha256'] and read(coverage_path)['asOf']==DAY
        coverage_name=coverage_spec['publicName']
        assert Path(coverage_name).name==coverage_name and Path(coverage_name).suffix=='.json'
        copy(coverage_path,'source-discovery/'+coverage_name)
    discovery_relative = plan.get('sourceReview', {}).get('sourceDiscoveryLocalReceipt')
    discovery_receipt_path = ROOT / discovery_relative if discovery_relative else ART / 'source-israelpolls/scan-receipt.json'
    assert discovery_receipt_path.resolve().is_relative_to(ART.resolve())
    discovery = read(discovery_receipt_path)
    assert discovery['asOf'] == DAY
    if plan.get('sourceReview', {}).get('sourceDiscoveryLocalSha256'):
        assert sha(discovery_receipt_path) == plan['sourceReview']['sourceDiscoveryLocalSha256']
    assert 'Full authored articles' in discovery['publicScope'] and 'excluded' in discovery['publicScope']
    safe_names={item['fileName'] for item in discovery['safePublicFiles']}
    if discovery['status'] == 'PASS-SECONDARY-NUMERICAL-CROSSCHECK':
        # This frozen receipt covers secondary numerical cross-checks only.
        # Primary verification is separately bound by the reviewed source plan.
        assert DAY == '2026-10-20'
        assert sha(discovery_receipt_path) == '324acaa4ae06f56a31b1c3d7c52220d7d7851754d061e659e46c5b620d03f756'
        assert plan['sourceReview']['requiredIsraelPollsUrl'] == discovery['profileUrl'] == 'https://x.com/IsraelPolls?s=20'
        assert discovery['newIndependentObservationsVerifiedHere'] == 3
        assert set(discovery['newPublishers']) == {'N12', 'Channel13', 'Channel14'}
        assert len(discovery['newPublishers']) == 3
        assert discovery['historyPostDatesAreNotPollPublicationDates'] is True
        assert plan['sourceReview']['pollGraphicsAndHistoricalTablesChecked'] is True
        assert plan['sourceReview']['sameObservationRepostsNotCounted'] is True
        assert discovery['canonicalMutation'] is False
        assert root_summary['status'] == 'reviewed'
        assert set(root_summary['newObservationIds']) == {read(ROOT / p['candidatePath'])['id'] for p in plan['polls']}
        assert root_summary['fullCopyrightedArticleBodiesExcluded'] is True
        assert discovery['publicScope'] == 'Concise facts and provenance only. Full authored articles and reader bodies are excluded.'
        assert safe_names == {
            'n12-2026-10-19-reviewed-source-facts.json',
            'c13-2026-10-19-reviewed-source-facts.json',
            'c14-2026-10-19-reviewed-source-facts.json',
        }
        assert len(discovery['safePublicFiles']) == 3
        assert all(Path(name).suffix == '.json' for name in safe_names)
    else:
        assert discovery['status'] in {'PASS', 'verified-new-numerical-observations-primary-web-verification-delegated'}
        assert discovery.get('rawArticleBodiesSaved') is False or discovery.get('fullCopyrightedArticleBodiesExcluded') is True
    assert all('local-only' not in name.lower() for name in safe_names), 'Raw reader exports stay local.'
    for item in discovery['safePublicFiles']:
        name = item['fileName']
        assert Path(name).name == name and Path(name).suffix.lower() in {'.json','.txt','.png','.webp','.jpeg','.jpg'}
        source = discovery_receipt_path.parent / name
        assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
        copy(source, 'source-discovery/' + name)
    copy(discovery_receipt_path, 'source-discovery/source-public-freeze-receipt.json')

    compiled = (ROOT / "dashboard/dist/index.html").read_bytes()
    clean, count = re.subn(rb'<meta\s+name="data-app-local-thread"[^>]*>\s*', b"", compiled, flags=re.I)
    assert count == 1 and b"01a0952c-a40b-7b01-b019-621f0cee2656" not in clean
    assert sha(ROOT / "dashboard/src/data.json").encode() in clean
    for p in [REPO / "index.html", ROOT / "election-simulator.html", ROOT / "artifacts/github-pages-release/index.html"]:
        writes[p] = clean
    writes[ROOT / "dashboard-snapshot.json"] = (ROOT / "dashboard/src/data.json").read_bytes()
    for name in ["current-polls", "poll-history", "sources", "parties", "calibration", "survey-documents-2026-09-14",
                 "strict-party-trends", "strict-party-trends-without-channel14", "poll-correlation"]:
        copy(ROOT / "data" / (name + ".json"), name + ".json")
    for name in ["source-plan.json", "ingestion-preflight.json", "ingestion-receipt.json", "ingestion-validation.json",
                 "strict-validation.json", "model-comparison.json", "model-comparison-similarity.json",
                 "model-comparison-validation.json", "model-comparisons-independent-review.json", "test-results-final.txt"]:
        copy(ART / name, name)
    # Current numerical evidence and required fieldwork audits only. The root
    # strict folder also contains old HTML/text archives, which stay local.
    canonical_numeric = ["analysis.json", "by-pollster.csv", "independent-strict-numeric-audit.json", "party-analysis.json",
        "party-by-pollster.csv", "party-independent.json", "party-overall.csv", "party-summary-he.md", "party-validation.json", "summary-he.md",
        "n12-kan-c13-fieldwork.json", "c14-i24-fieldwork.json", "c16-tatika-fieldwork.json", "lazar-fieldwork.json", "new-unverified-fieldwork-2026-09-30.json"]
    for name in canonical_numeric:
        copy(ROOT / "artifacts/strict-post-close" / name, "trends/canonical/" + name)
    for label, folder in [("without-channel14", without_dir), ("poll-correlation", corr_dir)]:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                assert p.suffix.lower() not in {".html", ".htm"}, p
                copy(p, "trends/" + label + "/" + p.relative_to(folder).as_posix())
    reproducers = ["ingest-polls-2026-10-20.py", "validate-ingestion-2026-10-20.py", "validate-poll-update-2026-10-20.py",
        "build-trend-summaries-2026-10-20.py", "build-strict-party-trends.py", "derive-strict-trends-without-channel14.py",
        "build-poll-correlation.py", "audit-poll-correlation.py", "compare-poll-update.mjs", "validate-model-comparison-2026-10-20.mjs",
        "compare-poll-update-similarity-2026-10-20.mjs", "review-model-comparisons-2026-10-20.py",
        "freeze-before-polls-2026-10-20.py", "prepare-source-plan-2026-10-20.py", "review-social-poll-update-2026-10-20.py",
        "review-staged-poll-update-2026-10-20.py", "readback-poll-update-2026-10-20.py",
        "complete-poll-update-2026-10-20.py", "package-poll-update-2026-10-20.py",
        "exact_scalar_marginals_2026_10_20.py", "run-exact-trends-2026-10-20.py", "validate-exact-scalar-backend-2026-10-20.py"]
    for name in ['toy-equivalence.json','archive19-equivalence.json']:
        proof_path=ART/'scalar-review'/name
        proof=read(proof_path)
        assert proof['status']=='PASS' and proof['asOf']==DAY
        assert proof['backendSha256']==sha(ROOT/'scripts/exact_scalar_marginals_2026_10_20.py')
        copy(proof_path,'trends/canonical/scalar-review/'+name)
    for name,digest in {
        'independent-backend-review.json':'63991734402d20a1c19fada4389432b2bb64ef98bca4dac01853fc301a3a4cf7',
        'derive-change-review.json':'f2083a49cb4b1d2f4c32b48b2a5f4c8edaec425ffbc8a22064c451ec9c97ab6f',
        'derive-change-review-r1.json':'b36c354f100efee1a86f5caabb69cf0d86e3be3dff74cf3195086c22415f8f51',
        'derive-change-review-r2.json':'5634a1f19b3762c2f2826a4090a48415a6671076ff72e85c10a43f9e046a9161',
        'independent-derive-r2-review.json':'d3532317b4d9e6b01603ada6ea90df5557dae0b3cf71aff3247da976b26aa101',
    }.items():
        proof_path=ART/'scalar-review'/name
        assert sha(proof_path)==digest
        proof=read(proof_path)
        assert proof['asOf']==DAY
        if name=='derive-change-review-r2.json':
            assert proof['beforeSha256']==checkpoint['files'][proof['path']]
            assert proof['afterSha256']==sha(ROOT/proof['path'])=='552278e86c4c0070383cce0091b1bc75e73a75dc42f37e7c00348989d4e46847'
            for relative,expected_hash in proof['preservedFrozenFiles'].items():
                assert sha(ROOT/relative)==expected_hash
        elif name.startswith('derive-change-review'):
            assert proof['status']=='REVIEWED-SCOPED-UPGRADE'
        elif name=='independent-derive-r2-review.json':
            assert proof['status']=='PASS'
            assert proof['beforeSha256']==checkpoint['files']['scripts/derive-strict-trends-without-channel14.py']
            assert proof['afterSha256']==sha(ROOT/'scripts/derive-strict-trends-without-channel14.py')
            assert proof['permutationNullAndInclusiveTailToleranceUnchanged']
            assert proof['newDependenciesCopiedAndHashedBeforeDatedValidationFreeze']
        else:
            assert proof['status']=='PASS' and proof['backendSha256']==sha(ROOT/'scripts/exact_scalar_marginals_2026_10_20.py')
        copy(proof_path,'trends/canonical/scalar-review/'+name)
    for p in sorted((ART/'numeric-lineage').glob('*.json')):
        assert read(p)['status']=='PASS' and read(p)['asOf']==DAY
        copy(p,'trends/canonical/numeric-lineage/'+p.name)
    for name in reproducers:
        copy(ROOT / "scripts" / name, "reproduction/" + name)
    for name in ["analyze-strict-post-close-2026-09-28.py", "audit-strict-full-series-2026-09-28.py", "analyze-party-trends-strict-2026-09-28.py"]:
        copy(ROOT / "artifacts" / name, "reproduction/" + name)
    for rel, digest in checkpoint["reviewedExactHelpers"].items():
        assert sha(ROOT / rel) == digest
        if rel.startswith("artifacts/strict-post-close/"):
            copy(ROOT / rel, "reproduction/" + Path(rel).name)
    copy(local, "browser-local-report.json")
    copy(visual, "browser-local-visual-review.json")
    copy(ART / "social/render-checks.json", "social/render-checks.json")
    copy(ART / 'social/independent-review.json', 'social/independent-review.json')
    for p in social_files:
        dest = REPO / "updates" / RELEASE / p.name
        copies[dest] = p
        rel = dest.relative_to(REPO).as_posix()
        files[rel] = {"path": rel, "sha256": sha(p), "bytes": p.stat().st_size}

    after = comparison["after"]
    party = lambda pid: next(p for p in after["parties"] if p["id"] == pid)
    groups = {g["id"]: g["stats"]["mean"] for g in after["reportingGroups"]}
    assert abs(sum(groups.values()) - 120) < 1e-8
    preferred_after=similarity['after']
    preferred_groups={g['id']:g['stats']['mean'] for g in preferred_after['reportingGroups']}
    preferred_party=lambda pid:next(p for p in preferred_after['parties'] if p['id']==pid)
    assert abs(sum(preferred_groups.values())-120)<1e-8
    bloc = read(without_dir / "party-analysis.json")
    bloc_labels = {"coalition": "קואליציה", "opposition": "אופוזיציה ללא ערביות", "opposition_raam": "אופוזיציה עם רע״ם"}
    bloc_findings = [bloc_labels[r["group"]] for r in bloc["primary"]["blocOverall"] if r["qValue"] < .05]
    party_findings = [r["partyName"] for r in selected["rows"] if r["qValue"] < .05]
    sensitivity_findings = [r["partyName"] for r in selected["rows"] if r["wholeSeriesSignFlipQ"] < .05]
    heading = "## חדשות 12, חדשות 13, ערוץ 14 וואלה — עדכון 20.10.2026\n\n"
    date_label=lambda value: '.'.join(reversed(value.split('-'))) if value else 'לא פורסם'
    ids={'coalition':['likud','otzma','utj','shas','rz_zehut','winter'],'opposition':['yashar','beyachad','democrats','yisrael_beiteinu'],'arab':['joint','raam'],'unassigned':['hendel']}
    poll_paragraphs=[]
    for spec in plan['polls']:
        candidate=read(ROOT / spec['candidatePath'])
        old_current=next(p for p in read(ART/'before/data/current-polls.json')['polls'] if p['pollsterId']==candidate['pollsterId'])
        source_fieldwork=(date_label(candidate.get('fieldworkStart'))+'–'+date_label(candidate.get('fieldworkEnd'))) if candidate.get('fieldworkStart') and candidate.get('fieldworkEnd') else 'לא אומת'
        sample_label=str(candidate['sampleSize']) if candidate.get('sampleSize') is not None else 'לא פורסם'
        raw={key:sum(candidate['seats'].get(pid,0) for pid in members) for key,members in ids.items()}
        assert sum(raw.values())==120
        poll_paragraphs.append(f"סקר {candidate['publisher']} / {candidate['pollster']}: פרסום {date_label(candidate['date'])}; עבודת שדה {source_fieldwork}; מדגם {sample_label}. בחלוקה הקבועה באתר: קואליציה {raw['coalition']} כולל וינטר, אופוזיציה {raw['opposition']} ללא ערביות והנדל–זליכה, ערביות {raw['arab']} והנדל–זליכה {raw['unassigned']} בנפרד. הסקר הקודם מ־{date_label(old_current['date'])} נשמר בהיסטוריה. [מקור]({candidate['sourceUrl']}).")
    eligible_new=[read(ROOT / p['candidatePath'])['publisher'] for p in plan['polls'] if p['strictEligible']]
    unknown_new=[read(ROOT / p['candidatePath'])['publisher'] for p in plan['polls'] if not p['strictEligible']]
    assert {p['pollsterId'] for p in plan['polls'] if p['strictEligible']} == {'midgam_geva','next_data','lazar'}
    assert {p['pollsterId'] for p in plan['polls'] if not p['strictEligible']} == {'hamadad_consortium'}
    strict_note=(f"הסקרים החדשים של {', '.join(eligible_new)} זכאים למבחנים המחמירים בזכות איסוף מאומת לאחר סגירת הרשימות. "
        f"הסקר החדש של {', '.join(unknown_new)} נשמר בתחזית ובהיסטוריה אך מוחרג מהמבחן המחמיר, משום שמועד האיסוף לא אומת.")
    section=heading+'''נוספו ארבעה סקרים: חדשות 12, חדשות 13 וערוץ 14 פורסמו ב־19.10.2026, ווואלה פורסם ב־20.10.2026 על בסיס איסוף מ־19.10. בדיקת האתר והניתוחים בוצעה ב־20.10.2026. תאריך הבדיקה אינו תאריך פרסום או איסוף חדש. מועדי הפרסום, האיסוף והבדיקה נשמרים בנפרד, ונתון שלא פורסם נשאר חסר.

'''+ '\n\n'.join(poll_paragraphs)+f'''

אלה מנדטים שפורסמו בסקרים, ואינם הסתברויות מעבר במודל. אין להסיק מהפרש בין שני סקרים לבדו מגמה מובהקת או מעבר מצביעים. ערוץ 14 נשמר במאגר אך מוחרג משקלול ברירת המחדל; המתג מאפשר להכלילו. [אימות המקורות]({PREFIX}/source-plan.json) · [מגבלות הגישה]({PREFIX}/primary-source-public-summary.json).

ברירת המחדל נשארה דיוק היסטורי, השתתפות בסיס 2022, ללא ערוץ 14, אות־רעש כבוי ודמיון־סקרים כבוי. ממוצעי המודל: קואליציה {groups['a']:.2f}, אופוזיציה {groups['b']:.2f}, ערביות {groups['arab']:.2f}, הנדל–זליכה ושאר הרשימות {groups['other']:.2f}; סכומם 120. סיכויי מעבר במודל: וינטר {100 * party('winter')['passProbability']:.2f}%, הנדל–זליכה {100 * party('hendel')['passProbability']:.2f}%. אלה הסתברויות לפי הנחות המודל, ואינן אחוזי תמיכה שפורסמו. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).

התרחיש המועדף לדיווח הנוכחי מוסיף את מתג דמיון הסקרים לדיוק ההיסטורי, ללא ערוץ 14, ושומר וינטר בקואליציה והנדל–זליכה ללא שיוך. בו ממוצעי המנדטים הם קואליציה {preferred_groups['a']:.2f}, אופוזיציה {preferred_groups['b']:.2f}, ערביות {preferred_groups['arab']:.2f} ושאר הרשימות {preferred_groups['other']:.2f}; סיכויי המעבר הם וינטר {100*preferred_party('winter')['passProbability']:.2f}% והנדל–זליכה {100*preferred_party('hendel')['passProbability']:.2f}%. זה תרחיש נפרד מברירת המחדל: התיקון הניסיוני משתמש בדמיון בין תחזיות, אינו מודד חפיפת משיבים או תלות בטעויות ולא הוכח כמשפר כיול. [השוואת התרחיש עם דמיון מופעל]({PREFIX}/model-comparison-similarity.json) · [בדיקה חשבונית עצמאית של שני התרחישים]({PREFIX}/model-comparisons-independent-review.json).

המגמות חושבו מחדש באמצעות השינוי בתוך כל מכון, במשקלי הדיוק ההיסטורי הקיימים. נכללו {full_count} סקרים מאומתים בניתוח הכולל; ללא 14 — {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים ו־{selected['coverage']['deltaCount']} דלתות. {strict_note} {unknown_count} תצפיות מוחרגות עקב מועד איסוף לא מאומת; החרגת ערוץ 14 היא בחירת מקורות נפרדת. במבחן הפרמוטציות הראשי לאחר תיקון BH, הגושים המובהקים: {', '.join(bloc_findings) or 'אין'}; המפלגות המובהקות: {', '.join(party_findings) or 'אין'}. בבדיקת הרגישות לפי מכונים לאחר תיקון BH, המפלגות המובהקות: {', '.join(sensitivity_findings) or 'אין'}. כל הכרעה מוצגת בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [הניתוח ללא 14]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

נשמרו {ingestion['activePollCount']} מכונים פעילים ו־{ingestion['historyPollCount']} תצפיות היסטוריות. כל {len(checkpoint['frozenEvidenceHashes'])} קובצי הראיות מהפרסומים הקודמים נשמרו ללא שינוי. ראיות הפרסום החדשות מוגבלות לנתונים, גרפיקות ומראי מקום; גופי כתבות מלאים נשארים מחוץ לחבילה. [טיוטת ציוץ](updates/{RELEASE}/tweet.he.txt) · [איור לשיתוף](updates/{RELEASE}/{render['output']}) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json).

'''
    readme = REPO / "README.md"
    body = readme.read_text(encoding="utf-8-sig")
    assert heading not in body
    anchor = "## כאן, ערוץ 14 ו־i24 — עדכון 19.10.2026"
    assert anchor in body
    writes[readme] = body.replace(anchor, section + anchor, 1).encode("utf-8")
    attrs = REPO / ".gitattributes"
    body = attrs.read_text(encoding="utf-8-sig").rstrip() + "\n"
    for prefix in [PREFIX, "updates/" + RELEASE]:
        line = "/" + prefix + "/** -text"
        assert line not in body
        body += line + "\n"
    writes[attrs] = body.encode("utf-8")
    preserved()
    receipt = {"status": "PASS", "asOf": DAY, "runId": "reviewed", "newPollCount": len(plan["polls"]),
        "observationDateKinds": {read(ROOT/p['candidatePath'])['id']:read(ROOT/p['candidatePath']).get('dateKind') for p in plan['polls']},
        "observationPublicationDates": sorted({read(ROOT / p['candidatePath'])['date'] for p in plan['polls']}),
        "activePolls": ingestion["activePollCount"], "historyPolls": ingestion["historyPollCount"],
        "eligibleFull": full_count, "eligibleWithout14": default_count,
        "unknownFieldworkExcluded": unknown_count, "testsPassed": tests_passed,
        "authorContentFilesUnchanged": len(checkpoint["authorContentHashes"]),
        "protectedRuntimeFilesVerified": len(checkpoint["protectedRuntimeHashes"]),
        "frozenEvidenceFilesPreserved": len(checkpoint["frozenEvidenceHashes"]),
        "conditionalAndArtisticFilesPreserved": len(checkpoint["frozenConditionalAndArtisticHashes"]),
        "reviewedExactHelpersUnchanged": checkpoint["reviewedExactHelpers"],
        "snapshotSha256": sha(ROOT / "dashboard/src/data.json"), "publishedHtmlSha256": hashlib.sha256(clean).hexdigest(),
        "featuresChatGPT": False, "defaultWeightMode": "quality", "includeChannel14": False,
        "signalNoiseEnabled": False, "pollCorrelationEnabled": False, "socialDraftOnly": True,
        "winterDefaultBloc": "coalition", "hendelDefaultBloc": "unassigned",
        "preferredReportingSimilarityEnabled": True,
        "comparisonHashes": {name:sha(ART/(name+'.json')) for name in ['model-comparison','model-comparison-similarity']},
        "independentComparisonsReviewSha256":sha(ART/'model-comparisons-independent-review.json'),
        "fullArticleBodiesExcludedFromNewRelease": True, "compiledTo120DatasetExcludedFromNewRelease": True,
        "sourcePlanSha256": sha(ART / "source-plan.json"), "primarySourceSummarySha256": sha(public_source), "sourcePublicFreezeReceiptSha256": sha(discovery_receipt_path),
        "files": [files[key] for key in sorted(files)]}
    if args.check:
        print(json.dumps({"status": "PASS", "phase": "package-preflight-no-files-written", "files": len(files),
            "testsPassed": tests_passed, "publishedHtmlSha256": receipt["publishedHtmlSha256"]}))
        return
    # All dependencies, hashes, paths and README insertion are validated before
    # the first write. Existing dated files remain immutable.
    for dest, source in copies.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), ("Existing output changed during preflight", dest)
        else:
            shutil.copy2(source, dest)
    for dest, body in writes.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
    preserved()
    immutable_write(ART / "publication-receipt.json", receipt)
    immutable_write(REPO / PREFIX / "release.json", receipt)
    print(json.dumps({"status": "PASS", "files": len(files), "testsPassed": tests_passed,
        "publishedHtmlSha256": receipt["publishedHtmlSha256"]}))


if __name__ == "__main__":
    main()
