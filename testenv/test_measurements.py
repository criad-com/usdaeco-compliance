"""Independent geometric and composition drills, including known limitations."""
import json
import math
from pathlib import Path
import tempfile
import pytest
from pxr import Sdf, Usd, UsdGeom, Gf
from usdaeco_compliance.evaluator import compare, evaluate, fingerprint, write_results, stale_paths
from usdaeco_compliance.measure import Measurements, Unmeasurable, union_area
from usdaeco_compliance.model import attr, applies
from usdaeco_compliance.convert import convert_document
from testUsdAecoComplianceValidators import fixture, READER, REQ, errors


def door(stage):
    p = stage.DefinePrim('/World/Site/Facility/Level/Door', 'Xform')
    p.AddAppliedSchema('AecoElementAPI')
    attr(p,'aeco:id',Sdf.ValueTypeNames.String,'11cd7132-d2e9-5cd9-9be2-461959bf4600')
    attr(p,'aeco:class:ifc:code',Sdf.ValueTypeNames.String,'IfcDoor.DOOR')
    attr(p,'aeco:props:DC_DoorApproach:ApproachNormal',Sdf.ValueTypeNames.String,'+Y')
    body = UsdGeom.Cube.Define(stage,p.GetPath().AppendChild('Body'))
    body.CreateSizeAttr(1)
    body.AddTranslateOp().Set((0.5,0,1))
    body.AddScaleOp().Set((1,0.05,2))
    body.GetPrim().AddAppliedSchema('AecoDerivedGeometryAPI')
    attr(body.GetPrim(),'aeco:derived:source',Sdf.ValueTypeNames.String,p.GetAttribute('aeco:id').Get())
    attr(body.GetPrim(),'aeco:derived:role',Sdf.ValueTypeNames.Token,'body')
    return p


def test_height_uses_body_not_authored_mounting_parameter():
    stage=fixture(); p=stage.GetPrimAtPath(READER)
    attr(p,'aeco:props:DC_Security:MountingHeight',Sdf.ValueTypeNames.Double,9)
    m=Measurements(stage)
    assert m.get(p,'measured:centreHeightAboveFloor') == pytest.approx(1.1)
    assert m.get(p,'measured:bottomHeightAboveFloor') == pytest.approx(1.02)


def test_world_transform_floor_and_metres():
    stage=fixture(); level=stage.GetPrimAtPath('/World/Site/Facility/Level')
    UsdGeom.Xformable(level).AddTranslateOp().Set((20,30,7))
    assert Measurements(stage).get(stage.GetPrimAtPath(READER),'measured:centreHeightAboveFloor') == pytest.approx(1.1)
    stage.SetMetadata('metersPerUnit',0.001)
    assert Measurements(stage).get(stage.GetPrimAtPath(READER),'measured:centreHeightAboveFloor') == pytest.approx(.0011)


def test_door_edge_and_side_follow_geometry():
    stage=fixture(); door(stage); p=stage.GetPrimAtPath(READER)
    m=Measurements(stage)
    assert m.get(p,'measured:distanceToDoorLeafEdge') == pytest.approx(.3)
    assert m.get(p,'measured:sideOfDoor') == 'pull'
    p.GetAttribute('xformOp:translate').Set((1.5,-.25,1.1))
    m=Measurements(stage)
    assert m.get(p,'measured:distanceToDoorLeafEdge') == pytest.approx(.5)
    assert m.get(p,'measured:sideOfDoor') == 'push'


def test_missing_binding_after_door_removed():
    stage=fixture(); d=door(stage)
    stage.GetPrimAtPath(REQ).GetAttribute('aeco:req:measure').Set('measured:distanceToDoorLeafEdge')
    assert not errors(stage,'MissingBinding')
    stage.RemovePrim(d.GetPath())
    assert errors(stage,'MissingBinding')


def test_clear_area_subtracts_union_not_sum():
    stage=fixture()
    space=stage.DefinePrim('/World/Site/Facility/Level/Room','AecoSpace')
    attr(space,'aeco:id',Sdf.ValueTypeNames.String,'space')
    extent=UsdGeom.Cube.Define(stage,space.GetPath().AppendChild('Extent'))
    extent.CreateSizeAttr(1); extent.AddTranslateOp().Set((2,2,1.5)); extent.AddScaleOp().Set((4,4,3))
    extent.GetPrim().AddAppliedSchema('AecoDerivedGeometryAPI')
    attr(extent.GetPrim(),'aeco:derived:source',Sdf.ValueTypeNames.String,'space')
    attr(extent.GetPrim(),'aeco:derived:role',Sdf.ValueTypeNames.Token,'extent')
    for name,x in [('A',1),('B',1.5)]:
        p=stage.DefinePrim(space.GetPath().AppendChild(name),'Xform');p.AddAppliedSchema('AecoElementAPI')
        attr(p,'aeco:id',Sdf.ValueTypeNames.String,name)
        body=UsdGeom.Cube.Define(stage,p.GetPath().AppendChild('Body'));body.CreateSizeAttr(1)
        body.AddTranslateOp().Set((x,1,.5));body.GetPrim().AddAppliedSchema('AecoDerivedGeometryAPI')
        attr(body.GetPrim(),'aeco:derived:source',Sdf.ValueTypeNames.String,name)
        attr(body.GetPrim(),'aeco:derived:role',Sdf.ValueTypeNames.Token,'body')
    assert Measurements(stage).get(space,'measured:clearFloorArea') == pytest.approx(14.5)
    assert union_area([(0,0,1,1),(.5,0,1.5,1)]) == 1.5


@pytest.mark.parametrize('operator, measured, values, expected',[
    ('eq',1.01,[1],True),('ne',1.01,[1],False),('lt',.8,[1],True),('le',1.01,[1],True),
    ('gt',1.2,[1],True),('ge',.99,[1],True),('between',2.01,[1,2],True),('in',1.01,[1,3],True)])
