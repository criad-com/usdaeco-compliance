"""aeco-compliance check: input stage to derived results and a JSON report."""
import argparse
import json
from pathlib import Path
from pxr import Usd
from .evaluator import write_results
from .model import specifications
from .convert import convert_sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check')
    check.add_argument('stage', type=Path)
    check.add_argument('--output', type=Path, default=Path('compliance.usda'))
    check.add_argument('--report', type=Path, default=Path('findings.json'))
    convert = commands.add_parser('convert')
    convert.add_argument('source_dir', type=Path)
    convert.add_argument('--stage', type=Path, required=True)
    convert.add_argument('--type-map', type=Path, required=True)
    convert.add_argument('--output-dir', type=Path, required=True)
    convert.add_argument('--study-root', help='Study prim path; otherwise use data, AECO_STUDY_ROOT, or /.')
    args = parser.parse_args(argv)
    stage = Usd.Stage.Open(str(args.stage))
    if not stage or stage.GetCompositionErrors():
        parser.error('Input stage does not compose.')
    if args.command == 'convert':
        try:
            convert_sources(args.source_dir, args.output_dir, stage, json.loads(args.type_map.read_text()),
                            study_root=args.study_root)
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    if not specifications(stage):
        parser.error('No active AecoSpecification records; compose requirement layers before checking.')
    source_paths = {Path(layer.realPath).resolve() for layer in stage.GetUsedLayers() if layer.realPath}
    if args.report.resolve() in source_paths or args.report.resolve() == args.output.resolve():
        parser.error('Report output must differ from USD inputs and result output.')
    result = write_results(stage, args.output)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
    counts = {status: sum(r['status']==status for r in result['results']) for status in ('pass','fail','warn','notApplicable')}
    print(', '.join(f'{n} {s}' for s,n in counts.items()))
    return int(any(f.get('severity')=='error' for f in result['findings']))


if __name__ == '__main__':
    raise SystemExit(main())
