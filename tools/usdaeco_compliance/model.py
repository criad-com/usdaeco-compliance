"""Data access shared by the converter, evaluator and validators."""
from pxr import Usd


def value(prim, name, default=None):
    attr = prim.GetAttribute(name)
    result = attr.Get() if attr else None
    return default if result is None else result


def has_api(prim, name):
    authored = prim.GetMetadata('apiSchemas')
    return name in prim.GetAppliedSchemas() or bool(authored and name in authored.GetAppliedItems())


def elements(stage):
    return [p for p in stage.Traverse() if has_api(p, 'AecoElementAPI')]


def classifications(prim):
    result = []
    for attr in prim.GetAttributes():
        parts = attr.GetName().split(':')
        if len(parts) == 4 and parts[:2] == ['aeco', 'class'] and parts[3] == 'code' and attr.Get():
            result.append(parts[2] + ':' + attr.Get())
    return result


def classified(prim, selector):
    return any(code == selector or code.startswith(selector + '.') for code in classifications(prim))


def specifications(stage):
    return sorted((p for p in stage.Traverse() if p.GetTypeName() == 'AecoSpecification'), key=lambda p: str(p.GetPath()))


def requirements(spec):
    return sorted((p for p in spec.GetChildren() if p.GetTypeName() == 'AecoRequirement'), key=lambda p: str(p.GetPath()))


def applies(spec, prim):
    codes = value(spec, 'aeco:spec:appliesToClassification', [])
    types = spec.GetRelationship('aeco:spec:appliesToTypes').GetTargets()
    inherited = prim.GetInherits().GetAllDirectInherits()
    return bool(codes or types) and (not codes or any(classified(prim, c) for c in codes)) and (not types or any(t in inherited for t in types))


def attr(prim, name, typ, data):
    from pxr import Sdf
    uniform = name in {'aeco:spec:kind', 'aeco:req:operator', 'aeco:req:severity', 'aeco:compliance:status'}
    variability = Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying
    return prim.CreateAttribute(name, typ, custom=False, variability=variability).Set(data)


def add_fallbacks(stage):
    from pxr import Vt
    fallbacks = dict(stage.GetMetadata('fallbackPrimTypes') or {})
    fallbacks.update(AecoSpecification=Vt.TokenArray(['Scope']), AecoRequirement=Vt.TokenArray(['Scope']))
    stage.SetMetadata('fallbackPrimTypes', fallbacks)


def nearest(prim, types):
    parent = prim.GetParent()
    while parent and not parent.IsPseudoRoot():
        if parent.GetTypeName() in types:
            return parent
        parent = parent.GetParent()
    return None
