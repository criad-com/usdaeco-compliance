"""Python UsdValidation plugin over the same evaluator used by the CLI."""
from pathlib import Path
import sys
from pxr import UsdValidation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from usdaeco_compliance.evaluator import evaluate, stale_paths, clause_data, check_clause
from usdaeco_compliance.measure import Measurements, Unmeasurable
from usdaeco_compliance.model import value, elements, applies
from . import validatorTokens as tokens


def error(stage, path, name, message, severity='error'):
    kind = UsdValidation.ValidationErrorType.Warn if severity == 'warn' else UsdValidation.ValidationErrorType.Error
    return UsdValidation.ValidationError(name, kind, [UsdValidation.ValidationErrorSite(stage, path)], message)


def requirement_task(prim, time_range):
    data = clause_data(prim)
    stage = prim.GetStage()
    try:
        if prim.GetParent().GetTypeName() != 'AecoSpecification':
            raise Unmeasurable('A requirement must be a direct child of a specification.')
        check_clause(data)
        measurement = Measurements(stage)
        for candidate in elements(stage):
            if applies(prim.GetParent(), candidate):
                measurement.get(candidate, data['measure'])
    except Unmeasurable as exc:
        return [error(stage, prim.GetPath(), tokens.REQUIREMENT_UNMEASURABLE, str(exc))]
    return []


def applicability_task(prim, time_range):
    codes = value(prim, 'aeco:spec:appliesToClassification', [])
    types = prim.GetRelationship('aeco:spec:appliesToTypes').GetTargets()
    if not codes and not types:
        return [error(prim.GetStage(), prim.GetPath(), tokens.SPECIFICATION_WITHOUT_APPLICABILITY,
                      'Specification has neither classification nor catalog type applicability.')]
    return []


def stale_task(stage, time_range):
    return [error(stage, path, tokens.COMPLIANCE_STALE, 'Composed inputs differ from the result-layer fingerprint; rerun the evaluator.')
            for path in stale_paths(stage)]


def finding_task(kind, name):
    def task(stage, time_range):
        result = []
        for row in evaluate(stage)['findings']:
            if row['kind'] == kind:
                text = row.get('message') or (f"{row['clause']} | {row['source']} | {row['measure']} = "
                                              f"{row['measured']:.6g} {row['unit']}" if isinstance(row.get('measured'), (float,int)) else
                                              f"{row['clause']} | {row['source']} | {row['measure']} = {row.get('measured')} {row['unit']}")
                result.append(error(stage, row['path'], name, text, row['severity']))
        return result
    return task


_registry = UsdValidation.ValidationRegistry()
_registry.RegisterPluginPrimValidator(tokens.REQUIREMENT_UNMEASURABLE_CHECKER, requirement_task)
_registry.RegisterPluginPrimValidator(tokens.SPECIFICATION_WITHOUT_APPLICABILITY_CHECKER, applicability_task)
_registry.RegisterPluginStageValidator(tokens.COMPLIANCE_STALE_CHECKER, stale_task)
_registry.RegisterPluginStageValidator(tokens.MISSING_DEVICE_CHECKER, finding_task('missingDevice', tokens.MISSING_DEVICE))
_registry.RegisterPluginStageValidator(tokens.MISPLACED_DEVICE_CHECKER, finding_task('misplacedDevice', tokens.MISPLACED_DEVICE))
_registry.RegisterPluginStageValidator(tokens.UNAPPROVED_PRODUCT_CHECKER, finding_task('unapprovedProduct', tokens.UNAPPROVED_PRODUCT))
_registry.RegisterPluginStageValidator(tokens.MISSING_BINDING_CHECKER, finding_task('missingBinding', tokens.MISSING_BINDING))
