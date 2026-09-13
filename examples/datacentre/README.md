# Iris reader compliance

Inputs are the pinned data-centre v0.4.8 `iris` stage and three committed
illustrative YAML specifications. `type-map.json` resolves the source catalog
selector to the catalog class path. The generated USD layers are strongest-first:
`01-accessibility.usda`, `02-employer-security.usda`, `03-reader-datasheet.usda`.

After configuring the environment in the repository README, run:

```sh
env -u PYTHONPATH python examples/datacentre/run.py --publish
```

Expected: **11 readers, 10 pass, 1 fail**. The office-link body centre is **1.65 m**,
outside both hard height bands. The two clause paths and measured values appear
in `expected/findings.json` and the result attributes. General stage counts come
from `dc.manifest.json`; they are not constants in the evaluator.

Open `result/example.usdc` in stock `usdview`. The entire pinned facility is
composed. The cameras are:

| Camera | View |
|---|---|
| `/Renders/overview` | The actual office-link door region, failing red reader and illustrative height envelopes; used for `result/vanilla.png` |
| `/Renders/facility` | The ground-floor facility with all eleven reader locations, clipped at 2.4 m by the camera |
| `/Renders/elevation` | Preserved door elevation diagram with the three labelled bands |
| `/Renders/plan` | Preserved labelled plan diagram with all eleven statuses |

The presentation layer colours the original ten passing reader bodies green
and the failing body red. Enlarged crosses locate their measured centres.
Envelope mesh bars show accessibility (blue, 0.90–1.20 m), employer (green,
1.05–1.20 m) and datasheet (amber, 1.00–1.70 m) bands; their heights are read
from the composed clauses. These illustrative symbols are separate from the
measured bodies. The standalone vanilla render uses stock USD and Embree.

![Office-link door and failing reader](result/vanilla.png)

![All eleven locations in the facility](renders/facility.png)

Geometry and identity in the source remain unchanged. `result/layers/` preserves
`compliance.usda`, `presentation.usda` and `diagrams.usda` separately alongside
the inputs. `run.py` creates the ignored `inputs/source` alias pointing at
`AECO_DATACENTRE_ROOT`; no fixed sibling layout is needed. The v0.4.8 release
retains the iris publication generated at v0.4.2, with unchanged source hashes.

`out/report.json` has every measured clause, including passing checks. The
ordinary runner writes only `out/`; `--publish` refreshes committed results and
images after comparing expected findings. Re-run the README's converter command
to regenerate the input layers; it never writes into the data-centre checkout.

Version 0.2.0 replaces the runtime-dependent fingerprint. For an older committed
result, run the one-time migration in the configured environment:

```sh
env -u PYTHONPATH python examples/datacentre/run.py --migrate-fingerprint --publish
```

Run from the repository root. Migration evaluates the same pinned inputs and
compares every result opinion with the archive before publishing; only the
fingerprint and evaluator-version metadata may differ. A changed verdict or
report aborts migration. The committed results in this release are migrated.
To verify them without evaluating clauses, writing outputs or rendering:

```sh
env -u PYTHONPATH python examples/datacentre/run.py --verify-results
```

This reads the archived layers over the v0.4.8 iris source, checks the published
source hashes and requires **11 checked, 0 stale**. The same verification runs
with no family plugins, compliance alone, and core + compliance + axis in the
full test suite. Use the archived layers for freshness checks: flattening a
stage can bake schema defaults and loses per-layer result provenance.

For the suite layout, use the same environment with:

```sh
export AECO_STUDY_ROOT=/Studies/compliance
env -u PYTHONPATH python examples/datacentre/run.py --output-dir out/study
```

This writes a composable study under `out/study/`: specifications are under
`/Studies/compliance/Specifications`, drawing sheets under
`/Studies/compliance/ComplianceFigures`, and cameras under
`/Renders/compliance`. Result opinions and reader envelopes remain on the
building. Input USD layers are copied before their namespaces change; their
authority order and project-catalog targets are preserved. The committed inputs,
expected findings, crate and images are unchanged. The configured runner writes
USD and JSON for suite composition; it does not render or publish the legacy
example. `--study-root` overrides the environment setting.

The saved layers can be checked without setting `AECO_STUDY_ROOT`. Tools follow
authored specification paths and result targets. Moving those prim paths makes
old fingerprints stale, so the hook evaluates after relocation. This preserves
the v0.2.0 authored-opinion hash and its existing default-layout digest.
Set `AECO_DATACENTRE_STAGE` to a different delivery's `dist/full/dc.usda` for
an explicit compatibility probe. The integration tests additionally use
`AECO_DATACENTRE_SUITE_ROOT` for the exact v0.5.2 suite fixture; the historical
publication remains pinned to v0.4.8.

All limits are illustrative. The door-edge check measures the combined frame
and leaf envelope; the precise leaf edge is not proven. See
[measurement limits](../../docs/measurements.md) and [validation](../../docs/validation.md).
