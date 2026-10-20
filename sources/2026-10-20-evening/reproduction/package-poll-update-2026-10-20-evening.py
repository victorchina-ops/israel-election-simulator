"""Package the three October20 evening observations in a distinct same-day release after independent checks.

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
RELEASE = "2026-10-20-evening"
ART = ROOT / "artifacts/poll-checks" / RELEASE
PREFIX = "sources/" + RELEASE
SOCIAL = ROOT / "outputs/social/2026-10-20-evening"
EXPECTED = {"maagar_mochot", "direct_polls", "next_data"}
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
    assert {p["pollsterId"] for p in plan["polls"]} == EXPECTED and len(plan["polls"]) == 3
    assert {read(ROOT / p['candidatePath'])['date'] for p in plan['polls']} == {'2026-10-20'}
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
    assert ingestion["activePollCount"] == 8 and ingestion["historyPollCount"] == 135
    full_count = ingestion["fullStrict"]["polls"]
    default_count = ingestion["defaultWithoutChannel14"]["polls"]
    unknown_count = ingestion["fullStrict"]["unknownFieldworkExcluded"]
    assert full_count == preflight["expectedStrictEligible"]
    assert default_count == preflight["expectedStrictWithoutChannel14"]
    assert unknown_count == preflight["expectedUnverifiedFieldwork"]
    assert (full_count, ingestion['fullStrict']['series'], ingestion['fullStrict']['deltas']) == (55, 8, 47)
    assert (default_count, ingestion['defaultWithoutChannel14']['series'], ingestion['defaultWithoutChannel14']['deltas']) == (43, 7, 36)
    corr_dir = ROOT / f"artifacts/poll-correlation/{DAY}/evening"
    without_dir = ROOT / f"artifacts/strict-post-close/without-channel14/{DAY}/evening"
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
    # The evening discovery receipt is a bounded profile scan and one i24
    # numerical lead. It is not a new primary-source or full-coverage claim.
    discovery_receipt_path=ROOT/plan['sourceReview']['sourceDiscoveryLocalReceipt']
    assert discovery_receipt_path.resolve().is_relative_to(ART.resolve())
    assert sha(discovery_receipt_path)==plan['sourceReview']['sourceDiscoveryLocalSha256']=='ca28238085c135cfa6599f1bc35b2232e61bb2da05e2ef65c4ff22b51830691c'
    discovery=read(discovery_receipt_path)
    assert discovery['status']=='PASS' and discovery['checkedAtUtc'].startswith(DAY+'T')
    assert discovery['profileUrl']==plan['sourceReview']['requiredIsraelPollsUrl']=='https://x.com/IsraelPolls?s=20'
    assert discovery['profileReadable'] is True
    assert discovery['canonicalMutated'] is discovery['publicMutated'] is False
    assert discovery['knownReposts'] and discovery['accessLimitations']
    assert plan['runId']=='evening' and plan['publicCopyrightScopeReviewed'] is True
    assert plan['sourceReview']['pollGraphicsAndHistoricalTablesChecked'] is True
    assert plan['sourceReview']['sameObservationRepostsNotCounted'] is True
    assert 'Full articles' in plan['publicEvidenceScope'] and 'remain local' in plan['publicEvidenceScope']
    assert root_summary['status']=='reviewed' and root_summary['fullCopyrightedArticleBodiesExcluded'] is True
    assert set(root_summary['newObservationIds'])=={read(ROOT/s['candidatePath'])['id'] for s in plan['polls']}
    secondary_facts=discovery_receipt_path.parent/'i24-secondary-facts.json'
    assert secondary_facts.suffix=='.json'
    assert sha(secondary_facts)==discovery['newOtherPollLead']['sha256']=='e8ad133fc9da8683d351e10169af09e4f38473c854f0e21bc9b6fc127c47760e'
    facts=read(secondary_facts)
    assert facts['status']=='SECONDARY-NUMERICAL-LEAD' and facts['pollsterId']=='direct_polls'
    assert facts['latestTableObservationDate']==DAY and facts['fieldworkVerified'] is False
    assert facts['canonicalMutation'] is False and sum(facts['seats'].values())==120
    assert any(s['pollsterId']=='direct_polls' and any(e['sha256']==sha(secondary_facts) for e in s['publicFiles']) for s in plan['polls'])
    lead_alias=discovery_receipt_path.parent/discovery['newOtherPollLead']['file']
    assert lead_alias.name=='israelpolls-i24-lead-185412Z.json'
    assert lead_alias.read_bytes()==secondary_facts.read_bytes()
    # Exact three JSON-only files; the alias resolves the immutable scan link.
    # No directory-wide article/reader copy is permitted.
    for source in [discovery_receipt_path,secondary_facts,lead_alias]:
        assert Path(source.name).name==source.name and source.suffix=='.json' and 'local-only' not in source.name
        copy(source,'source-discovery/'+source.name)

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
    reproducers = ["ingest-polls-2026-10-20-evening.py", "validate-ingestion-2026-10-20-evening.py", "validate-poll-update-2026-10-20-evening.py",
        "build-trend-summaries-2026-10-20-evening.py", "build-strict-party-trends.py", "derive-strict-trends-without-channel14.py",
        "build-poll-correlation.py", "audit-poll-correlation.py", "compare-poll-update.mjs", "validate-model-comparison-2026-10-20-evening.mjs",
        "compare-poll-update-similarity-2026-10-20-evening.mjs", "review-model-comparisons-2026-10-20-evening.py",
        "freeze-before-polls-2026-10-20-evening.py", "prepare-source-plan-2026-10-20-evening.py", "review-social-poll-update-2026-10-20-evening.py",
        "review-staged-poll-update-2026-10-20-evening.py", "readback-poll-update-2026-10-20-evening.py",
        "complete-poll-update-2026-10-20-evening.py", "package-poll-update-2026-10-20-evening.py",
        "exact_scalar_marginals_2026_10_20.py", "run-exact-trends-2026-10-20-evening.py", "validate-exact-scalar-backend-2026-10-20.py",
        "run-exact-trends-2026-10-20-evening-party-schema-r1.py",
        "run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py"]
    compatibility_path=ART/'numeric-compatibility/wrapper-compatibility.json'
    compatibility=read(compatibility_path)
    assert sha(compatibility_path)=='9796fbaf4bbd72224c512e3dc93e76a1194c2ba4ad313d8dc72c9afeed41b9f3'
    assert compatibility['status']=='PASS' and compatibility['asOf']==DAY and compatibility['runId']=='evening'
    assert compatibility['checkpointManifestSha256']==sha(ART/'before/manifest.json')
    assert compatibility['byteExactExceptOneArtPathReplacement'] and compatibility['normalizedAstIdentical'] and compatibility['transformAndInferenceUnchanged']
    assert sha(ROOT/compatibility['baselineWrapper'])==checkpoint['files'][compatibility['baselineWrapper']]==compatibility['baselineWrapperSha256']
    assert sha(ROOT/compatibility['eveningWrapper'])==compatibility['eveningWrapperSha256']
    assert sha(ROOT/compatibility['backendPath'])==checkpoint['files'][compatibility['backendPath']]==compatibility['backendSha256']
    independent_path=ART/'numeric-compatibility/independent-wrapper-review.json'
    independent_compatibility=read(independent_path)
    assert sha(independent_path)=='6c80b05865b65f9d8c5cf4ec3c4e6330d4184a1cb87eb012a939af8224ca36d5'
    assert independent_compatibility['status']=='PASS'
    assert independent_compatibility['originalCompatibilityReceiptSha256']==sha(compatibility_path)
    assert independent_compatibility['eveningWrapperSha256']==sha(ROOT/compatibility['eveningWrapper'])
    assert independent_compatibility['byteExactExceptOneArtifactDirectoryLiteral'] and independent_compatibility['normalizedAstIdentical']
    assert independent_compatibility['backendUnchangedSha256']==compatibility['backendSha256']
    assert independent_compatibility['allExistingNumericalProofHashesRechecked']==compatibility['existingProofHashes']
    assert sha(ROOT/'scripts/derive-strict-trends-without-channel14.py')==checkpoint['files']['scripts/derive-strict-trends-without-channel14.py']
    for relative,digest in compatibility['existingProofHashes'].items():
        proof_path=ROOT/relative
        assert proof_path.parent==ROOT/'artifacts/poll-checks/2026-10-20/scalar-review'
        assert sha(proof_path)==digest
        copy(proof_path,'trends/canonical/scalar-review/'+proof_path.name)
    for proof_path in [compatibility_path,independent_path]:
        copy(proof_path,'trends/canonical/numeric-compatibility/'+proof_path.name)
    copy(ART/'numeric-compatibility/independent-review-wrapper.py','reproduction/independent-review-wrapper.py')
    adapter_path=ROOT/'scripts/run-exact-trends-2026-10-20-evening-party-schema-r1.py'
    adapter_review_path=ART/'numeric-compatibility/party-schema-adapter-review.json'
    adapter_independent_path=ART/'numeric-compatibility/independent-party-schema-adapter-review.json'
    assert sha(adapter_path)=='d8e7164f20176ee864de8b9702cd6ac0b130fcca854032261a329805a98d0b74'
    assert sha(adapter_review_path)=='dc708e2df4a801f4299fb00244c1556b7d2addcc069ecc249026ba0651843877'
    assert sha(adapter_independent_path)=='1879863ed0cdec2b8ba19a283a4ddb5bc60b9e11d991c6f0bb431e351b2997c1'
    adapter_review=read(adapter_review_path)
    adapter_independent=read(adapter_independent_path)
    assert adapter_review['status']==adapter_independent['status']=='PASS'
    assert adapter_review['asOf']==DAY and adapter_review['runId']=='evening'
    assert adapter_review['baselineWrapperSha256']==adapter_independent['originalEveningWrapperSha256']==compatibility['eveningWrapperSha256']
    assert adapter_review['partySchemaAdapterSha256']==adapter_independent['partyAdapterSha256']==sha(adapter_path)
    assert adapter_independent['agentProofSha256']==sha(adapter_review_path)
    assert adapter_review['historySha256']==adapter_independent['historySha256']==sha(ROOT/'data/poll-history.json')
    assert adapter_review['analysisSha256']==adapter_independent['analysisSha256']==sha(ROOT/'artifacts/strict-post-close/analysis.json')
    assert adapter_review['catalogueSha256']==adapter_independent['catalogueSha256']==sha(ROOT/'data/parties.json')
    assert adapter_review['predeclaredBallotPartyCount']==17
    assert adapter_review['strictPollCount']==adapter_independent['strictCohortPolls']==full_count
    assert adapter_review['extraSeatKeys']=={'history_maagar_mochot_2026-10-20_current':{'other':0}}
    assert adapter_review['onlyPrimaryPartyPreconditionChanged'] and adapter_review['allOtherTransformedSourceBytesIdentical']
    assert adapter_review['otherStageTransformsUnchanged'] and adapter_review['adapterCliRestrictedToPrimaryParty']
    assert adapter_review['all17BallotArraysExactlyEqualBeforeAndAfterZeroAggregateOmission']
    assert adapter_review['timesWeightsNullStatisticsToleranceBHAndSignFlipsUnchanged']
    assert adapter_independent['normalizedAdapterAstEqualsOriginalAfterRemovingOnlyGuardAdditionAndPartyCliRestriction']
    assert adapter_independent['actualPartyTransformDiffOnlyPinnedUnionGuardReplacement']
    assert adapter_independent['otherThreeStageTransformsByteIdentical']
    assert adapter_independent['predeclared17PartyNumericalArraysExactlyEqualWithAndWithoutZeroAggregate']
    assert adapter_independent['frozenHelpersAndOriginalWrapperUnmodified']
    for proof_path in [adapter_review_path,adapter_independent_path]:
        copy(proof_path,'trends/canonical/numeric-compatibility/'+proof_path.name)
    for name in ['review-party-schema-adapter.py','independent-review-party-schema-adapter.py']:
        source=ART/'numeric-compatibility'/name
        if name=='review-party-schema-adapter.py':
            assert sha(source)==adapter_review['reviewScriptSha256']
        copy(source,'reproduction/'+name)
    independent_party_adapter_path=ROOT/'scripts/run-exact-trends-2026-10-20-evening-independent-party-schema-r1.py'
    independent_party_proof_path=ART/'numeric-compatibility/independent-party-schema-adapter-proof.json'
    assert sha(independent_party_adapter_path)=='d9d5328f57a6dc3f62090ba02868e2a2a9940ad2c4a431c3551b65c0e38ae9c1'
    assert sha(independent_party_proof_path)=='e32425b8402295fb241b12ee630345aa5b64f1e4d72de8b64321237fb92a36a5'
    independent_party_proof=read(independent_party_proof_path)
    assert independent_party_proof['status']=='PASS' and independent_party_proof['asOf']==DAY and independent_party_proof['runId']=='evening'
    assert independent_party_proof['independentPartyAdapterSha256']==sha(independent_party_adapter_path)
    assert independent_party_proof['originalEveningWrapperSha256']==compatibility['eveningWrapperSha256']
    assert independent_party_proof['historySha256']==sha(ROOT/'data/poll-history.json')
    assert independent_party_proof['analysisSha256']==sha(ROOT/'artifacts/strict-post-close/analysis.json')
    assert independent_party_proof['catalogueSha256']==sha(ROOT/'data/parties.json')
    assert independent_party_proof['predeclaredBallotPartyCount']==17
    assert independent_party_proof['strictCohortPolls']==full_count
    assert independent_party_proof['onlyIndependentPartyPerRowPreconditionChanged']
    assert independent_party_proof['allOtherTransformedSourceBytesIdentical'] and independent_party_proof['otherThreeStageTransformsUnchanged']
    assert independent_party_proof['adapterCliRestrictedToIndependentParty']
    assert independent_party_proof['all17BallotArraysExactlyEqualWithAndWithoutZeroAggregate']
    assert independent_party_proof['lstsqDPExactTailsToleranceBHAndSignFlipsUnchanged']
    assert independent_party_proof['rawDataAndFrozenHelperBytesUnchanged']
    copy(independent_party_proof_path,'trends/canonical/numeric-compatibility/'+independent_party_proof_path.name)
    independent_party_reviewer=ART/'numeric-compatibility/review-independent-party-schema-adapter.py'
    assert sha(independent_party_reviewer)==independent_party_proof['reviewScriptSha256']
    copy(independent_party_reviewer,'reproduction/'+independent_party_reviewer.name)
    second_judge_path=ART/'numeric-compatibility/secondary-party-schema-independent-review.json'
    second_judge_reviewer=ART/'numeric-compatibility/independent-review-secondary-party-schema.py'
    assert sha(second_judge_path)=='ec3d4ad40b6d52b298556abb16e9d8dbb74203a40bbd3ee20b0863c2e2d0571f'
    assert sha(second_judge_reviewer)=='6e80f765718456e4149117d996bd2b0491be875036c0bff306223e0d1fe0977f'
    second_judge=read(second_judge_path)
    assert second_judge['status']=='PASS'
    assert second_judge['agentProofSha256']==sha(independent_party_proof_path)
    assert second_judge['independentPartyAdapterSha256']==sha(independent_party_adapter_path)
    assert second_judge['primaryPartyAdapterPreservedSha256']==sha(adapter_path)
    assert second_judge['originalWrapperPreservedSha256']==compatibility['eveningWrapperSha256']
    assert second_judge['onlyPerRowSubsetGuardAndIndependentStageCliRestrictionChanged']
    assert second_judge['allNumericalTransformBytesIdenticalOutsideGuard']
    assert second_judge['otherThreeStageTransformsUnchanged']
    assert second_judge['actual55x17ArraysEqualWithAndWithoutZeroAggregate']
    assert second_judge['noAdditionalTestFamilyOrMethodChange'] and second_judge['frozenFourAnalyzerHashesUnchanged']
    for stage,digest in second_judge['threePassedLineageHashesPreserved'].items():
        assert stage in {'bloc','independent-bloc','party'}
        assert sha(ART/'numeric-lineage'/(stage+'-enumeration-lineage.json'))==digest
    copy(second_judge_path,'trends/canonical/numeric-compatibility/'+second_judge_path.name)
    copy(second_judge_reviewer,'reproduction/'+second_judge_reviewer.name)
    boundary_path=ART/'numeric-compatibility/float-boundary/focused-common-threshold-review.json'
    boundary_reviewer=ART/'numeric-compatibility/float-boundary/review-common-threshold.py'
    observed_encoding_path=ART/'numeric-compatibility/bloc-tail-observed-threshold-difference.json'
    assert sha(boundary_path)=='a0ece1bb9589de317a739a043fe649dcfe13b65b2c7e6dfc94c4742027d9b6ba'
    assert sha(boundary_reviewer)=='42d33424d6781aa2aba0a9b486a6899427d80c55c5ea81eba4238702772fad18'
    assert sha(observed_encoding_path)=='7846ff9fdec229a611353ecf7484906b5db0b83596958500dd7435cef4326714'
    boundary=read(boundary_path)
    encoding=read(observed_encoding_path)
    assert boundary['status']=='PASS' and boundary['outcome']==encoding['group']=='opposition_raam'
    assert encoding['asOf']==DAY and encoding['runId']=='evening'
    for relative,digest in boundary['inputSha256'].items():
        assert sha(ROOT/relative)==digest
    assert boundary['commonThresholdExactIntegerMatch'] and boundary['independentOwnThresholdIntegerMatch']
    assert boundary['allPrimaryUniqueAndIndependentDpScalarBlocksByteIdentical']
    assert boundary['nullMassRestoredByExactLabeledMultiplicities']
    assert boundary['numericalOutputsOrFrozenHelpersModified'] is False and encoding['noCounterOrOutputChanges'] is True
    assert boundary['toleranceUnchanged']==encoding['registeredAbsoluteTolerance']==1e-12
    assert boundary['independentCounterAtPrimaryObservedCountExact']==boundary['archivedPrimaryExtremeCountExact']==encoding['primaryExtremeCountExact']
    assert boundary['independentCounterAtOwnObservedCountExact']==boundary['archivedIndependentExtremeCountExact']==encoding['independentExtremeCountExact']
    assert boundary['totalPermutationsExact']==encoding['totalExact']
    assert int(boundary['boundaryMultiplicityDifferenceExact'])==int(encoding['countDifferenceExact'])
    assert abs(boundary['primaryP']-boundary['independentP'])<1e-12
    assert len(boundary['seriesBlocks'])==ingestion['fullStrict']['series']
    copy(boundary_path,'trends/canonical/numeric-compatibility/float-boundary/'+boundary_path.name)
    copy(observed_encoding_path,'trends/canonical/numeric-compatibility/'+observed_encoding_path.name)
    copy(boundary_reviewer,'reproduction/'+boundary_reviewer.name)
    test_compatibility_dir=ART/'test-boundary-compatibility'
    test_review_path=test_compatibility_dir/'review-receipt.json'
    test_independent_path=test_compatibility_dir/'independent-review.json'
    assert sha(test_review_path)=='91fdf663a227b28c0463d37827ca4e65dc2201956d3b99c89cf35e04dd1aa8da'
    assert sha(test_independent_path)=='954e9e01c9c3cef4adf3d238c0dc81a4c595c41a72b6cc9d9e6179134ea933bd'
    test_review=read(test_review_path)
    test_independent=read(test_independent_path)
    assert test_review['status']=='READY-FOR-ROOT-FULL-TEST-RERUN'
    assert test_independent['status']=='PASS-STATIC-REVIEW'
    assert test_review['asOf']==DAY and test_review['runId']=='evening'
    assert test_review['strictValidationSha256']==sha(ART/'strict-validation.json')
    assert test_review['focusedCommonThresholdReview']['sha256']==test_independent['exactCounterDiagnosticProofSha256']==sha(boundary_path)
    assert test_review['independentReview']['sha256']==sha(test_independent_path)
    assert test_review['currentDefaultVerdictRepair']['validationSha256']==sha(without_dir/'validation.json')
    expected_tests={'tests/strict-party-publication.test.mjs','tests/channel14-strict-trends.test.mjs'}
    assert {s['path'] for s in test_review['files']}==expected_tests and len(test_review['files'])==2
    assert {(s['path'],s['beforeSha256'],s['afterSha256']) for s in test_review['files']}=={(s['path'],s['beforeSha256'],s['afterSha256']) for s in test_independent['files']}
    for relative,digest in test_review['strictNumericInputHashesUnchanged'].items():
        assert sha(ROOT/relative)==digest
    for spec in test_review['files']:
        current_test=ROOT/spec['path']
        assert sha(current_test)==spec['afterSha256']
        copy(current_test,'reproduction/validation/tests/'+current_test.name)
        for key,hash_key in [('beforeFile','beforeSha256'),('diffFile','diffSha256')]:
            source=ROOT/spec[key]
            assert source.resolve().is_relative_to(test_compatibility_dir.resolve())
            assert sha(source)==spec[hash_key]
            copy(source,'reproduction/validation/test-boundary-compatibility/'+source.relative_to(test_compatibility_dir).as_posix())
    failed_test_log=test_review['preservedInitialFailedLog']
    assert sha(ROOT/failed_test_log['file'])==failed_test_log['sha256']
    for source in [test_review_path,test_independent_path]:
        copy(source,'reproduction/validation/test-boundary-compatibility/'+source.name)
    stage_wrapper_hashes={'bloc':compatibility['eveningWrapperSha256'],
        'independent-bloc':compatibility['eveningWrapperSha256'],
        'party':sha(adapter_path),'independent-party':sha(independent_party_adapter_path)}
    lineage_files=sorted((ART/'numeric-lineage').glob('*.json'))
    assert {p.name for p in lineage_files}=={s+'-enumeration-lineage.json' for s in ['bloc','party','independent-bloc','independent-party']}
    for p in lineage_files:
        lineage=read(p)
        assert lineage['status']=='PASS' and lineage['asOf']==DAY
        assert p.name==lineage['stage']+'-enumeration-lineage.json'
        expected_wrapper=stage_wrapper_hashes[lineage['stage']]
        assert lineage['wrapperSha256']==expected_wrapper
        assert lineage['scalarBackendSha256']==compatibility['backendSha256']
        assert lineage['inputHistorySha256']==sha(ROOT/'data/poll-history.json')
        assert lineage['nullUnchanged'] and lineage['outcomeMarginalExactness'] and lineage['cohortAndWeightsUnchanged']
        assert lineage['monteCarlo'] is False
        pinned_analyzer=independent_compatibility['allFourPinnedHelpersUnchanged'][lineage['stage']]
        assert lineage['frozenAnalyzer']==pinned_analyzer['path']
        assert sha(ROOT/lineage['frozenAnalyzer'])==pinned_analyzer['sha256']==lineage['frozenAnalyzerSha256']
        assert Path(lineage['outputFile']).name==lineage['outputFile']
        assert sha(ROOT/'artifacts/strict-post-close'/lineage['outputFile'])==lineage['outputSha256']
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
    bloc_sensitivity_findings = [bloc_labels[r["group"]] for r in bloc["primary"]["blocOverall"] if r["wholeInstituteSignFlipQ"] < .05]
    party_findings = [r["partyName"] for r in selected["rows"] if r["qValue"] < .05]
    sensitivity_findings = [r["partyName"] for r in selected["rows"] if r["wholeSeriesSignFlipQ"] < .05]
    heading = "## ערוץ 16, i24 וערוץ 14 — עדכון ערב 20.10.2026\n\n"
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
    assert {p['pollsterId'] for p in plan['polls'] if p['strictEligible']} == EXPECTED
    assert not unknown_new
    strict_note=f"כל שלושת הסקרים החדשים של {', '.join(eligible_new)} זכאים למבחנים המחמירים בזכות איסוף מאומת לאחר סגירת הרשימות; ערוץ 14 מוחרג בנפרד לפי בחירת המקורות."
    section=heading+'''נוספו שלושה סקרים מהערב: ערוץ 16, i24 וערוץ 14, כולם פורסמו ב־20.10.2026. איסוף ערוץ 16 נערך ב־19–20.10; איסוף i24 וערוץ 14 נערך ב־20.10. זהו עדכון ערב נפרד לעדכון הבוקר מאותו תאריך; המקורות, החישובים והראיות של שני העדכונים נשמרים בנפרד. תאריך הבדיקה אינו תאריך פרסום או איסוף חדש, ונתון שלא פורסם נשאר חסר.

'''+ '\n\n'.join(poll_paragraphs)+f'''

אלה מנדטים שפורסמו בסקרים, ואינם הסתברויות מעבר במודל. אין להסיק מהפרש בין שני סקרים לבדו מגמה מובהקת או מעבר מצביעים. ערוץ 14 נשמר במאגר אך מוחרג משקלול ברירת המחדל; המתג מאפשר להכלילו. [אימות המקורות]({PREFIX}/source-plan.json) · [מגבלות הגישה]({PREFIX}/primary-source-public-summary.json).

ברירת המחדל נשארה דיוק היסטורי, השתתפות בסיס 2022, ללא ערוץ 14, אות־רעש כבוי ודמיון־סקרים כבוי. ממוצעי המודל: קואליציה {groups['a']:.2f}, אופוזיציה {groups['b']:.2f}, ערביות {groups['arab']:.2f}, הנדל–זליכה ושאר הרשימות {groups['other']:.2f}; סכומם 120. סיכויי מעבר במודל: וינטר {100 * party('winter')['passProbability']:.2f}%, הנדל–זליכה {100 * party('hendel')['passProbability']:.2f}%. אלה הסתברויות לפי הנחות המודל, ואינן אחוזי תמיכה שפורסמו. [השוואה לפני ואחרי]({PREFIX}/model-comparison.json).

התרחיש המועדף לדיווח הנוכחי מוסיף את מתג דמיון הסקרים לדיוק ההיסטורי, ללא ערוץ 14, ושומר וינטר בקואליציה והנדל–זליכה ללא שיוך. בו ממוצעי המנדטים הם קואליציה {preferred_groups['a']:.2f}, אופוזיציה {preferred_groups['b']:.2f}, ערביות {preferred_groups['arab']:.2f} ושאר הרשימות {preferred_groups['other']:.2f}; סיכויי המעבר הם וינטר {100*preferred_party('winter')['passProbability']:.2f}% והנדל–זליכה {100*preferred_party('hendel')['passProbability']:.2f}%. זה תרחיש נפרד מברירת המחדל: התיקון הניסיוני משתמש בדמיון בין תחזיות, אינו מודד חפיפת משיבים או תלות בטעויות ולא הוכח כמשפר כיול. [השוואת התרחיש עם דמיון מופעל]({PREFIX}/model-comparison-similarity.json) · [בדיקה חשבונית עצמאית של שני התרחישים]({PREFIX}/model-comparisons-independent-review.json).

המגמות חושבו מחדש באמצעות השינוי בתוך כל מכון, במשקלי הדיוק ההיסטורי הקיימים. נכללו {full_count} סקרים מאומתים בניתוח הכולל; ללא 14 — {selected['coverage']['pollCount']} סקרים, {selected['coverage']['seriesCount']} מכונים ו־{selected['coverage']['deltaCount']} דלתות. {strict_note} {unknown_count} תצפיות מוחרגות עקב מועד איסוף לא מאומת; החרגת ערוץ 14 היא בחירת מקורות נפרדת. במבחן הפרמוטציות הראשי לאחר תיקון BH, הגושים המובהקים: {', '.join(bloc_findings) or 'אין'}; המפלגות המובהקות: {', '.join(party_findings) or 'אין'}. בבדיקת הרגישות לפי מכונים לאחר תיקון BH, הגושים המובהקים: {', '.join(bloc_sensitivity_findings) or 'אין'}; המפלגות המובהקות: {', '.join(sensitivity_findings) or 'אין'}. כל הכרעה מוצגת בנפרד; אי־מובהקות אינה הוכחת אקראיות או היעדר שינוי. [הניתוח ללא 14]({PREFIX}/strict-party-trends-without-channel14.json) · [אימות המבחנים]({PREFIX}/strict-validation.json).

נשמרו {ingestion['activePollCount']} מכונים פעילים ו־{ingestion['historyPollCount']} תצפיות היסטוריות. כל {len(checkpoint['frozenEvidenceHashes'])} קובצי הראיות מהפרסומים הקודמים נשמרו ללא שינוי. ראיות הפרסום החדשות מוגבלות לנתונים, גרפיקות ומראי מקום; גופי כתבות מלאים נשארים מחוץ לחבילה. [טיוטת ציוץ](updates/{RELEASE}/tweet.he.txt) · [איור לשיתוף](updates/{RELEASE}/{render['output']}) · [בדיקות דפדפן]({PREFIX}/browser-local-report.json).

'''
    paragraphs=[p.strip() for p in section.split('\n\n') if p.strip()]
    assert len(paragraphs)==len(set(paragraphs)), 'New evening README section must not repeat paragraphs.'
    readme = REPO / "README.md"
    body = readme.read_text(encoding="utf-8-sig")
    assert heading not in body
    anchor = "## חדשות 12, חדשות 13, ערוץ 14 וואלה — עדכון 20.10.2026"
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
    receipt = {"status": "PASS", "asOf": DAY, "runId": "evening", "newPollCount": len(plan["polls"]),
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
        "sourcePlanSha256": sha(ART / "source-plan.json"), "primarySourceSummarySha256": sha(public_source), "sourceDiscoveryReceiptSha256": sha(discovery_receipt_path),
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
