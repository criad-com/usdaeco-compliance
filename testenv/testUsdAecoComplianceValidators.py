#!/pxrpythonsubst
import tempfile
import unittest
from pathlib import Path
from pxr import Plug, Usd, UsdGeom, Sdf
from usdaeco_compliance.evaluator import evaluate, write_results
from usdaeco_compliance.model import attr
ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoComplianceValidators'))
from pxr import UsdValidation

READER = '/World/Site/Facility/Level/Reader'
REQ = '/Specifications/Reach/Height'


def fixture():
    source = Sdf.Layer.FindOrOpen(str(ROOT/'usdAecoCompliance/examples/minimal.usda'))
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString(source.ExportToString())
    return Usd.Stage.Open(layer)


def errors(stage, rule):
    registry = UsdValidation.ValidationRegistry()
    validator = registry.GetOrLoadValidatorByName('usdAecoComplianceValidators:'+rule+'Checker')
    assert validator, rule
    return UsdValidation.ValidationContext([validator]).Validate(stage)


class TestValidators(unittest.TestCase):
    def test_RequirementUnmeasurable(self):
        stage = fixture()
        self.assertFalse(errors(stage, 'RequirementUnmeasurable'))
        stage.GetPrimAtPath(REQ).GetAttribute('aeco:req:measure').Set('measured:unknown')
        self.assertEqual(evaluate(stage)['results'][0]['status'], 'fail')
        self.assertEqual(errors(stage, 'RequirementUnmeasurable')[0].GetName(), 'RequirementUnmeasurable')

    def test_SpecificationWithoutApplicability(self):
        stage = fixture()
        self.assertFalse(errors(stage, 'SpecificationWithoutApplicability'))
        stage.GetPrimAtPath('/Specifications/Reach').GetAttribute('aeco:spec:appliesToClassification').Set([])
        self.assertFalse(evaluate(stage)['results'])
        self.assertEqual(errors(stage, 'SpecificationWithoutApplicability')[0].GetName(), 'SpecificationWithoutApplicability')

    def test_ComplianceStale(self):
        stage = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            write_results(stage, Path(tmp)/'result.usda')
            self.assertFalse(errors(stage, 'ComplianceStale'))
            stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate').Set((1.3,0.25,1.65))
            self.assertEqual(stage.GetPrimAtPath(READER).GetAttribute('aeco:compliance:status').Get(), 'pass')
            self.assertEqual(evaluate(stage)['results'][0]['status'], 'fail')
            self.assertEqual(errors(stage, 'ComplianceStale')[0].GetName(), 'ComplianceStale')
            write_results(stage, Path(tmp)/'result.usda')
            self.assertFalse(errors(stage, 'ComplianceStale'))

    def test_MissingDevice(self):
        stage = fixture()
        self.assertFalse(errors(stage, 'MissingDevice'))
        stage.RemovePrim(READER)
        self.assertFalse(evaluate(stage)['results'])
        self.assertEqual(errors(stage, 'MissingDevice')[0].GetName(), 'MissingDevice')

    def test_MisplacedDevice(self):
        stage = fixture()
        self.assertFalse(errors(stage, 'MisplacedDevice'))
        stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate').Set((1.3,0.25,1.65))
        self.assertAlmostEqual(evaluate(stage)['results'][0]['clauses'][0]['measured'], 1.65)
        result = errors(stage, 'MisplacedDevice')
        self.assertEqual(result[0].GetName(), 'MisplacedDevice')
        self.assertIn('1.65', result[0].GetMessage())
        self.assertIn('/Specifications/Reach/Height', result[0].GetMessage())

    def test_UnapprovedProduct(self):
        stage = fixture()
        req = stage.GetPrimAtPath(REQ)
        req.GetAttribute('aeco:req:measure').Set('aeco:type:model')
        req.GetAttribute('aeco:req:operator').Set('in')
        req.GetAttribute('aeco:req:values').Set([])
        attr(req, 'aeco:req:tokens', Sdf.ValueTypeNames.StringArray, ['Approved reader'])
        req.GetAttribute('aeco:req:unit').Set('1')
        req.GetAttribute('aeco:req:tolerance').Set(0)
        prim = stage.GetPrimAtPath(READER)
        attr(prim, 'aeco:type:model', Sdf.ValueTypeNames.String, 'Approved reader')
        self.assertFalse(errors(stage, 'UnapprovedProduct'))
        prim.GetAttribute('aeco:type:model').Set('Substituted reader')
        self.assertEqual(evaluate(stage)['findings'][0]['kind'], 'unapprovedProduct')
        self.assertEqual(errors(stage, 'UnapprovedProduct')[0].GetName(), 'UnapprovedProduct')

    def test_MissingBinding(self):
        stage = fixture()
        req = stage.GetPrimAtPath(REQ)
        req.GetAttribute('aeco:req:measure').Set('measured:distanceToDoorLeafEdge')
        self.assertEqual(evaluate(stage)['findings'][0]['kind'], 'missingBinding')
        self.assertEqual(errors(stage, 'MissingBinding')[0].GetName(), 'MissingBinding')


if __name__ == '__main__':
    unittest.main()
