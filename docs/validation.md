# Validation evidence for 0.1.3

The checked source tags and peeled forge revisions are recorded in
[dependencies.json](../dependencies.json): core v0.9.5, axis v0.1.5,
toolchain v0.3.10 and data centre v0.4.8. All four flake inputs use public
release tags. Requirement ranges remain unchanged. The toolchain transitively
pins the public build kit v0.4.0.

The schema rebuild and `usdGenSchema --validate` pass with OpenUSD 26.8.
Use the committed core source plugin as documented in the
[README](../README.md#build-and-check). Tests respect `CORE_PLUGIN_DIR` and
run directly from source without an installed package or setuptools.

| Acceptance | Measured evidence |
|---|---|
| Release metadata | Package, source package and plugin all 0.1.3 |
| Pins | Four matching public tag URLs and four checked revisions |
| Iris result | 11 readers; 10 pass, 1 fail; two named height clauses at 1.65 m |
| Full facility | All 12,266 source prims preserved, including identities, transforms, points, topology and extents |
| Standalone result | 12,480 prims; 3,884,764 bytes across the result directory |
| Schema and publication | Rebuilt schema; republished through `examples/datacentre/run.py --publish` |
| Reproduction | One crate and seven editable layers byte-identical to 0.1.2; source layers and expected findings unchanged |
| Renders | Five fresh 1280 × 800 non-blank PNGs; committed images and hashes retained |
| Gate | 48 checks, 0 failed, 0 not run |
| Structure | 29 checks, 0 failed, including strengthened S05 and plugin-free S27/S28 |
| Tests | 40 passed from source |
| Core validation | Eight rules loaded; 0 errors, 2 inherited classification warnings |
| Example runner | 73.314 s within its 180 s budget |

[Current receipt](public-repin-verification.json) records the gate, pin matrix,
byte comparisons and fresh render hashes. The
[previous two-layout receipt](relocation-verification.json) remains historical
0.1.2 evidence; its old pins do not describe this release.

The final gate requires all eight core validators and seven compliance rules.
It verifies the standalone result in a fresh plugin-free process, checks a fresh
stock Embree render, reproduces findings and layers, preserves all 2,954 element
identities and transforms when the hard-source layers are muted, and exercises
the seeded measurement and validation tests.

## Reproduction

Configure the environment from the README using the exact dependency tags,
then run:

```sh
export PYTHONDONTWRITEBYTECODE=1
bash build.sh
env -u PYTHONPATH python examples/datacentre/run.py --publish
env -u PYTHONPATH PYTHONPATH="$CORE_DIR:$PWD" python check.py
```

The ordinary runner writes to ignored `out/`. Compare the freshly published
crate and editable layers with the previous release before retaining existing
PNG bytes and their manifest hashes. Fresh PNG hashes are evidence of the new
render; S28 deliberately does not compare sampled pixels across runs.

## Deviations

- The single `nix flake check --offline --no-write-lock-file` attempt used
  four local overrides for toolchain, core, axis and data centre. It evaluated
  five macOS derivations and both apps, then began a 1,051-dependency build
  graph. The attempt was interrupted to respect the restricted network scope;
  exit 1 reports interruption. Nix build completion and Linux evaluation are
  **not proven**. Direct public GitHub resolution remains for review; no retry
  or lockfile was committed.
- The installed core plugin reported 0.9.4 although its checkout was tagged
  v0.9.5. A preliminary gate was stopped; the final rebuild and gate use the
  committed 0.9.5 source plugin. No dependency checkout was modified.
- Fresh renders differ through sampling: mean absolute RGB channel differences
  against the committed PNGs range from 0.027054 to 0.204554 on the 0–255 scale.
  The five committed PNGs and their hashes are retained after fresh render
  validation. The crate, all seven editable layers and source geometry are
  byte-identical. Result changes are limited to pin provenance and notice hashes.
- Evaluator and presentation producer stamps retain their existing values
  because those implementations are unchanged. Datacentre 0.4.7 and 0.4.8
  explicitly retain the published stage bytes; core 0.9.5 republishes unchanged
  geometry, and toolchain 0.3.9/0.3.10 strengthen version and tag checks.
- Requirement values remain illustrative; existing measurement and export
  limitations are documented in [measurements](measurements.md) and
  [mapping](mapping.md).

Remaining work is review, public resolution verification and release.
