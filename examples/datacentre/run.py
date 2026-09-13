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
from usdaeco_compliance.study import configured_root, study_root, define_scopes, record_root
from usdaeco_compliance.model import specifications
from usdaeco_compliance.convert import SOURCES


def prepare_study(stage, out, root=None):
    """Relocate copies of the example's input layers; never edit source files.

    The shared harness and suite compose these inputs as direct sublayers.
    Authority order and catalog targets are retained in the relocated copies.
    """
    from pxr import Sdf, Usd
    location = configured_root(root) if root is not None or 'AECO_STUDY_ROOT' in os.environ else study_root(stage)
    if location == Sdf.Path.absoluteRootPath:
        return
    layer = stage.GetRootLayer()
    paths = list(layer.subLayerPaths)
    names = {filename for _, filename in SOURCES} | {'cameras.usda'}
    example = Path(__file__).parent
    owned = {(directory/name).resolve() for directory in
             (example/'inputs', example/'result/layers/inputs') for name in names}
    for index, path in enumerate(paths):
        source = Sdf.Layer.FindOrOpenRelativeToLayer(layer, path)
        if not source or Path(source.realPath).name not in names:
            continue
        if Path(source.realPath).resolve() not in owned and 'aecoComplianceStudyRoot' not in source.customLayerData:
            continue
        inputs = Usd.Stage.Open(source)
        scopes = {p.GetParent().GetPath() for p in specifications(inputs)}
        cameras = [p.GetPath() for p in inputs.Traverse() if p.GetTypeName() == 'Camera']
        moves = [(scope, location.AppendChild('Specifications')) for scope in scopes]
        moves += [(camera, Sdf.Path('/Renders/compliance').AppendChild(camera.name)) for camera in cameras]
        moves = [(old, new) for old, new in moves if old != new]
        if not moves:
            continue
        target = Path(out)/'inputs'/Path(source.realPath).name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == Path(source.realPath).resolve():
            raise ValueError('Relocated input output must differ from the source layer.')
        copied = Sdf.Layer.CreateNew(str(target.resolve()))
        copied.TransferContent(source)
        working = Usd.Stage.Open(copied)
        edits = Sdf.BatchNamespaceEdit()
        for old, new in moves:
            define_scopes(working, new.GetParentPath())
            edits.Add(old, new)
        if not copied.Apply(edits):
            raise ValueError('Cannot relocate compliance input layer: ' + source.GetDisplayName())
        if scopes:
            working.SetDefaultPrim(working.GetPrimAtPath(location.GetPrefixes()[0]))
        record_root(copied, location)
        copied.Save()
        paths[index] = str(target.resolve())
    layer.subLayerPaths = paths


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
    prepare_study(stage,out)
    add_fallbacks(stage)
    result=write_results(stage,out/'compliance.usda')
    if migrate:
        check_migration(Path(__file__).parent/'result/layers/out/compliance.usda', out/'compliance.usda')
    (out/'report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    errors=run(stage,['UsdAecoComplianceValidators'])
    expected_failures=sum(f['kind']=='misplacedDevice' for f in result['findings'])
    if len(errors)!=expected_failures or any(e.GetName()!='MisplacedDevice' for e in errors):
        raise ValueError('Unexpected validation findings: '+ '; '.join(e.GetName()+': '+e.GetMessage() for e in errors))
    source=(Path(os.environ['AECO_DATACENTRE_STAGE']).with_name('dc.manifest.json')
            if os.environ.get('AECO_DATACENTRE_STAGE') else
            Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/iris/dc.manifest.json')
    source_counts=json.loads(source.read_text())['counts']
    counts={s:sum(r['status']==s for r in result['results']) for s in ('pass','fail','warn','notApplicable')}
    findings=[{'kind':'summary','source_counts':source_counts,'readers':len(result['results']),
               **counts,'clause_failures':expected_failures,'illustrative':True}]+result['findings']
    draw(stage,result,out/'diagrams.usda')
    present_facility(stage,result,out/'presentation.usda')
    if stale_paths(stage):raise ValueError('Presentation unexpectedly changed the measurement inputs.')
    return findings


def run_study(output):
    """Write a configured study stage for composition by the suite, without publishing."""
    from pxr import Sdf, Usd
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(os.environ.get('AECO_DATACENTRE_STAGE') or
                  Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/iris/dc.usda').resolve()
    if not os.environ.get('AECO_DATACENTRE_STAGE'):
        pin = json.loads((ROOT/'dependencies.json').read_text())['repos']['datacentre']['ref']
        metadata = json.loads((Path(os.environ['AECO_DATACENTRE_ROOT'])/'library.json').read_text())
        if 'v'+metadata['version'] != pin:
            raise ValueError('Data-centre release differs from the example pin; use AECO_DATACENTRE_STAGE for a compatibility probe.')
    base = Usd.Stage.Open(str(source))
    if not base or base.GetCompositionErrors():
        raise ValueError('Study source stage does not compose.')
    if output/'example.usda' in {Path(l.realPath).resolve() for l in base.GetUsedLayers() if l.realPath}:
        raise ValueError('Study output must not overwrite a source layer.')
    layer = Sdf.Layer.CreateNew(str(output/'example.usda'))
    layer.subLayerPaths = [str(p.resolve()) for p in sorted((Path(__file__).parent/'inputs').glob('*.usda'))] + [str(source)]
    stage = Usd.Stage.Open(layer)
    if base.GetDefaultPrim():
        stage.SetDefaultPrim(stage.GetPrimAtPath(base.GetDefaultPrim().GetPath()))
    for key in ('upAxis', 'metersPerUnit', 'fallbackPrimTypes'):
        data = base.GetMetadata(key)
        if data is not None:
            stage.SetMetadata(key, data)
    findings = hook(stage, output)
    (output/'findings.json').write_text(json.dumps(findings, indent=2, sort_keys=True)+'\n')
    layer.subLayerPaths = [os.path.relpath(p, output) for p in layer.subLayerPaths]
    layer.Save()
    return stage


def main():
    os.environ["HDEMBREE_CAMERA_LIGHT_INTENSITY"]="100"
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--study-root', help='Study prim path; defaults to AECO_STUDY_ROOT or /.')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).parent/'out',
                        help='Configured study output directory (non-default roots only).')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--migrate-fingerprint',action='store_true',
                       help='Republish the new fingerprint only if all committed result opinions agree.')
    modes.add_argument('--verify-results',action='store_true',
                       help='Verify committed result layers against the pinned source without recomputation.')
    args=parser.parse_args()
    try:
        location=configured_root(args.study_root)
    except ValueError as exc:
        parser.error(str(exc))
    if args.study_root is not None:
        os.environ['AECO_STUDY_ROOT']=str(location)
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
    if str(location) != '/':
        if args.publish or args.migrate_fingerprint:
            parser.error('Configured studies write to --output-dir; publication uses the default root.')
        stage=run_study(args.output_dir)
        print(json.dumps({'stage': str(Path(args.output_dir)/'example.usda'),
                          'studyRoot': str(study_root(stage)), 'stale': len(stale_paths(stage))}, sort_keys=True))
        return
    run_example(Path(__file__).parent,lambda stage,out: hook(stage,out,migrate=args.migrate_fingerprint),
                variant='iris',publish=args.publish,keywords=[])


if __name__=='__main__':main()
