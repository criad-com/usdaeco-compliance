# Changelog

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
