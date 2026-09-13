# Changelog

## 0.2.0

- Fingerprint authored input opinions after USD composition, including authored
  API applications, defaults, samples, blocks and relationship targets. Exclude
  schema fallbacks and expanded built-in APIs; keep result and presentation
  exclusions. Layer identifiers and versions remain outside the digest.
- Preserve the property namespaces and result shape. Migrate the example's
  fingerprint and evaluator-version metadata while requiring every committed
  result opinion to remain unchanged; add verification without recomputation.
- Test fresh-process equivalence with no family plugins, compliance alone,
  and core + compliance + axis, plus explicit fallback values, opinion removal,
  blocks, time samples, inheritance and stale reader-height results.
- Keep the exact data-centre v0.4.8 pin and source hashes. Import core validators
  from the configured source checkout without requiring PYTHONPATH.
- Verify 49 checks, 0 failed; structure 29/0; 51 pytest tests. Committed results
  verify with 0, 1, 3 and 11 family schema plugins without recomputation.
  Keep the standalone crate, six other editable layers and five images
  byte-identical. The single Nix attempt stopped during input resolution;
  packaging remains not proven. See docs/validation.md for the receipt.

## 0.1.3

- public re-pin: usdaeco-toolchain v0.3.10, usdaeco-core v0.9.5,
  usdaeco-axis v0.1.5, usdaeco-datacentre v0.4.8. Record the checked
  revisions alongside public release tags; requirement ranges are unchanged.
- Bump package and plugin metadata; rebuild the schema and republish the iris
  example through the documented runner.
- Keep the crate, seven editable layers, source layers and findings byte-identical;
  retain five committed images after fresh sampled renders. Result changes are
  provenance-only. Keep unchanged evaluator and presentation producer stamps.
- Honour CORE_PLUGIN_DIR in source tests and document the tagged source plugin
  so stale installed metadata cannot substitute for the checked core version.
- Verify 48 checks, 0 failed, 0 not run; structure 29/0 and 40 pytest tests.
  The single offline Nix attempt evaluated five macOS derivations and two apps,
  then was interrupted during the uncached dependency build; completion is not
  proven. See docs/validation.md for measured evidence and deviations.

## 0.1.2

- Publish a stock facility render of the office-link door, failing reader and
  illustrative height envelopes. Colour all eleven original readers by verdict;
  retain the elevation and plan diagrams and add a ground-floor facility view.
- Keep the full pinned facility and the unchanged 10 pass / 1 fail findings,
  including both named height clauses at 1.65 m.
- Pin toolchain v0.3.8 and data centre v0.4.6; use the portable inputs/source
  alias and retain the other dependency pins.
- public names → github.com/criad-com.
- Verify both directory layouts: 48 checks, 0 failed; structure 29/0; 40 pytest
  tests; ResultStale PASS. The single Nix
  attempt failed at upstream input resolution; packaging remains not proven.

## 0.1.1

- Re-pin to train aeco-0.7.0: core v0.9.2, axis v0.1.2, toolchain v0.3.5
  and data centre v0.4.5; retain requirement ranges.
- Refresh the example's pin manifest and source receipt. The iris source layers,
  findings and standalone crate remain byte-identical; retain the authored layers
  and committed renders.
- Verify 44 checks, 0 failed, 0 not run; structure 28/0 under toolchain v0.3.5;
  40 pytest tests. One offline Nix attempt cannot resolve the uncached upstream
  toolchain input; Nix packaging remains not proven.

## 0.1.0

- Add specification and requirement records and derived compliance results.
- Convert three illustrative YAML specifications into authority-ordered USD layers.
- Measure body height, door envelope offset, approach side and conservative clear area.
- Register seven Python UsdValidation rules, including staleness and four finding kinds.
- Publish the iris example: ten passing readers, one failing reader at 1.65 m,
  two failed height clauses, door elevation, plan and a standalone USD result.
- Document conceptual IDS/IFC mapping, approximation limits and reproducible gates.
