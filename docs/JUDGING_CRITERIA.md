# Judging criteria mapping

This mapping separates current strengths from release acceptance. Scores and
outcomes must be taken from the integrated application, never invented here.

| Criterion | Current evidence | Competition-ready acceptance evidence |
| --- | --- | --- |
| Impact — 25 | Transparent Rice-derived heat, UHI, POI, activity, and economic context; scenario labeling prevents false certainty | For each city: a physical access gap, intervention package, passengers served, venue-area trip range, net VMT/CO2e range, cost range, lead time, and evidence status |
| Data Analytics — 20 | Deterministic ETL, hashes, source statuses, combined-market warnings, seasonal-naive comparison, and no silent transit fallback | Pinned FIFA/GTFS/OSM/factor sources; hourly reconciliation; network-distance checks; capacity ranges; monotonicity; intervention accounting; rank-sensitivity report |
| Innovation — 15 | Evidence gating, status-aware metrics, auditable assumptions, and downloadable artifacts | Match-specific gap diagnosis plus Pareto tradeoffs across gap resolved, cost-effectiveness, emissions, lead time, and evidence quality |
| Feasibility — 15 | Modular cache-only Streamlit application, offline ETL, tests, and workstream ownership | City-specific owner, dependencies, lead-time band, order-of-magnitude cost, source freshness, and operational-versus-capital package distinction |
| Legacy — 10 | Reusable evidence contracts and data pipeline beyond FIFA | Event-agnostic match/event input, repeatable source refresh, baseline monitoring, and post-event comparison without causal claims |
| Visualization — 10 | Executive, Explorer, and Methods views with evidence statuses and table alternatives | Priority corridors, match selector, hourly uncertainty, routes/stops/isochrones, three scenario comparisons, accessible tables, and exact downloads |
| Presentation — 5 | Narrative explains provenance and limitations | Demo answers where, why, what intervention, modeled outcome, cost, lead time, and confidence while following the evidence-to-claim matrix |

## Judge-facing proof sequence

1. Start with one city’s match-specific access gap and evidence status.
2. Show the corridor evidence behind the gap, including missing coverage.
3. Compare Baseline, Operational Package, and Capital Package.
4. Explain one tradeoff rather than claiming a universally optimal package.
5. Open Methods & QA and trace a headline metric to its contract field, source,
   hash, factor, and assumption.
6. State what the platform does not measure.
