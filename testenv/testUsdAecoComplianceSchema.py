#!/pxrpythonsubst
import unittest
from pathlib import Path
from pxr import Plug, Usd, UsdGeom
ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoCompliance'))


class TestSchema(unittest.TestCase):
    def test_registry(self):
        registry = Usd.SchemaRegistry()
        for name in ('AecoSpecification', 'AecoRequirement'):
            self.assertIsNotNone(registry.FindConcretePrimDefinition(name))
        definition = registry.FindAppliedAPIPrimDefinition('AecoComplianceAPI')
        for name in ('specifications', 'status', 'report'):
            self.assertIs(definition.GetPropertyMetadata('aeco:compliance:'+name, 'aecoDerived'), True)

    def test_application(self):
        stage = Usd.Stage.CreateInMemory()
        self.assertTrue(stage.DefinePrim('/Reader','Xform').CanApplyAPI('AecoComplianceAPI'))
        self.assertFalse(stage.DefinePrim('/Material','Material').CanApplyAPI('AecoComplianceAPI'))

    def test_typed_fallbacks(self):
        stage = Usd.Stage.Open(str(ROOT/'usdAecoCompliance/examples/minimal.usda'))
        self.assertFalse(stage.GetCompositionErrors())
        self.assertEqual(list(stage.GetMetadata('fallbackPrimTypes')['AecoSpecification']), ['Scope'])


if __name__ == '__main__':
    unittest.main()
