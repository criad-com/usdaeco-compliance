# Validation evidence for 0.1.2

Checks use OpenUSD 26.8 and clean exports of the exact dependency tags:
core v0.9.2, axis v0.1.2, toolchain v0.3.8 and data centre v0.4.6.
The latter retains the iris publication generated at v0.4.2. Source layer
hashes and expected findings are unchanged from the previous release.
The schema rebuild and fresh `usdGenSchema --validate` pass.

| Acceptance | Measured evidence |
|---|---|
| Iris result | 11 readers; 10 pass, 1 fail |
| Clause detail | `/Specifications/accessibility/Clause01` and `/Specifications/employer_security/Clause01` both report 1.65 m on the office-link reader |
| Full facility | All 12,266 source prims preserved, including identity, transforms, mesh points, topology and extents |
| Reader presentation | 11 original bodies coloured by verdict; three illustrative height envelopes per reader |
| Vanilla view | Actual facility door region; failing red reader above the two hard bands; diagram sheet outside the camera view |
| Diagrams | Original labelled plan and door elevation retained in `renders/` and the separate diagram layer |
| Standalone result | 12,480 prims; 3,884,764 bytes including own layers and vanilla PNG |
| Gate | 48 checks, 0 failed, 0 not run |
| Structure | 29 checks, 0 failed, including S25, S27, S28 and S29 |
| Tests | 40 passed from source, without an installed package |
| Validators | Seven compliance rules and all eight core rules imported and loaded |
| Core validation | 0 errors, 2 inherited classification warnings |
| Representation marks | 186 symbols: 142 diagram shapes and 44 reader envelope/status meshes |
| Authority audit | Both hard-source layers muted: 11 pass; all 2,954 element identities and transforms unchanged |
| Renders | Four 1280 × 800 images; largest 250,836 bytes; vanilla PNG 140,549 bytes |
| Fresh result / ResultStale | PASS in both working and relocated layouts; each runner within its 180 s budget |

Both full gates report **48 checks, 0 failed, 0 not run**, structure **29/0**
and **40 passed** in pytest. The relocated consumer was a complete Git archive,
with dependencies independently copied into a different directory hierarchy;
it began without transient outputs or a source alias.
[Machine-readable evidence](relocation-verification.json) records every check
and the source hashes for both layouts.

The full gate checks every source prim against the pinned stage, original
reader colours, envelope presence and camera framing. The independent stock
render proof uses the flattened crate with family plugin paths removed.
The published vanilla image, facility view and preserved diagrams were
visually inspected. Hash inventories are in the example manifest.

## Reproduction

Configure the environment as in [README](../README.md#build-and-check), using
the exact tags above. `CORE_PLUGIN_DIR` may point to the exported core's
`usdAeco/` source plugin instead of an installed plugin directory.

```sh
export PYTHONDONTWRITEBYTECODE=1
env -u PYTHONPATH PYTHONPATH="$CORE_DIR:$PWD" python check.py
```

For a second layout, export the consumer into a deeper directory and copy the
pinned dependencies into a separate release directory. Start without `out/`
or `inputs/source`, update the environment paths, and run the same gate.
The runner recreates `inputs/source`; the committed crate needs no source link.

## Deviations

- S29 adds a rule to the original 28-rule skeleton: the current lint reports
  **29/0**. The source has **12,266** `TraverseAll` prims, excluding instance
  prototypes, rather than the anticipated 12,358. The gate compares every source
  prim against the result; the complete pinned stage remains composed.
- The vanilla camera uses the actual office-link door region to make the high
  reader and envelopes legible. The separate `facility` view shows all eleven
  locations. Its 2.4 m camera clipping plane exposes the ground floor without
  deleting or altering source geometry. Status crosses and envelope widths are
  illustrative display symbols; measured reader geometry is unchanged.
- One `nix flake check --offline --no-write-lock-file` attempt with local direct
  input overrides failed resolving the nested public `aeco-toolchain` revision
  with HTTP 404. Nix packaging and platform evaluation are **not proven**;
  no second attempt was made.
- All example requirement values remain illustrative. Door distance uses the
  combined frame/leaf envelope, side uses the exported approach normal, and
  height uses the containing level datum. Exact leaf distance, optical-centre
  identification and nonrectangular clear area remain outside v0.1. No IDS XML
  or IFC constraint exporter is claimed.

Remaining work is review and merge/release.
