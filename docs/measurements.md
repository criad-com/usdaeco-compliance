# Measurement and result contract

All measured quantities use the composed default-time geometry. Bodies must
carry `AecoDerivedGeometryAPI`, role `body`, and the referent's existing
`aeco:id` as source. v0.1 supports Mesh vertices and analytic Cube bounds.
It ignores nominal mounting-height and offset answers. Lengths are multiplied
by `metersPerUnit`, areas by its square; Z-up and horizontal floor datums are
required. Unsupported/missing data yields an explicit unmeasurable finding.

| Token | v0.1 measurement | Limit |
|---|---|---|
| `measured:centreHeightAboveFloor` | World body-bound centre Z minus containing AecoLevel transform origin Z | Geometric centre and level datum; optical centre and floor finishes are not identified |
| `measured:bottomHeightAboveFloor` | Lowest body vertex Z minus the same floor datum | Tessellation accuracy follows the input body |
| `measured:distanceToDoorLeafEdge` | Lateral distance in the door frame from reader centre to nearest door-body envelope edge | Combined leaf/frame mesh; includes the jamb, not an isolated leaf |
| `measured:sideOfDoor` | Sign of reader centre relative to the door centre along the exported approach normal | The example convention defines that normal as the pull side; it is not inferred from swing geometry |
| `measured:clearFloorArea` | Rectangular space extent area minus union of intersecting obstacle body rectangles up to 1.8 m above the floor | Conservative plan area, not a wheelchair turning or path-reachability test |

In the iris stage the combined door frame extends 0.025 m beyond the nominal
leaf. The measured envelope offset is approximately **0.325 m**, whereas the
exported nominal offset is 0.35 m. Both lie inside the illustrative 0.30–0.50 m
band. A precise leaf-edge verdict is **not proven** by this representation.

Door association first uses the existing exported source reference
`aeco:props:DC_Identity:Door`, resolved against exported door source keys.
These are input cross-references, never newly authored element identities;
reports use only core `aeco:id`. Where no source reference exists, exactly one
same-level door must fall within a 1.5 m lateral / 0.75 m plane search envelope.
Zero or multiple candidates raise `missingBinding`; a broken explicit reference
never falls back to a guessed door. The approach-normal input is the exported
core ad-hoc property `aeco:props:DC_DoorApproach:ApproachNormal`, expressed in
stage axes. The evaluator reads no CCTV or other kind-library property.

Arbitrary scalar element properties can also be measured by attribute name.
They must already use the clause's stated SI unit; there is no automatic unit
inference. String comparisons use `tokens` and dimensionless unit `1`. Numeric
`eq` and `in` accept absolute differences within tolerance; `ne` negates equality;
`between`, `le` and `ge` expand accepted bounds by tolerance. Strict `lt`/`gt`
require separation exceeding tolerance. Invalid units, NaN, descending bounds,
wrong arity, missing properties and incompatible value types fail loudly.

Clear floor area requires a marked rectangular `extent` representation on the
containing space. It subtracts the union of obstacle XY bounds rather than
summing overlapping rectangles. Missing obstacle bodies refuse measurement.
The iris acceptance example does not use this token; an independent overlapping
obstacle fixture checks a 16 m2 room with 1.5 m2 occupied and 14.5 m2 clear.

Results are one replaceable layer containing only API application and the three
result properties. Input fingerprints include composed requirements, values,
mesh vertices/topology, transforms, body stamps, classification, type inheritance
and spatial properties. Presentation colour/visibility and tagged drawing prims
are excluded. Freshness is conservative: an unrelated model input change may
invalidate every result. Re-run rather than editing a result by hand.

Publication figure meshes are marked `AecoDerivedGeometryAPI` symbols beneath
the existing facility referent, with its core identity as source. Their bounding
geometry declares `approx = bbox`; it is presentation, never a measurement body.
