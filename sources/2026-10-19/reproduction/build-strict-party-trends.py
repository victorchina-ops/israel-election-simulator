"""Publish the latest reviewed party-trend snapshot without recomputing it.

The snapshot intentionally remains fixed when the interactive model, selected
pollsters, or future poll database change. A new audit must be supplied before
its date or cohort can advance.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "artifacts/strict-post-close/party-analysis.json"
OUTPUT = ROOT / "data/strict-party-trends.json"
LABELS = {
    "midgam_geva": "חדשות 12 / מדגם",
    "hamadad_consortium": "חדשות 13 / המדד",
    "kantar": "כאן והיום / קנטאר",
    "lazar": "מעריב ווואלה / לזר",
    "next_data": "חדשות 14 / NEXT DATA",
    "direct_polls": "i24 / דיירקט פולס",
    "tatika": "זמן ישראל / טאטיקה",
    "maagar_mochot": "ערוץ 16 / מאגר מוחות",
}


def public_urls(record):
    candidates = [record.get("sourceUrl")]
    candidates.extend(item.get("url") for item in record.get("evidence", []))
    return list(dict.fromkeys(url for url in candidates if isinstance(url, str)
                             and urlparse(url).scheme in {"http", "https"}
                             and urlparse(url).netloc))


def build():
    audit_bytes = AUDIT.read_bytes()
    audit = json.loads(audit_bytes.decode("utf-8-sig"))
    primary = audit["primary"]
    eligible = [row for row in audit["cohort"] if row["eligibleStrict"]]
    assert len(eligible) == primary["nPolls"]
    assert len(primary["overall"]) == len(audit["testedPartyIds"])
    assert all(row["fieldworkStart"] >= audit["closure"]["firstEligibleFieldworkDate"]
               for row in eligible)
    assert abs(sum(audit["normalizedHistoricalWeights"].values()) - 1) < 1e-12

    rows = []
    for party in primary["overall"]:
        details = []
        for series in primary["byPollster"]:
            entry = next(row for row in series["parties"] if row["partyId"] == party["partyId"])
            details.append({**entry, "label": LABELS[series["pollsterId"]],
                            "pollIds": series["pollIds"],
                            "dates": series["publicationDates"],
                            "timeDaysFromFirst": series["timeDaysFromFirst"]})
        rows.append({**party, "byPollster": details})

    cohort = []
    for entry in audit["cohort"]:
        included = entry["eligibleStrict"]
        cohort.append({
            **{key: entry.get(key) for key in ["pollId", "pollsterId", "publicationDate",
                                               "fieldworkStart", "fieldworkEnd"]},
            "label": LABELS[entry["pollsterId"]], "eligibleStrict": included,
            "sourceUrls": public_urls(entry),
            "reason": ("מועדי האיסוף אומתו במקור; כל האיסוף החל אחרי סגירת הרשימות."
                       if included else "מועדי האיסוף לא אומתו; תאריך הפרסום לבדו אינו מספיק להכללה."),
        })

    snapshot = {
        "schemaVersion": 1, "asOf": audit["asOf"], "weightMode": "quality",
        "coverage": {
            "pollCount": primary["nPolls"], "seriesCount": primary["nSeries"],
            "deltaCount": primary["nDeltas"], "partyCount": len(rows),
            "from": min(row["fieldworkStart"] for row in eligible),
            "to": max(row["fieldworkEnd"] for row in eligible),
            "closureDate": audit["closure"]["date"],
            "excludedPollCount": len(cohort) - len(eligible),
        },
        "weights": [{"pollsterId": series["pollsterId"], "label": LABELS[series["pollsterId"]],
                     "weight": series["weight"], "nPolls": len(series["pollIds"])}
                    for series in primary["byPollster"]],
        "rows": rows, "cohort": cohort,
        "sources": [
            {"title": "ועדת הבחירות — לוח הזמנים לבחירות", "url": audit["closure"]["sources"][0]},
            {"title": "המכון הישראלי לדמוקרטיה — מועד סגירת הרשימות", "url": audit["closure"]["sources"][1]},
            {"title": "מבחני פרמוטציה — תיעוד SciPy", "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html"},
        ],
        "methodology": {
            "kind": "exact_within_series_time_permutation", "twoSided": True,
            "timeAxis": primary["timeAxis"],
            "statistic": "absolute historical-quality-weighted mean of all-observation party seat slopes per week",
            "permutations": primary["exactCounting"]["nPermutations"],
            "permutationsExact": primary["exactCounting"]["nPermutationsExact"],
            "signPatterns": primary["wholeSeriesSignPatterns"],
            "multipleTesting": "Benjamini-Hochberg", "partyTests": len(rows),
            "individualTests": len(rows) * primary["nSeries"],
            "fixedSnapshot": True, "usesCurrentControls": False,
            "weightsRenormalizedAcrossEligibleSeries": True,
            "netDeltaDefinition": "weighted mean of each series' last-minus-first published seats; not the tested statistic",
            "adjacentDeltaDependence": "OLS over all observations, equivalent to GLS on adjacent deltas with D D-transpose covariance",
            "nullAssumptions": "time exchangeability within each series and independent permutation blocks",
            "zeroSeatConvention": "constant published-seat series get p=1; vote shares below the threshold may still change",
        },
        "provenance": {
            "analysisSha256": hashlib.sha256(audit_bytes).hexdigest(),
            "historySha256": audit["historySha256"], "partiesSha256": audit["partiesSha256"],
            "script": "scripts/build-strict-party-trends.py",
            "analysisScript": "artifacts/analyze-party-trends-strict-2026-09-28.py",
        },
    }
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published fixed snapshot: {primary['nPolls']} polls, {primary['nSeries']} series, {len(rows)} parties -> {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
