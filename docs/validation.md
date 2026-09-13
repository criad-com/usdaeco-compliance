# Validation evidence for 0.2.1

The release keeps the existing dependency pins and the committed v0.4.8 iris
publication. The additional suite compatibility fixture is the exact data-centre
v0.5.2 `dist/full/dc.usda`. Source/package/plugin metadata reports 0.2.1;
`evaluatorVersion` stays 0.2.0 because the authored-opinion algorithm is unchanged.

| Acceptance | Measured evidence |
|---|---|
| Contract gate | 49 checks, 0 failed, 0 not run |
| Structure | 29 checks, 0 failed, including sanitized-content and plugin-free checks |
| Pytest | 64 passed, 0 skipped; 65.26 s |
| Schema | Rebuilt successfully; `usdGenSchema --validate` clean |
| Configured deliveries | v0.4.8 iris and v0.5.2 full: 10 pass, 1 fail, two findings, 0 stale |
| Catalog | All 65 project-catalog prims retained on each delivery; no root catalog |
| Stage roots | Project, `/Studies` (Scope), `/Renders`; four cameras under `/Renders/compliance` |
| Default artifacts | 24 committed input/publication files byte-identical; every manifest artifact hash matches |
| Committed verification | 11 checked, 0 stale without recomputation; original v0.2.0 digest retained |
| Default reproduction | Shared runner passed in 58.759 s / 180 s; four non-blank renders and stock vanilla render |

The [study-root receipt](study-root-verification.json) records source hashes,
root paths, cameras and fingerprints for both configured deliveries.

The non-default-root tests exercise the converter and its CLI override, the
example hook, project-catalog relationships, result targets, both presentation
writers, validators and a plugin-free CLI recheck on both releases. They compare
all verdicts and measurements against the default layout, check that the only
root prims are the project, plain `Studies` Scope and `Renders`, and verify
unchanged source files, catalog classes and building transforms. Reopening with
an unrelated environment setting still follows the authored specification paths.
Another library's camera layer with the same filename remains untouched.

Configure the README environment, selecting v0.4.8 for `AECO_DATACENTRE_ROOT`
and v0.5.2 for `AECO_DATACENTRE_SUITE_ROOT`, then run:

```sh
unset AECO_STUDY_ROOT AECO_DATACENTRE_STAGE
bash build.sh
env -u PYTHONPATH python check.py
env -u PYTHONPATH python -m pytest -q
env -u PYTHONPATH python examples/datacentre/run.py --verify-results
AECO_STUDY_ROOT=/Studies/compliance env -u PYTHONPATH python examples/datacentre/run.py --output-dir out/study
```

The suite fixture can also be selected explicitly with `AECO_DATACENTRE_STAGE`
pointing at its `dist/full/dc.usda`. The tests assert fixture release metadata;
without the optional suite fixture they skip its two integration cases. Full
release validation supplies both fixtures and permits no skips.

## Deviations for 0.2.1

- Study prim relocation is deliberately fingerprint-dependent. The unchanged
  v0.2.0 algorithm hashes prim paths; moving specifications requires rechecking.
  This preserves the default publication's existing digest and all artifact
  bytes. The hook relocates first and then evaluates. File relocation alone
  remains fingerprint-independent.
- The v0.5.2 full delivery is an additional compatibility fixture, not a re-pin
  of the historical publication. It is supplied externally, without modifying
  a sibling checkout or adding another kind-library dependency.
- The single offline `nix flake check --no-write-lock-file` attempt resolved
  public inputs and evaluated five macOS derivations and two apps. It was
  interrupted during uncached dependency builds. Nix packaging is not proven;
  no retry or lockfile is included.
- Configured example runs emit composable USD layers and JSON under the selected
  output directory. The legacy shared rendering/publication harness continues
  to run for the default root; configured runs do not replace its publication.

## Historical validation evidence for 0.2.0

The exact dependency pins remain core v0.9.5, axis v0.1.5, toolchain v0.3.10
and data centre v0.4.8. All flake URLs retain their public release tags.
The schema rebuild and `usdGenSchema --validate` pass with OpenUSD 26.8.
The package, source package and plugin metadata all report 0.2.0.

