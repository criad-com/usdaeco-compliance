"""Evaluate composed clauses and write replaceable result opinions."""
import hashlib
import json
import math
from pathlib import Path
from pxr import Sdf, Usd, UsdGeom
from .measure import Measurements, Unmeasurable, MissingBinding, MEASURE_UNITS
from .model import value, elements, specifications, requirements, applies, attr, add_fallbacks, has_api

OPERATORS = {'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'between', 'in'}
FINDING_KINDS = ('missingDevice', 'misplacedDevice', 'unapprovedProduct', 'missingBinding')


def clause_data(req):
    return {name: value(req, 'aeco:req:'+name, default) for name, default in (
        ('measure', ''), ('operator', 'between'), ('values', []), ('tokens', []),
        ('unit', 'm'), ('tolerance', 0), ('severity', 'error'), ('rationale', ''))}


def check_clause(data):
    op, nums, strings, tol = (data[k] for k in ('operator', 'values', 'tokens', 'tolerance'))
    if not data['measure'] or op not in OPERATORS:
        raise Unmeasurable('Missing measure or unsupported operator.')
    if data['severity'] not in ('error', 'warn'):
        raise Unmeasurable('Severity must be error or warn.')
    if not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol < 0:
        raise Unmeasurable('Tolerance must be finite and nonnegative.')
    if bool(nums) == bool(strings):
        raise Unmeasurable('Exactly one of values and tokens must be populated.')
    values = strings if strings else nums
    if op == 'between' and len(values) != 2 or op not in ('between', 'in') and len(values) != 1:
        raise Unmeasurable('Benchmark count does not match operator.')
    if strings and (op not in ('eq', 'ne', 'in') or tol != 0 or data['unit'] != '1'):
        raise Unmeasurable('Token comparisons require eq/ne/in, zero tolerance and unit 1.')
    if nums and not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in nums):
        raise Unmeasurable('Benchmarks must be finite numbers.')
    if op == 'between' and values[0] > values[1]:
        raise Unmeasurable('Between bounds must be ascending.')
    if data['unit'] not in ('m', 'm2', '1'):
        raise Unmeasurable('Only SI units m, m2 and 1 are supported; convert source units explicitly.')
    measure = data['measure']
    if measure.startswith('measured:') and measure not in MEASURE_UNITS:
        raise Unmeasurable('Unknown measured quantity: ' + measure)
    if measure in MEASURE_UNITS and data['unit'] != MEASURE_UNITS[measure]:
        raise Unmeasurable('Unit does not match measured quantity.')


def compare(measured, data):
    check_clause(data)
    values = data['tokens'] or data['values']
    if bool(data['tokens']) != isinstance(measured, str):
        raise Unmeasurable('Measured value and benchmarks have incompatible types.')
    op, tol = data['operator'], data['tolerance']
    equal = lambda a, b: a == b if isinstance(a, str) else abs(a-b) <= tol
    if op == 'eq': return equal(measured, values[0])
    if op == 'ne': return not equal(measured, values[0])
    if op == 'in': return any(equal(measured, v) for v in values)
    if op == 'between': return values[0]-tol <= measured <= values[1]+tol
    if op == 'lt': return measured < values[0]-tol
    if op == 'le': return measured <= values[0]+tol
    if op == 'gt': return measured > values[0]+tol
    if op == 'ge': return measured >= values[0]-tol
    raise Unmeasurable('Unsupported operator.')


