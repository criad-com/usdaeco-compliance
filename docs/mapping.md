# Conceptual IDS and IFC constraint mapping

This is a vocabulary and modeling correspondence, not a claim of IDS XML
conformance or a lossless IFC exchange. No external standard text or legal
limit is reproduced. The example sources and numbers are illustrative.

| USD data | IDS-shaped concept | IFC constraint concept |
|---|---|---|
| `AecoSpecification` | Specification with applicability and requirements | An objective grouping related metrics (`IfcObjective`) |
| `aeco:spec:title`, `source`, `sourceDocument` | Specification title and source description | Constraint name, source and document association |
| classification selector | Applicability classification/entity facet | Classified constrained objects |
| `appliesToTypes` | Applicability narrowed to selected product types | Type-based object selection; not a direct IDS field |
| child `AecoRequirement` | One requirement facet/restriction | `IfcMetric` benchmark over a referenced value |
| `measure` | Property or model-specific measured quantity | Reference-path/value selection for a metric |
| `operator`, `values`, `tokens` | Value restriction | Metric benchmark and benchmark value |
| `unit`, `tolerance` | Measurement convention | Typed/unit-bearing benchmark, with an explicit comparison policy |
| `severity`, `rationale` | Requirement severity/explanation | Constraint grade/description (`IfcConstraint`) |
| result `specifications` relationship | Checked specification association | Constraint association with the checked object |
| result `status`, `report` | Evaluation output | Application result, not a direct serialized IFC metric field |

`between` would require two comparisons combined with logical AND in an IFC
projection. `in` would require multiple equality alternatives. Clause severity
`error` corresponds conceptually to a hard constraint; `warn` to advisory.
Each geometric measured token requires an explicit producer and unit policy;
IDS does not supply this library's geometry engine. Source-layer authority,
content fingerprints and the conservative clear-area algorithm also require
application conventions and are not asserted to round-trip through those formats.

The document category token `aeco:spec:kind` does not classify a built product.
Product selection always uses core classification or catalog inheritance. The
schema deliberately keeps the named record classes and their `spec`/`req`
namespaces together in this one library.
