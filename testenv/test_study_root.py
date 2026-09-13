"""Configurable studies over the release example and the suite's project catalog."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pxr import Sdf, Usd, UsdGeom

from usdaeco_compliance.convert import convert_sources, SOURCES
from usdaeco_compliance.evaluator import evaluate, fingerprint, stale_paths, write_results
from usdaeco_compliance.model import specifications
from usdaeco_compliance.presentation import draw, present_facility
from usdaeco_compliance.study import configured_root, define_scopes, study_root
from testUsdAecoComplianceValidators import fixture, errors, READER

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT/'examples/datacentre/inputs'
LOCATION = '/Studies/compliance'


@pytest.mark.parametrize('path', ['', 'Studies/compliance', '../study', '/Studies.attr', '/Studies{v=a}', '/Studies/', '//Studies'])
def test_invalid_root(path):
    with pytest.raises(ValueError, match='absolute prim path'):
        configured_root(path)


def test_relocation_requires_recheck_and_data_wins_over_environment(tmp_path, monkeypatch):
    stage = fixture()
    previous = fingerprint(stage)
    write_results(stage, tmp_path/'results.usda')
    define_scopes(stage, LOCATION)
    edit = Sdf.BatchNamespaceEdit()
    edit.Add('/Specifications', LOCATION+'/Specifications')
    assert stage.GetRootLayer().Apply(edit)
    monkeypatch.setenv('AECO_STUDY_ROOT', '/WrongSetting')
    assert str(study_root(stage)) == LOCATION
    assert fingerprint(stage) != previous
    assert stale_paths(stage) == [READER]
    assert errors(stage, 'ComplianceStale')
    result = write_results(stage, tmp_path/'results.usda')
    assert result['results'][0]['status'] == 'pass'
    assert result['results'][0]['specifications'] == [LOCATION+'/Specifications/Reach']
    assert not stale_paths(stage)
    assert not errors(stage, 'RequirementUnmeasurable')
    assert not errors(stage, 'SpecificationWithoutApplicability')
    stage.GetPrimAtPath(LOCATION+'/Specifications/Reach/Height').GetAttribute('aeco:req:values').Set([.5, .8])
    assert errors(stage, 'ComplianceStale')
    assert LOCATION+'/Specifications/Reach/Height' in errors(stage, 'MisplacedDevice')[0].GetMessage()
    stage.RemovePrim(LOCATION)
    assert str(study_root(stage)) == LOCATION  # persisted result metadata
    assert write_results(stage, tmp_path/'results.usda')['results'][0]['status'] == 'notApplicable'
    assert Sdf.Layer.FindOrOpen(str(tmp_path/'results.usda')).customLayerData['aecoComplianceStudyRoot'] == LOCATION


def test_preparation_leaves_another_librarys_camera_layer_alone(tmp_path, monkeypatch):
    from examples.datacentre.run import prepare_study
    monkeypatch.setenv('AECO_STUDY_ROOT', LOCATION)
    other = Usd.Stage.CreateNew(str(tmp_path/'cameras.usda'))
    UsdGeom.Camera.Define(other, '/Renders/other/overview')
    other.GetRootLayer().Save()
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [str(INPUTS/'cameras.usda'), other.GetRootLayer().identifier]
    prepare_study(stage, tmp_path/'output')
    assert stage.GetPrimAtPath('/Renders/compliance/overview')
    assert stage.GetPrimAtPath('/Renders/other/overview')
    assert other.GetRootLayer().identifier in stage.GetRootLayer().subLayerPaths


@pytest.fixture(params=['example', 'suite'])
def source(request):
    if request.param == 'example':
        configured = os.environ.get('AECO_DATACENTRE_ROOT')
        if not configured:
            pytest.skip('Set AECO_DATACENTRE_ROOT to the pinned example release.')
        root, version, variant = Path(configured), '0.4.8', 'iris'
    else:
        root = Path(os.environ.get('AECO_DATACENTRE_SUITE_ROOT', ROOT.parent/'usdaeco-datacentre-0.5.2'))
        if not root.is_dir():
            pytest.skip('Set AECO_DATACENTRE_SUITE_ROOT to the v0.5.2 suite fixture.')
        version, variant = '0.5.2', 'full'
    assert json.loads((root/'library.json').read_text())['version'] == version
    return root/'dist'/variant/'dc.usda'


def compose(source):
    base = Usd.Stage.Open(str(source))
    layer = Sdf.Layer.CreateAnonymous()
    layer.subLayerPaths = [str(p) for p in sorted(INPUTS.glob('*.usda'))] + [str(source)]
    stage = Usd.Stage.Open(layer)
    stage.SetDefaultPrim(stage.GetPrimAtPath(base.GetDefaultPrim().GetPath()))
    for key in ('upAxis', 'metersPerUnit', 'fallbackPrimTypes'):
        stage.SetMetadata(key, base.GetMetadata(key))
    return stage


def test_converter_paths_and_legacy_bytes(source, tmp_path, monkeypatch):
    base = Usd.Stage.Open(str(source))
    types = json.loads((INPUTS/'type-map.json').read_text())
    for location in ('/', LOCATION, '/Review/Compliance'):
        monkeypatch.setenv('AECO_STUDY_ROOT', location)
        output = tmp_path/('legacy' if location == '/' else location.strip('/'))
        convert_sources(INPUTS, output, base, types)
        for _, name in SOURCES:
            layer = Sdf.Layer.FindOrOpen(str(output/name))
            stage = Usd.Stage.Open(layer)
            assert str(study_root(stage)) == location
            assert stage.GetDefaultPrim().GetPath().pathElementCount == 1
            for spec in specifications(stage):
                assert spec.GetParent().GetPath() == Sdf.Path(location).AppendChild('Specifications')
                assert spec.GetRelationship('aeco:spec:appliesToTypes').GetTargets() == list(map(Sdf.Path, types.values()))
            if location == '/':
                assert (output/name).read_bytes() == (INPUTS/name).read_bytes()
            else:
                assert layer.customLayerData['aecoComplianceStudyRoot'] == location
                assert stage.GetPrimAtPath(Sdf.Path(location).GetPrefixes()[0]).GetTypeName() == 'Scope'
                assert not stage.GetPrimAtPath('/Specifications')

    monkeypatch.setenv('AECO_STUDY_ROOT', '/IgnoredSetting')
    output = tmp_path/'cli-conversion'
    completed = subprocess.run([sys.executable, str(ROOT/'tools/run_compliance.py'), 'convert', str(INPUTS),
                                '--stage', str(source), '--type-map', str(INPUTS/'type-map.json'),
                                '--output-dir', str(output), '--study-root', LOCATION],
                               env={k: v for k, v in os.environ.items() if k != 'PYTHONPATH'},
                               capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert all(str(study_root(Usd.Stage.Open(str(output/name)))) == LOCATION for _, name in SOURCES)


def test_hook_over_pinned_building(source, tmp_path, monkeypatch):
    from examples.datacentre.run import hook, prepare_study
    monkeypatch.setenv('AECO_STUDY_ROOT', LOCATION)
    monkeypatch.setenv('AECO_DATACENTRE_STAGE', str(source))
    stage = compose(source)
    before = evaluate(stage)
    source_files = {Path(l.realPath): hashlib.sha256(Path(l.realPath).read_bytes()).hexdigest()
                    for l in stage.GetUsedLayers() if l.realPath}
    project = stage.GetDefaultPrim().GetPath()
    catalog = project.AppendChild('_TypeCatalog')
    catalog_paths = {p.GetPath() for p in stage.TraverseAll() if p.GetPath().HasPrefix(catalog)}
    xforms = UsdGeom.XformCache()
    transforms = {p.GetPath(): xforms.GetLocalToWorldTransform(p) for p in stage.TraverseAll()
                  if p.IsA(UsdGeom.Xformable)}
    findings = hook(stage, tmp_path)
    report = json.loads((tmp_path/'report.json').read_text())
    # Only paths to clauses/documents change; all measurements and verdicts agree.
    assert json.loads(json.dumps(report).replace(LOCATION+'/Specifications', '/Specifications')) == before
    assert findings[0]['readers'] == len(before['results'])
    assert not stage.GetCompositionErrors()
    assert {p.GetPath() for p in stage.GetPseudoRoot().GetChildren()} == {project, Sdf.Path('/Studies'), Sdf.Path('/Renders')}
    assert stage.GetPrimAtPath('/Studies').GetTypeName() == 'Scope'
    assert not stage.GetPrimAtPath('/Specifications')
    assert not stage.GetPrimAtPath('/_TypeCatalog')
    assert {p.GetPath() for p in stage.TraverseAll() if p.GetPath().HasPrefix(catalog)} == catalog_paths
    assert catalog_paths
    for spec in specifications(stage):
        assert all(p.HasPrefix(catalog) and stage.GetPrimAtPath(p).IsAbstract()
                   for p in spec.GetRelationship('aeco:spec:appliesToTypes').GetTargets())
    cameras = [p for p in stage.Traverse() if p.IsA(UsdGeom.Camera)]
    assert len(cameras) == 4
    assert all(p.GetPath().HasPrefix('/Renders/compliance') for p in cameras)
    assert stage.GetPrimAtPath(LOCATION+'/ComplianceFigures/Elevation')
    xforms = UsdGeom.XformCache()
    assert all(xforms.GetLocalToWorldTransform(stage.GetPrimAtPath(p)) == value for p, value in transforms.items()
               if not p.HasPrefix('/Renders'))
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in source_files.items())
    assert not stale_paths(stage)
    assert not errors(stage, 'ComplianceStale')
    for row in report['results']:
        prim = stage.GetPrimAtPath(row['path'])
        assert [str(p) for p in prim.GetRelationship('aeco:compliance:specifications').GetTargets()] == row['specifications']
        assert all(stage.GetPrimAtPath(p) for p in row['specifications'])
    # Calling the hook's preparation twice neither duplicates nor mutates layers.
    paths = list(stage.GetRootLayer().subLayerPaths)
    prepare_study(stage, tmp_path)
    assert list(stage.GetRootLayer().subLayerPaths) == paths
    saved = tmp_path/'example.usda'
    stage.GetRootLayer().Export(str(saved))
    monkeypatch.setenv('AECO_STUDY_ROOT', '/UnrelatedSetting')
    reopened = Usd.Stage.Open(str(saved))
    assert str(study_root(reopened)) == LOCATION
    assert not stale_paths(reopened)
    draw(reopened, report, tmp_path/'redrawn.usda')
    present_facility(reopened, report, tmp_path/'redisplayed.usda')
    assert not stale_paths(reopened)
    # A fresh CLI process must follow authored paths without the setting/plugins.
    environment = {k: v for k, v in os.environ.items() if k not in ('AECO_STUDY_ROOT', 'PYTHONPATH', 'PXR_PLUGINPATH_NAME')}
    completed = subprocess.run([sys.executable, str(ROOT/'tools/run_compliance.py'), 'check', str(saved),
                                '--output', str(tmp_path/'cli.usda'), '--report', str(tmp_path/'cli.json')],
                               env=environment, capture_output=True, text=True, timeout=60)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert json.loads((tmp_path/'cli.json').read_text()) == report
