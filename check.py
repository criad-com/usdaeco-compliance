#!/usr/bin/env python3
"""Run the contract gate and print N checks, M failed."""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
CORE=Path(os.environ.get('CORE_DIR',HERE.parent/'usdaeco-core')).resolve()
TOOLCHAIN=Path(os.environ.get('TOOLCHAIN_DIR',HERE.parent/'usdaeco-toolchain')).resolve()
sys.path.insert(0,str(TOOLCHAIN/'tools'))
sys.path.insert(0,str(HERE/'tools'))
sys.path.insert(0,str(HERE))
from usdaeco_check import Report, can_apply, plugin_requires, registry_probe, validate_examples
from usdaeco_check.structure import check_structure
from usdaeco_check.example import check_example
from usdaeco_check.validation import run


def main():
    os.environ["HDEMBREE_CAMERA_LIGHT_INTENSITY"]="100"
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-plugin',default=os.environ.get('CORE_PLUGIN_DIR',str(CORE/'out/plugins/usdAeco/resources')))
    args=parser.parse_args()
    report=Report()
    print('== stage: registry and core validator import',flush=True)
    if not report.add(plugin_requires([args.core_plugin,HERE/'usdAecoCompliance'])):return report.finish()
    from pxr import Plug, Usd, UsdValidation, UsdGeom, Gf
    Plug.Registry().RegisterPlugins(str(CORE/'usdAecoValidators'))
    Plug.Registry().RegisterPlugins(str(HERE/'usdAecoComplianceValidators'))
    try:
        importlib.import_module('usdAecoValidators')
    except ImportError:
        report.check('core validators import',False,'usdAecoValidators is unavailable; run with the core checkout on PYTHONPATH.')
        return report.finish()
    report.check('core validators import',True,'usdAecoValidators imported; no skip path')
    registry=UsdValidation.ValidationRegistry()
    for keyword,count in [('UsdAecoValidators',8),('UsdAecoComplianceValidators',7)]:
        metadata=registry.GetValidatorMetadataForKeyword(keyword)
        report.check(keyword+' listing',len(metadata)==count and all(registry.GetOrLoadValidatorByName(m.name) for m in metadata),f'{len(metadata)} declared validators loaded')
    report.add(registry_probe(['AecoComplianceAPI'],['AecoSpecification','AecoRequirement']))
    report.add(can_apply([('Xform','AecoComplianceAPI',True),('Material','AecoComplianceAPI',False)]))
    definition=Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('AecoComplianceAPI')
    report.check('derived result metadata',all(definition.GetPropertyMetadata('aeco:compliance:'+p,'aecoDerived') is True for p in ('specifications','status','report')))
    report.add(validate_examples(HERE/'usdAecoCompliance/examples',validators=[lambda s:run(s,['UsdAecoValidators','UsdAecoComplianceValidators'])]))
    print('== stage: structure',flush=True)
    structure=check_structure(HERE,deps=[args.core_plugin])
    for result in structure:report.add(result)
    print(f'structure: {len(structure)} checks, {sum(not r.ok for r in structure)} failed',flush=True)
    print('== stage: pinned example and result reproduction',flush=True)
    example=HERE/'examples/datacentre'
    if not report.add(check_example(example)):return report.finish()
    from usdaeco_compliance.evaluator import evaluate, fingerprint
    from usdaeco_compliance.convert import convert_sources
    stage=Usd.Stage.Open(str(example/'out/example.usda'))
    results=json.loads((example/'out/report.json').read_text())
    count={s:sum(r['status']==s for r in results['results']) for s in ('pass','fail')}
    report.check('iris acceptance',count=={'pass':10,'fail':1} and len(results['findings'])==2
                 and all(abs(f['measured']-1.65)<1e-6 and f['clause'].endswith('/Clause01') for f in results['findings']),
                 f"{count['pass']} pass, {count['fail']} fail; two clauses name 1.65 m")
    core_errors=run(stage,['UsdAecoValidators'])
    hard=[e for e in core_errors if e.GetType()==UsdValidation.ValidationErrorType.Error]
    report.check('core validators on iris result',not hard,f'{len(hard)} errors, {len(core_errors)-len(hard)} warnings')
    figures=[p for p in stage.Traverse() if p.IsA(UsdGeom.Gprim) and p.GetCustomDataByKey('aecoCompliancePresentation')]
    report.check('publication representation marks',bool(figures) and all('AecoDerivedGeometryAPI' in p.GetAppliedSchemas() and p.GetAttribute('aeco:derived:role').Get()=='symbol' and p.GetAttribute('aeco:derived:source').Get() for p in figures),f'{len(figures)} facility-derived symbols')
    # Every source specification is converted deterministically, preserving labels.
    data_root=Path(os.environ['AECO_DATACENTRE_ROOT'])
    base=Usd.Stage.Open(str(data_root/'dist/iris/dc.usda'))
    print('== stage: facility presentation acceptance',flush=True)
    source_prims=list(base.TraverseAll())
    source_xforms, result_xforms=UsdGeom.XformCache(),UsdGeom.XformCache()
    preserved=True
    for original in source_prims:
        composed=stage.GetPrimAtPath(original.GetPath())
        if not composed or original.GetTypeName()!=composed.GetTypeName():
            preserved=False
            break
        if original.IsA(UsdGeom.Xformable):
            preserved &= source_xforms.GetLocalToWorldTransform(original)==result_xforms.GetLocalToWorldTransform(composed)
        for name in ('aeco:id','points','faceVertexCounts','faceVertexIndices','extent'):
            source_attr=original.GetAttribute(name)
            if source_attr:
                preserved &= source_attr.Get()==composed.GetAttribute(name).Get()
    report.check('full pinned facility preserved',preserved,
                 f'{len(source_prims)} source prims; identities, transforms and mesh geometry unchanged')
    from usdaeco_compliance.measure import Measurements
    from usdaeco_compliance.presentation import GREEN, RED
    measurement=Measurements(stage)
    decorated=True
    for row in results['results']:
        reader=stage.GetPrimAtPath(row['path'])
        colour=Gf.Vec3f(GREEN if row['status']=='pass' else RED)
        bodies=measurement.bodies(reader)
        decorated &= bool(bodies) and all(b.GetAttribute('primvars:displayColor').Get()==[colour] for b in bodies)
        decorated &= all(bool(stage.GetPrimAtPath(reader.GetPath().AppendPath('ComplianceEnvelope/'+name)))
                         for name in ('accessibility','employer_security','reader_datasheet','Status'))
    report.check('reader body colours and clause envelopes',decorated,
                 f"{len(results['results'])} original readers coloured; three illustrative bands each")
    reader=stage.GetPrimAtPath(next(r['path'] for r in results['results'] if r['status']=='fail'))
    camera=UsdGeom.Camera(stage.GetPrimAtPath('/Renders/overview')).GetCamera(Usd.TimeCode.Default())
    focus=measurement.centre(reader)
    report.check('vanilla camera frames facility reader',camera.frustum.Intersects(focus)
                 and camera.frustum.Intersects(Gf.Vec3d(focus[0],focus[1],measurement.floor(reader)+1.05))
                 and not camera.frustum.Intersects(Gf.Vec3d(38,5,20)),
                 'failing body and hard height band in view; drawing sheet outside view')
    with tempfile.TemporaryDirectory() as tmp:
        convert_sources(example/'inputs',tmp,base,json.loads((example/'inputs/type-map.json').read_text()))
        generated=list(Path(tmp).glob('*.usda'))
        report.check('illustrative conversion reproducible',len(generated)==3 and all(p.read_bytes()==(example/'inputs'/p.name).read_bytes() for p in generated))
    from usdaeco_compliance.model import elements
    before={str(p.GetPath()):(p.GetAttribute('aeco:id').Get(),UsdGeom.XformCache().GetLocalToWorldTransform(p)) for p in elements(stage)}
    muted=[l.identifier for l in stage.GetUsedLayers() if Path(l.identifier).name in ('01-accessibility.usda','02-employer-security.usda')]
    for identifier in muted:stage.MuteLayer(identifier)
    audit=evaluate(stage)
    after={str(p.GetPath()):(p.GetAttribute('aeco:id').Get(),UsdGeom.XformCache().GetLocalToWorldTransform(p)) for p in elements(stage)}
    report.check('authority muting audit',len(muted)==2 and len(audit['results'])==11 and all(r['status']=='pass' for r in audit['results']), 'both hard-source layers muted: 11 pass, 0 fail')
    report.check('identity and transforms preserved',before==after,f'{len(before)} core elements unchanged by muting')
    print('== stage: seeded defect and measurement tests',flush=True)
    tests=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=HERE,text=True,capture_output=True,env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'})
    print(tests.stdout,flush=True)
    if tests.stderr:print(tests.stderr,flush=True)
    report.check('pytest',tests.returncode==0,tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else 'no test output')
    return report.finish()


if __name__=='__main__':raise SystemExit(main())