def test_numeric_operators(operator,measured,values,expected):
    data=dict(measure='x',operator=operator,values=values,tokens=[],unit='m',tolerance=.02,severity='error')
    assert compare(measured,data) is expected


@pytest.mark.parametrize('updates',[{'values':[float('nan')]},{'tolerance':-1},{'unit':'mm'},
    {'operator':'invalid'},{'values':[]},{'values':[2,1],'operator':'between'}, {'tokens':['x']}])
def test_invalid_clauses_never_pass(updates):
    data=dict(measure='x',operator='eq',values=[1],tokens=[],unit='m',tolerance=0,severity='error')
    data.update(updates)
    with pytest.raises(Unmeasurable): compare(1,data)


def test_authority_is_usd_strength_and_muting():
    base=fixture()
    weak=Usd.Stage.CreateInMemory()
    p=weak.OverridePrim(REQ);attr(p,'aeco:req:values',Sdf.ValueTypeNames.DoubleArray,[1,1.7])
    strong=Usd.Stage.CreateInMemory()
    p=strong.OverridePrim(REQ);attr(p,'aeco:req:values',Sdf.ValueTypeNames.DoubleArray,[.9,1.2])
    root=Sdf.Layer.CreateAnonymous();root.subLayerPaths=[strong.GetRootLayer().identifier,weak.GetRootLayer().identifier,base.GetRootLayer().identifier]
    stage=Usd.Stage.Open(root); stage.SetMetadata('upAxis','Z');stage.SetMetadata('metersPerUnit',1.)
    stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate').Set((1.3,.25,1.65))
    before=UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(READER))
    assert evaluate(stage)['results'][0]['status']=='fail'
    stage.MuteLayer(strong.GetRootLayer().identifier)
    assert evaluate(stage)['results'][0]['status']=='pass'
    assert UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(READER))==before
    stage.UnmuteLayer(strong.GetRootLayer().identifier)
    assert evaluate(stage)['results'][0]['status']=='fail'


def test_stale_on_requirement_change_and_mute(tmp_path):
    stage=fixture();write_results(stage,tmp_path/'result.usda')
    assert not stale_paths(stage)
    stage.GetPrimAtPath(REQ).GetAttribute('aeco:req:values').Set([.5,.8])
    assert stale_paths(stage)==[READER]


def test_stale_on_body_change_without_stamp(tmp_path):
    stage=fixture();write_results(stage,tmp_path/'result.usda')
    stage.GetPrimAtPath(READER+'/Body').GetAttribute('size').Set(2)
    assert stale_paths(stage)==[READER]


def test_not_applicable_after_spec_removed(tmp_path):
    stage=fixture();write_results(stage,tmp_path/'result.usda')
    stage.RemovePrim('/Specifications')
    assert write_results(stage,tmp_path/'result.usda')['results'][0]['status']=='notApplicable'


def test_applicability_classification_and_inherited_type():
    stage=fixture(); p=stage.GetPrimAtPath(READER); spec=stage.GetPrimAtPath('/Specifications/Reach')
    stage.CreateClassPrim('/Catalog/Reader');stage.CreateClassPrim('/Catalog/Wrong')
    spec.CreateRelationship('aeco:spec:appliesToTypes').SetTargets(['/Catalog/Reader'])
    assert not applies(spec,p)
    p.GetInherits().AddInherit('/Catalog/Reader')
    assert applies(spec,p)
    p.GetAttribute('aeco:class:ifc:code').Set('IfcDoor.DOOR')
    assert not applies(spec,p)


def test_converter_requires_illustrative_marker(tmp_path):
    with pytest.raises(ValueError,match='illustrative'):
        convert_document({'illustrative':False},tmp_path/'x.usda',name='x')


def test_result_never_overwrites_input(tmp_path):
    stage=fixture(); stage.GetRootLayer().Export(str(tmp_path/'input.usda'))
    opened=Usd.Stage.Open(str(tmp_path/'input.usda'))
    before=(tmp_path/'input.usda').read_bytes()
    with pytest.raises(ValueError,match='source'): write_results(opened,tmp_path/'input.usda')
    assert (tmp_path/'input.usda').read_bytes()==before


@pytest.mark.parametrize('height, code, status', [(1.1,0,'pass'),(1.65,1,'fail')])
def test_cli_plugin_free_check(tmp_path,height,code,status):
    import subprocess,sys,os
    stage=fixture();stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate').Set((1.3,.25,height))
    source=tmp_path/'source.usda';stage.GetRootLayer().Export(str(source))
    root=Path(__file__).resolve().parents[1]
    environment={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PXR_PLUGINPATH_NAME')}
    run=subprocess.run([sys.executable,str(root/'tools/run_compliance.py'),'check',str(source),'--output',str(tmp_path/'result.usda'),'--report',str(tmp_path/'report.json')],env=environment,capture_output=True,text=True)
    assert run.returncode==code,run.stderr
    report=json.loads((tmp_path/'report.json').read_text())
    assert report['results'][0]['status']==status
    assert report['results'][0]['clauses'][0]['measured']==pytest.approx(height)


def test_cli_refuses_empty_specifications(tmp_path):
    from usdaeco_compliance.cli import main
    stage=fixture();stage.RemovePrim('/Specifications');source=tmp_path/'empty.usda';stage.GetRootLayer().Export(str(source))
    with pytest.raises(SystemExit) as exit:
        main(['check',str(source),'--output',str(tmp_path/'result.usda'),'--report',str(tmp_path/'report.json')])
    assert exit.value.code==2
    assert not (tmp_path/'result.usda').exists()
