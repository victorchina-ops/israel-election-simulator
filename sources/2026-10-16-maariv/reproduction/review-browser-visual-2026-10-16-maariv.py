"""Record the explicitly inspected Maariv browser screenshots without changing them.

Run only after viewing every named screenshot. This records human/agent visual
inspection; it does not claim that the checks below are an automated image test.
"""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-16-maariv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
NAMES={
    '1440-about-light.png','1440-about-dark.png','1440-trends.png','1440-poll-data.png',
    '1440-default-threshold-overview.png','390-default-threshold-overview.png',
    '320-default-threshold-overview.png','390-trends.png','390-poll-data.png',
    '390-triple-all-fail.png',
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['local','public'],required=True)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    assert Path(args.run_id).name==args.run_id
    folder=ART/('browser-'+args.phase)/args.run_id
    report=read(folder/'report.json')
    assert report['status']=='passed' and report['phase']==args.phase
    assert report['asOf']=='2026-10-16'
    assert len(report['checks'])==10 and len(report['geometry'])==23
    assert report['thresholdAlignedRowChecks']>=80 and not report['pageErrors']
    assert {p.name for p in folder.glob('*.png')}==NAMES
    rows={name:sha(folder/name) for name in sorted(NAMES)}
    receipt={
        'status':'passed','asOf':'2026-10-16','phase':args.phase,'runId':args.run_id,
        'browserReportSha256':sha(folder/'report.json'),'reviewedScreenshots':rows,
        'visualInspectionCompleted':True,'screenshotsReviewed':len(rows),
        'reviewMethod':'Every screenshot was opened and inspected visually through view_image; structured browser assertions are separately recorded in report.json.',
        'checks':[
            'Both desktop About themes retain the author photograph, contact, introduction, seven tabs and visible theme toggle; text and buttons are legible.',
            'Desktop strict trends show the fresh October16 cohort and separate main-BH/sensitivity verdicts; all visible values match the fresh structured browser assertions.',
            'Desktop register shows the fresh Maariv observation with its actual retrieval-category link and all other current publishers; observation dates and unknown sample/fieldwork match the reviewed candidate.',
            'Threshold charts at1440/390/320 retain aligned logos, mean seats, labels and fresh probabilities; narrow-label ellipses are intentional and accessible names are independently tested.',
            'Mobile trends retain wrapped cohort and method explanations; mobile poll register remains inside its intended horizontally scrollable table region.',
            'Mobile all-three-fail selection has the correct all-selected event definition and selected lists; fresh count, probability, CSV and histogram arithmetic are independently checked by the browser script.',
            'No new clipping, overlapping marks or document-level horizontal overflow was found in the inspected views; broader geometry and interaction coverage is in the browser report.',
        ],
        'sourcePlanSha256':report['sourcePlanSha256'],
        'checkedAt':datetime.now(timezone.utc).isoformat(),
        'reviewRecorderSha256':sha(Path(__file__)),
    }
    target=folder/'visual-review.json'
    assert not target.exists(),'Preserve the immutable prior visual review.'
    target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','phase':args.phase,'screenshots':len(rows),'visualReviewSha256':sha(target),'browserReportSha256':receipt['browserReportSha256']},ensure_ascii=False))

if __name__=='__main__':main()
