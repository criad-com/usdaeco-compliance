"""Fresh-process fingerprints and committed result verification."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pxr import Sdf, Usd, Vt

from usdaeco_compliance.evaluator import fingerprint, stale_paths, write_results
from testUsdAecoComplianceValidators import fixture, READER, REQ

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('CORE_DIR', ROOT.parent/'usdaeco-core'))
CORE_PLUGIN = Path(os.environ.get('CORE_PLUGIN_DIR', CORE/'usdAeco'))
AXIS_PLUGIN = Path(os.environ.get('AXIS_PLUGIN_DIR', ROOT.parent/'usdaeco-axis/usdAecoAxis'))


def probe(source, plugins):
    # Registration cannot be undone. Isolation also prevents conftest and an
    # inherited plugin search path from making the vanilla case a false pass.
    worker = '''
import json, sys
from pathlib import Path
from pxr import Plug
root, source, *plugins = sys.argv[1:]
for plugin in plugins:
    assert Plug.Registry().RegisterPlugins(plugin), plugin
from pxr import Usd
sys.path[:0] = [str(Path(root)/'tools'), root]
import usdaeco_compliance.evaluator as evaluator
def forbidden(*args, **kwargs):
    raise AssertionError('Verification must not recompute results')
evaluator.evaluate = evaluator.write_results = forbidden
from examples.datacentre.run import verify_results
if source == 'committed':
    result = verify_results()
else:
    stage = Usd.Stage.Open(source)
    assert not stage.GetCompositionErrors()
    result = {'fingerprint': evaluator.fingerprint(stage), 'stale': evaluator.stale_paths(stage)}
registry = Usd.SchemaRegistry()
result['schemas'] = [bool(registry.FindAppliedAPIPrimDefinition(name))
                     for name in ('AecoElementAPI', 'AecoComplianceAPI', 'AecoAxisAPI')]
print(json.dumps(result, sort_keys=True))
'''
    environment = {k: v for k, v in os.environ.items()
                   if k not in ('PYTHONPATH', 'PXR_PLUGINPATH_NAME', 'PXR_AR_DEFAULT_SEARCH_PATH')}
    completed = subprocess.run([sys.executable, '-I', '-c', worker, str(ROOT), str(source),
                                *[str(p.resolve()) for p in plugins]],
                               env=environment, text=True, capture_output=True, timeout=60)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def matrix(source):
    results = [probe(source, plugins) for plugins in
               ([], [ROOT/'usdAecoCompliance'], [CORE_PLUGIN, ROOT/'usdAecoCompliance', AXIS_PLUGIN])]
    assert [r['schemas'] for r in results] == [[False, False, False], [False, True, False], [True, True, True]]
    assert len({r['fingerprint'] for r in results}) == 1
    return results


@pytest.mark.parametrize('opinion', ['absent', 'fallback', 'samples', 'block'])
def test_same_authored_stage_across_plugin_sets(tmp_path, opinion):
    stage = fixture()
    stage.DefinePrim('/System', 'AecoSystem')
    fallbacks = dict(stage.GetMetadata('fallbackPrimTypes'))
    fallbacks['AecoSystem'] = Vt.TokenArray(['Scope'])
    stage.SetMetadata('fallbackPrimTypes', fallbacks)
    reader = stage.GetPrimAtPath(READER)
    reader.AddAppliedSchema('AecoAxisAPI')
    # Axis is an existing test pin, with fallback end=(1,0,0). In the samples
    # case Default resolves to that fallback only in the larger plugin set.
    end = reader.CreateAttribute('aeco:axis:end', Sdf.ValueTypeNames.Double3)
    if opinion == 'fallback':
        end.Set((1, 0, 0))
    elif opinion == 'samples':
        end.Set((2, 0, 0), 1)
        end.Set((3, 0, 0), 2)
    elif opinion == 'block':
        end.Block()
    write_results(stage, tmp_path/'result.usda')
    source = tmp_path/'source.usda'
    stage.GetRootLayer().Export(str(source))
    assert all(r['stale'] == [] for r in matrix(source))


def test_authoring_and_removing_fallback_equal_opinion():
    stage = fixture()
    phase = stage.GetPrimAtPath(READER).GetAttribute('aeco:phase')
    assert phase.Get() == 'proposed' and not phase.HasAuthoredValue()
    before = fingerprint(stage)
    phase.Set('proposed')
    assert phase.HasAuthoredValue() and fingerprint(stage) != before
    authored = fingerprint(stage)
    phase.Clear()
    assert phase.Get() == 'proposed' and not phase.HasAuthoredValue()
    assert fingerprint(stage) != authored and fingerprint(stage) == before


def test_authored_api_equal_to_builtin_counts():
    stage = fixture()
    system = stage.DefinePrim('/System', 'AecoSystem')
    assert system.GetMetadata('apiSchemas').GetAppliedItems() == ['CollectionAPI:members']
    assert 'apiSchemas' not in system.GetAllAuthoredMetadata()
    before = fingerprint(stage)
    system.SetMetadata('apiSchemas', Sdf.TokenListOp.CreateExplicit(['CollectionAPI:members']))
    assert fingerprint(stage) != before
    system.ClearMetadata('apiSchemas')
    assert fingerprint(stage) == before


def test_blocks_and_empty_relationship_targets_are_opinions():
    stage = fixture()
    phase = stage.GetPrimAtPath(READER).GetAttribute('aeco:phase')
    before = fingerprint(stage)
    phase.Block()
    assert not phase.HasAuthoredValue() and phase.GetResolveInfo().ValueIsBlocked()
    assert fingerprint(stage) != before
    phase.Clear()
    assert fingerprint(stage) == before
    rel = stage.GetPrimAtPath('/Specifications/Reach').GetRelationship('aeco:spec:appliesToTypes')
    rel.SetTargets([])
    assert fingerprint(stage) != before
    rel.ClearTargets(False)
    assert fingerprint(stage) == before


def test_authored_apis_inherits_and_composed_values(tmp_path):
    stage = fixture()
    before = fingerprint(stage)
    reader = stage.GetPrimAtPath(READER)
    reader.AddAppliedSchema('AecoAxisAPI')
    assert fingerprint(stage) != before
    catalog = stage.CreateClassPrim('/Catalog/Reader')
    reader.GetInherits().AddInherit(catalog.GetPath())
    end = catalog.CreateAttribute('aeco:axis:end', Sdf.ValueTypeNames.Double3)
    end.Set((1, 0, 0))
    inherited = fingerprint(stage)
    end.Set((2, 0, 0))
    assert fingerprint(stage) != inherited
    # An occurrence opinion hides the inherited change by USD strength.
    reader.CreateAttribute('aeco:axis:end', Sdf.ValueTypeNames.Double3).Set((3, 0, 0))
    overridden = fingerprint(stage)
    end.Set((4, 0, 0))
    assert fingerprint(stage) == overridden
    write_results(stage, tmp_path/'result.usda')
    assert fingerprint(stage) == overridden and not stale_paths(stage)


def test_time_sample_edit_changes_fingerprint():
    stage = fixture()
    position = stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate')
    position.Set((1.3, .25, 1.1), 1)
    before = fingerprint(stage)
    position.Set((1.3, .25, 1.65), 1)
    assert fingerprint(stage) != before


def test_result_migration_refuses_changed_verdict(tmp_path):
    from examples.datacentre.run import check_migration
    stage = fixture()
    old = tmp_path/'old.usda'
    new = tmp_path/'new.usda'
    write_results(stage, old)
    write_results(stage, new)
    check_migration(old, new)
    stage.GetPrimAtPath(READER).GetAttribute('xformOp:translate').Set((1.3, .25, 1.65))
    write_results(stage, new)
    with pytest.raises(ValueError, match='change result opinions'):
        check_migration(old, new)


def test_committed_results_verify_across_plugin_sets():
    if not os.environ.get('AECO_DATACENTRE_ROOT'):
        # Unit-only invocations need no facility. The full gate always supplies
        # the exact pin and separately requires committed verification.
        pytest.skip('Set AECO_DATACENTRE_ROOT for the pinned example verification.')
    results = matrix('committed')
    assert all((r['checked'], r['stale'], r['pass'], r['fail']) == (11, 0, 10, 1) for r in results)