def fingerprint(stage):
    """Hash composed inputs, not file mtimes; relocation and results are inert.

    Includes inherited properties, mesh points/topology, transforms, identities,
    classification, requirement benchmarks, property values and spatial datums.
    Ignores presentation-only colour, visibility, cameras and marked figures.
    """
    rows = [('metrics', UsdGeom.GetStageMetersPerUnit(stage), UsdGeom.GetStageUpAxis(stage))]
    for prim in stage.TraverseAll():
        if prim.GetCustomDataByKey('aecoCompliancePresentation') or prim.GetPath().HasPrefix('/Renders'):
            continue
        relevant = (prim.GetTypeName().startswith('Aeco') or has_api(prim, 'AecoElementAPI')
                    or has_api(prim, 'AecoDerivedGeometryAPI') or prim.IsA(UsdGeom.Xformable))
        if not relevant:
            continue
        props = []
        for prop in prim.GetProperties():
            name = prop.GetName()
            if name.startswith(('aeco:compliance:', 'primvars:')) or name in ('visibility', 'purpose', 'doubleSided'):
                continue
            if isinstance(prop, Usd.Attribute):
                props.append((name, str(prop.Get()), [(t, str(prop.Get(t))) for t in prop.GetTimeSamples()]))
            else:
                props.append((name, [str(p) for p in prop.GetTargets()]))
        rows.append((str(prim.GetPath()), prim.GetTypeName(), str(prim.GetInherits().GetAllDirectInherits()), props))
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def evaluate(stage):
    """Return element results, clause findings and scope findings without writes."""
    specs, candidates = specifications(stage), elements(stage)
    measurements = Measurements(stage)
    results, findings = [], []
    matched = {str(s.GetPath()): 0 for s in specs}
    for prim in sorted(candidates, key=lambda p: str(p.GetPath())):
        selected = [s for s in specs if applies(s, prim)]
        previously_checked = has_api(prim, 'AecoComplianceAPI')
        if not selected and not previously_checked:
            continue
        rows = []
        for spec in selected:
            matched[str(spec.GetPath())] += 1
            for req in requirements(spec):
                data = clause_data(req)
                row = {'clause': str(req.GetPath()), 'source': value(spec, 'aeco:spec:source', ''),
                       'measure': data['measure'], 'unit': data['unit'], 'severity': data['severity'],
                       'benchmarks': list(data['tokens'] or data['values']), 'operator': data['operator'],
                       'tolerance': data['tolerance']}
                try:
                    check_clause(data)
                    measured = measurements.get(prim, data['measure'])
                    ok = compare(measured, data)
                    row.update(measured=measured, status='pass' if ok else ('warn' if data['severity']=='warn' else 'fail'))
                    if not ok:
                        row['kind'] = 'unapprovedProduct' if data['measure'].startswith('aeco:type:') else 'misplacedDevice'
                except Unmeasurable as exc:
                    row.update(measured=None, status='fail', severity='error',
                               kind='missingBinding' if isinstance(exc, MissingBinding) else 'RequirementUnmeasurable', message=str(exc))
                rows.append(row)
                if row['status'] != 'pass':
                    findings.append({'path': str(prim.GetPath()), 'id': value(prim, 'aeco:id', ''), **row})
        states = {r['status'] for r in rows}
        status = 'fail' if 'fail' in states else 'warn' if 'warn' in states else 'pass' if rows else 'notApplicable'
        results.append({'path': str(prim.GetPath()), 'id': value(prim, 'aeco:id', ''), 'status': status,
                        'specifications': [str(s.GetPath()) for s in selected], 'clauses': rows})
    for spec in specs:
        if not matched[str(spec.GetPath())] and (value(spec, 'aeco:spec:appliesToClassification', []) or spec.GetRelationship('aeco:spec:appliesToTypes').GetTargets()):
            findings.append({'kind': 'missingDevice', 'path': str(spec.GetPath()), 'severity': 'error',
                             'message': 'No element matches this specification applicability.'})
    return {'results': results, 'findings': findings}


def report_line(row):
    measured = row['measured']
    rendered = f'{measured:.6g}' if isinstance(measured, (float, int)) else str(measured)
    return (f"{row['clause']} | {row['source']} | {row['measure']} = {rendered} {row['unit']} | "
            f"{row['operator']} {row['benchmarks']} +/- {row['tolerance']:.6g} | {row['status']}" +
            (f" | {row['message']}" if 'message' in row else ''))


def write_results(stage, output):
    """Write a separate, deterministic result layer and compose it strongest."""
    output = Path(output).resolve()
    source_paths = {Path(l.realPath).resolve() for l in stage.GetUsedLayers() if l.realPath}
    existing = Sdf.Layer.Find(str(output))
    if output in source_paths and not (existing and existing.customLayerData.get('aecoComplianceRole') == 'result'):
        raise ValueError('Result output must not overwrite a source layer.')
    # A previous result is excluded from authority and replaced as a whole.
    result = evaluate(stage)
    digest = fingerprint(stage)
    layer = existing or Sdf.Layer.CreateNew(str(output))
    layer.Clear()
    layer.customLayerData = {'aecoComplianceRole': 'result', 'inputFingerprint': digest, 'evaluatorVersion': '0.1.0'}
    result_stage = Usd.Stage.Open(layer)
    add_fallbacks(result_stage)
    for row in result['results']:
        prim = result_stage.OverridePrim(row['path'])
        prim.AddAppliedSchema('AecoComplianceAPI')
        prim.CreateRelationship('aeco:compliance:specifications', custom=False).SetTargets(row['specifications'])
        attr(prim, 'aeco:compliance:status', Sdf.ValueTypeNames.Token, row['status'])
        attr(prim, 'aeco:compliance:report', Sdf.ValueTypeNames.String, '\n'.join(report_line(r) for r in row['clauses']))
    layer.Save()
    root = stage.GetRootLayer()
    if str(output) not in root.subLayerPaths and not any(l == layer for l in stage.GetLayerStack()):
        root.subLayerPaths.insert(0, str(output))
    return result


def stale_paths(stage):
    expected = fingerprint(stage)
    stale = []
    for prim in elements(stage):
        status = prim.GetAttribute('aeco:compliance:status')
        if not status or status.Get() in (None, 'unchecked'):
            continue
        stack = status.GetPropertyStack()
        if not stack or stack[0].layer.customLayerData.get('inputFingerprint') != expected:
            stale.append(str(prim.GetPath()))
    return stale
