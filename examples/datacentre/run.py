#!/usr/bin/env python3
"""Compose the pinned iris variant, check clauses and publish USD figures."""
import argparse
import hashlib
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
from usdaeco_compliance.evaluator import write_results, stale_paths, fingerprint
from usdaeco_compliance.model import add_fallbacks
from usdaeco_compliance.presentation import draw, present_facility


def check_migration(previous, current):
    """Refuse a fingerprint migration if any committed result opinion changes."""
    from pxr import Sdf
    old, new = [Sdf.Layer.OpenAsAnonymous(str(p)) for p in (previous, current)]
    digests = []
    for layer in (old, new):
        metadata = dict(layer.customLayerData)
        if metadata.get('aecoComplianceRole') != 'result':
            raise ValueError('Fingerprint migration requires a compliance result layer.')
        digests.append(metadata.pop('inputFingerprint'))
        metadata.pop('evaluatorVersion')
        layer.customLayerData = metadata
    if old.ExportToString() != new.ExportToString():
        raise ValueError('Fingerprint migration would change result opinions; review and recheck the inputs.')
    print('== stage: fingerprint migration (all result opinions unchanged)', flush=True)
    print(json.dumps({'previous': digests[0], 'current': digests[1]}, sort_keys=True), flush=True)


def committed_stage():
    """Compose archived opinions over the exact pinned source without writes."""
    from pxr import Sdf, Usd
    example = Path(__file__).parent
    source = Path(os.environ['AECO_DATACENTRE_ROOT'])
    pin = json.loads((ROOT/'dependencies.json').read_text())['repos']['datacentre']['ref']
    if 'v' + json.loads((source/'library.json').read_text())['version'] != pin:
        raise ValueError('Committed verification requires the pinned data-centre release.')
    published = json.loads((example/'manifest.json').read_text())
    source_dir = source/'dist/iris'
    for record in [*published['source']['layers'],
                   {'path': 'dc.manifest.json', 'sha256': published['source']['manifest_sha256']}]:
        if hashlib.sha256((source_dir/record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Committed verification source hash mismatch: ' + record['path'])
    base = Usd.Stage.Open(str(source_dir/'dc.usda'))
    root = Sdf.Layer.CreateAnonymous()
    archived = example/'result/layers'
    layers = [str((archived/'out'/name).resolve())
              for name in ('presentation.usda', 'diagrams.usda', 'compliance.usda')]
    layers += [str(p.resolve()) for p in sorted((archived/'inputs').glob('*.usda'))]
    root.subLayerPaths = layers + [base.GetRootLayer().identifier]
    stage = Usd.Stage.Open(root)
    for key in ('upAxis', 'metersPerUnit', 'fallbackPrimTypes'):
        data = base.GetMetadata(key)
        if data is not None:
            stage.SetMetadata(key, data)
    add_fallbacks(stage)
    if stage.GetCompositionErrors():
        raise ValueError('Committed result layers do not compose.')
    return stage


def verify_results():
    """Verify the archived result fingerprint without evaluating or publishing."""
    stage = committed_stage()
    statuses = [p.GetAttribute('aeco:compliance:status') for p in stage.Traverse()]
    statuses = [a.Get() for a in statuses if a and a.HasAuthoredValue()]
    stale = stale_paths(stage)
    if not statuses or stale:
        raise ValueError(f'Committed results: {len(statuses)} checked, {len(stale)} stale.')
    return {'fingerprint': fingerprint(stage), 'checked': len(statuses), 'stale': len(stale),
            'pass': statuses.count('pass'), 'fail': statuses.count('fail')}


def hook(stage,out,*,migrate=False):
    add_fallbacks(stage)
    result=write_results(stage,out/'compliance.usda')
    if migrate:
        check_migration(Path(__file__).parent/'result/layers/out/compliance.usda', out/'compliance.usda')
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
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--migrate-fingerprint',action='store_true',
                       help='Republish the new fingerprint only if all committed result opinions agree.')
    modes.add_argument('--verify-results',action='store_true',
                       help='Verify committed result layers against the pinned source without recomputation.')
    args=parser.parse_args()
    if not os.environ.get('AECO_DATACENTRE_ROOT'):
        parser.error('AECO_DATACENTRE_ROOT must name the pinned data-centre checkout.')
    if args.verify_results:
        if args.publish:
            parser.error('--verify-results cannot publish.')
        print('== stage: verify committed results (no recomputation)',flush=True)
        print(json.dumps(verify_results(),sort_keys=True))
        return
    if args.migrate_fingerprint and not args.publish:
        parser.error('--migrate-fingerprint requires --publish.')
    run_example(Path(__file__).parent,lambda stage,out: hook(stage,out,migrate=args.migrate_fingerprint),
                variant='iris',publish=args.publish,keywords=[])


if __name__=='__main__':main()