| Acceptance | Measured evidence |
|---|---|
| Gate | 49 checks, 0 failed, 0 not run |
| Structure | 29 checks, 0 failed, including term sweep and plugin-free S27/S28 |
| Tests | 51 passed, 0 skipped, from source; 15.50 s |
| Plugin independence | Fresh processes with 0, 1 and 3 family schema plugins; identical hashes for absent, fallback-equal, sampled and blocked opinions |
| Built-in APIs | Schema-provided collection API excluded; explicitly authoring the same API changes the hash |
| Opinion edits | Authoring a fallback-equal value, removing it, blocking, empty targets, inherited values and sample edits covered |
| Height staleness | Reader moved to 1.65 m retains its old pass opinion and reports ComplianceStale until rechecked |
| Committed verification | 11 checked, 0 stale with each plugin set; evaluator and writer replaced by failing sentinels |
| Larger plugin set | 11 family schema plugins, including repeat; identical hash, 11 checked, 0 stale, no recomputation |
| Migration | All result opinions unchanged; only inputFingerprint and evaluatorVersion metadata updated |
| Iris findings | 11 readers; 10 pass, 1 fail; two height clauses measure 1.65 m |
| Source preservation | All 12,266 source prims preserved, including identities, transforms and mesh geometry |
| Standalone result | 12,480 prims; 3,884,764 bytes across result/ |
| Reproduction | Crate and six editable layers byte-identical to 0.1.3; migrated result layer reproduces exactly |
| Source provenance | Exact v0.4.8 pin, source hashes and expected findings unchanged |
| Rendering | Five fresh non-blank 1280 × 800 PNGs; committed image bytes and hashes retained |
| Core validators | Eight rules loaded; 0 errors, 2 inherited classification warnings |
| Muting | 2,954 element identities/transforms preserved; both hard-source layers muted gives 11 pass |
| Example runner | 56.006 s within its 180 s budget |

[The receipt](fingerprint-verification.json) records both fingerprints, the
plugin matrix, publication render hashes and the unchanged result inventory.
The [previous pin receipt](public-repin-verification.json) remains historical
0.1.3 evidence.

The larger probe registers core, compliance, axis, build-up, wall, pipe, sync,
CCTV, clash, plan and repeat codeless schemas before opening the stage. This
checks fingerprint independence; it does not claim to run every library's
validators. Compliance-only and plugin-free probes explicitly assert the absence
of the other schema definitions. `GetAllAuthoredMetadata()` excludes built-in
API fallbacks that `GetMetadata('apiSchemas')` would otherwise return.

## Reproduction

Configure the source checkouts and Python environment from the README, with
`AECO_DATACENTRE_ROOT` naming v0.4.8, then run from the repository root:

```sh
export PYTHONDONTWRITEBYTECODE=1
bash build.sh
env -u PYTHONPATH python examples/datacentre/run.py --verify-results
env -u PYTHONPATH python check.py
env -u PYTHONPATH python -m pytest -q
```

The full gate supplies the pinned source for all 51 tests. Unit-only pytest
invocations without `AECO_DATACENTRE_ROOT` skip the facility verification;
the gate requires it and has no skip path. The new example verification mode
checks the archived source/result composition without evaluating, writing or
rendering. The full gate additionally regenerates outputs in ignored `out/`
and compares them against the committed publication.

For a pre-0.2.0 result, `run.py --migrate-fingerprint --publish` performs the
one-time migration, refusing publication unless every old result opinion agrees
with the evaluated pinned inputs. The committed result is already migrated.
The algorithm deliberately omits layer identifiers, versions and timestamps,
as before. See [fingerprint coverage](usecase.md#5-validation).

## Deviations

- The available data checkout is v0.4.9, while this example pins v0.4.8.
  Validation used an isolated archive of the exact v0.4.8 tag containing its
  release metadata and iris publication. No sibling checkout was changed;
  the harness recorded `source.mode = pinned` and unchanged source hashes.
- The installed core plugin reports 0.9.4. The checked v0.9.5 source plugin
  was selected explicitly, as documented in the README; no sibling was rebuilt.
- Axis supplies the three-plugin test because it is already an exact test pin.
  Repeat is included in the additional eleven-plugin probe; no new dependency
  between kind libraries is introduced.
- The single offline `nix flake check --no-write-lock-file` attempt used an
  external registry and five local input overrides. Nix rejected a symlinked
  parent of the temporary source export during input resolution (exit 1),
  before evaluation or building. Nix packaging is **not proven**. No retry or
  lockfile was committed.
- Fresh Embree renders passed image checks, but sampled pixels are not a
  cross-run identity contract. The five previously committed PNGs and their
  hashes are retained; publication changes only the result metadata and its
  manifest hash. The standalone crate remains byte-identical.
- The fingerprint changes by construction, so migration evaluates once to
  establish unchanged result opinions. All subsequent committed verifications
  run without recomputation. Flattened inspection snapshots retain their
  existing provenance limitation.

Review and release remain. Measurement and export limitations are unchanged
and documented in [measurements](measurements.md) and [mapping](mapping.md).
