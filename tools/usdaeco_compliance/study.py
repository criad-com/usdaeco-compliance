"""Study locations are settings when authoring and composed data when reading."""
import os
from pxr import Sdf
from .model import specifications


def configured_root(root=None):
    text = os.environ.get('AECO_STUDY_ROOT', '/') if root is None else str(root)
    if not Sdf.Path.IsValidPathString(text):
        raise ValueError('Study root must be / or an absolute prim path.')
    path = Sdf.Path(text)
    if not path.IsAbsolutePath() or (path != Sdf.Path.absoluteRootPath and
                                    (not path.IsPrimPath() or path.ContainsPrimVariantSelection())):
        raise ValueError('Study root must be / or an absolute prim path.')
    return path


def study_root(stage=None, root=None):
    """An explicit argument wins; otherwise prefer existing specifications to env."""
    if root is not None:
        return configured_root(root)
    if stage is not None:
        roots = {p.GetParent().GetPath().GetParentPath() for p in specifications(stage)}
        if len(roots) > 1:
            raise ValueError('Specifications span multiple study roots; select one explicitly.')
        if roots:
            return roots.pop()
        roots = {configured_root(layer.customLayerData['aecoComplianceStudyRoot'])
                 for layer in stage.GetLayerStack() if 'aecoComplianceStudyRoot' in layer.customLayerData}
        if len(roots) > 1:
            raise ValueError('Layers span multiple study roots; select one explicitly.')
        if roots:
            return roots.pop()
    return configured_root()


def define_scopes(stage, path):
    """Define plain Scope ancestors, including /Studies in the suite layout."""
    for prefix in Sdf.Path(path).GetPrefixes():
        stage.DefinePrim(prefix, 'Scope')


def record_root(layer, root):
    # Keep the legacy publication byte-identical, including its metadata.
    if root != Sdf.Path.absoluteRootPath:
        layer.customLayerData = {**layer.customLayerData, 'aecoComplianceStudyRoot': str(root)}


def selected_specification(stage, row, name):
    """Resolve a presentation band through the evaluated element's actual targets."""
    matches = [stage.GetPrimAtPath(path) for path in row['specifications']
               if Sdf.Path(path).name == name]
    if len(matches) != 1 or not matches[0]:
        raise ValueError('Expected one applicable specification named ' + name)
    return matches[0]
