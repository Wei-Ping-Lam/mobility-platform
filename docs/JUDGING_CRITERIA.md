# Judging criteria mapping

This mapping separates current strengths from release acceptance. Scores and
outcomes must be taken from the integrated application, never invented here.

| Criterion | Current evidence | Competition-ready acceptance evidence |
| --- | --- | --- |
| Impact — 25 | All cities have match demand, intervention packages, VMT/CO2e and cost ranges, candidate actors, and explicit evidence status; capacity-qualified gaps remain withheld pending GTFS | Refresh event-valid GTFS and demonstrate a defensible gap and package tradeoff for each city |
| Data Analytics — 20 | Deterministic Rice/public artifacts, 78 match records, hashes, hourly reconciliation, seasonal-naive comparison, physical invariants, city differentiation, and no silent transit fallback | Replace estimated OSM fixtures and unavailable GTFS with pinned validated extracts/feeds |
| Innovation — 15 | Match-specific movement plus evidence-gated Pareto tradeoffs across gap resolved, cost-effectiveness, emissions, lead time, and evidence quality | Demonstrate the frontier with capacity-qualified service evidence |
| Feasibility — 15 | Modular cache-only application, candidate owner/dependencies, lead-time bands, operational/capital packages, order-of-magnitude costs, tests, and isolated workstreams | Confirm local agency costs, fleet constraints, and delivery dependencies |
| Legacy — 10 | Reusable evidence contracts and data pipeline beyond FIFA | Event-agnostic match/event input, repeatable source refresh, baseline monitoring, and post-event comparison without causal claims |
| Visualization — 10 | Executive, Explorer, and Methods views include match selector, hourly uncertainty, available layers, three scenarios, table alternatives, and exact downloads | Replace placeholder isochrones, add route/stop geometry, and capture desktop/narrow screenshots |
| Presentation — 5 | Narrative and automated guards map claims to contract fields and prohibit unsupported conclusions | Fill team metadata and rehearse a capacity-qualified city case after GTFS refresh |

## Judge-facing proof sequence

1. Start with one city’s match-specific access gap and evidence status.
2. Show the corridor evidence behind the gap, including missing coverage.
3. Compare Baseline, Operational Package, and Capital Package.
4. Explain one tradeoff rather than claiming a universally optimal package.
5. Open Methods & QA and trace a headline metric to its contract field, source,
   hash, factor, and assumption.
6. State what the platform does not measure.
