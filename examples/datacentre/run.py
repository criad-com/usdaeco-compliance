#!/usr/bin/env python3
"""Compose the pinned iris variant, check clauses and publish USD figures."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(os.environ.get('TOOLCHAIN_DIR',ROOT.parent/'usdaeco-toolchain'))/'tools'))
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT))
from usdaeco_check.example import run_example
from usdaeco_check.validation import run
from usdaeco_compliance.evaluator import write_results, stale_paths
from usdaeco_compliance.model import add_fallbacks
from usdaeco_compliance.presentation import draw, present_facility


def hook(stage,out):
    add_fallbacks(stage)
    result=write_results(stage,out/'compliance.usda')
    (out/'report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    errors=run(stage,['UsdAecoComplianceValidators'])
    expected_failures=sum(f['kind']=='misplacedDevice' for f in result['findings'])
    if len(errors)!=expected_failures or any(e.GetName()!='MisplacedDevice' for e in errors):
        raise ValueError('Unexpected validation findings: '+ '; '.join(e.GetName()+': '+e.GetMessage() for e in errors))
    source=Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/iris/dc.manifest.json'
    source_counts=json.loads(source.read_text())['counts']
    counts={s:sum(r['status']==s for r in result['results']) for s in ('pass','fail','warn','notApplicable')}
    findings=[{'kind':'summary','source_counts':source_counts,'readers':len(result['results']),
               **counts,'clause_failures':expected_failures,'illustrative':True}]+result['findings']
    draw(stage,result,out/'diagrams.usda')
    present_facility(stage,result,out/'presentation.usda')
    if stale_paths(stage):raise ValueError('Presentation unexpectedly changed the measurement inputs.')
    return findings


def main():
    os.environ["HDEMBREE_CAMERA_LIGHT_INTENSITY"]="100"
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if not os.environ.get('AECO_DATACENTRE_ROOT'):
        parser.error('AECO_DATACENTRE_ROOT must name the pinned data-centre checkout.')
    run_example(Path(__file__).parent,hook,variant='iris',publish=args.publish,keywords=[])


if __name__=='__main__':main()
