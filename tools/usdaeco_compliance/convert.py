"""Convert the small illustrative YAML dialect to three authority layers."""
import json
from pathlib import Path
import yaml
from pxr import Sdf, Usd, UsdGeom
from .model import attr, add_fallbacks, value, elements, classified
from .evaluator import check_clause

MEASURES = {'MountingHeight': 'measured:centreHeightAboveFloor', 'BottomHeight': 'measured:bottomHeightAboveFloor',
            'DoorEdgeOffset': 'measured:distanceToDoorLeafEdge', 'Side': 'measured:sideOfDoor',
            'ClearFloorArea': 'measured:clearFloorArea'}
SOURCES = [('accessibility', '01-accessibility.usda'), ('employer-security', '02-employer-security.usda'),
           ('reader-datasheet', '03-reader-datasheet.usda')]


def convert_document(data, output, *, name, type_paths=()):
    if data.get('illustrative') is not True:
        raise ValueError('This converter accepts illustrative data only; verified regulatory ingestion is outside v0.1.')
    if data['kind'] not in ('regulation', 'specification', 'datasheet', 'standard'):
        raise ValueError('Unknown specification kind.')
    applicability = data.get('appliesTo', {})
    if applicability.get('types') and not type_paths:
        raise ValueError('Source catalog type selectors did not resolve.')
    parsed = []
    for i, source in enumerate(data['requirements'], 1):
        vals = source.get('values', [])
        is_tokens = bool(vals) and all(isinstance(x, str) for x in vals)
        clause = dict(measure=MEASURES.get(source['measure'], source['measure']), operator=source['operator'],
                      values=[] if is_tokens else vals, tokens=vals if is_tokens else [], unit=source.get('unit', 'm'),
                      tolerance=source.get('tolerance', 0), severity={'hard':'error','advisory':'warn'}.get(source['severity'],source['severity']),
                      rationale=source.get('rationale', ''))
        check_clause(clause)
        parsed.append((f'Clause{i:02d}', clause))
    stage = Usd.Stage.CreateInMemory()
    stage.SetMetadata('metersPerUnit', 1.0)
    stage.SetMetadata('upAxis', 'Z')
    add_fallbacks(stage)
    stage.GetRootLayer().customLayerData = {'illustrative': True, 'source': name+'.yaml'}
    root = stage.DefinePrim('/Specifications', 'Scope')
    stage.SetDefaultPrim(root)
    spec = stage.DefinePrim('/Specifications/'+name.replace('-', '_'), 'AecoSpecification')
    attr(spec, 'aeco:spec:title', Sdf.ValueTypeNames.String, data['title'])
    attr(spec, 'aeco:spec:source', Sdf.ValueTypeNames.String, data['source'])
    attr(spec, 'aeco:spec:kind', Sdf.ValueTypeNames.Token, data['kind'])
    codes = [c if ':' in c else 'ifc:'+c for c in applicability.get('classification', [])]
    attr(spec, 'aeco:spec:appliesToClassification', Sdf.ValueTypeNames.StringArray, codes)
    spec.CreateRelationship('aeco:spec:appliesToTypes', custom=False).SetTargets(type_paths)
    for name, clause in parsed:
        req = stage.DefinePrim(spec.GetPath().AppendChild(name), 'AecoRequirement')
        for key, data_value in clause.items():
            typ = {'measure':Sdf.ValueTypeNames.String,'operator':Sdf.ValueTypeNames.Token,
                   'values':Sdf.ValueTypeNames.DoubleArray,'tokens':Sdf.ValueTypeNames.StringArray,
                   'unit':Sdf.ValueTypeNames.String,'tolerance':Sdf.ValueTypeNames.Double,
                   'severity':Sdf.ValueTypeNames.Token,'rationale':Sdf.ValueTypeNames.String}[key]
            attr(req, 'aeco:req:'+key, typ, data_value)
    stage.GetRootLayer().Export(str(output))
    return output


def convert_sources(source_dir, output_dir, stage, type_map):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stem, filename in SOURCES:
        data = yaml.safe_load((Path(source_dir)/(stem+'.yaml')).read_text())
        paths = []
        for source_type in data.get('appliesTo', {}).get('types', []):
            if source_type not in type_map:
                raise ValueError('Unresolved source type selector: ' + source_type)
            path = Sdf.Path(type_map[source_type])
            target = stage.GetPrimAtPath(path)
            if not target or not target.IsAbstract():
                raise ValueError('Type selector must map to a catalog class prim.')
            paths.append(path)
        convert_document(data, output_dir/filename, name=stem, type_paths=paths)
