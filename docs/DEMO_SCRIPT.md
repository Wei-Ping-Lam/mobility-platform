# Competition demo script

Use this script only after checking the run-specific release report. Bracketed
items are presenter prompts, not values to read aloud.

## Current branch demonstration

1. “The six Rice datasets are our canonical supplied evidence. They describe
   commercial activity, weather, urban heat, POIs, origin context, and spending.”
2. Start in **Portfolio Overview**. Show all 11 host cities, change the map lens,
   and select two cities for the common access/cost/climate comparison.
3. Open **City Brief** for one selection and show the evidence-qualified and
   exploratory options without calling one an optimum.
4. Open **Detailed Comparison**. “Physical access priority, strict MRS, and
   evidence screening are separate decision lenses.”
5. Open **City & Match**. “This event band is a planning scenario, not observed
   match attendance, because both annual holdout gates did not pass.”
6. Show map-layer controls, GTFS status, the OSM route/isochrones, and missing
   coverage. “Scheduled service is not ridership; OSM is not an accessibility audit.”
7. Return to **City Brief** and change the time horizon. “Capital is counted
   once per city, operations recur per event, and nonqualified matches are omitted
   unless I explicitly opt into screening totals.”
8. Open **Methods & QA** and trace one claim to its source hash and assumptions.

Use Kansas City or Philadelphia to show repaired event-period service evidence;
use Boston, Dallas, or New York/NJ to demonstrate honest unavailable evidence.

## Release demonstration after all gates pass

1. Select `[city]` in **Portfolio Overview**, compare it with another host, and open its **City Brief**.
   - Read `[peak_demand_per_hour]`, `[residual_passengers]`, and evidence status.
   - State one material limitation.
2. Compare the exact match-scoped nondominated set, separating qualified options from exploratory sensitivities.
   - Read gap resolved, cost per passenger, net CO2e, lead time, candidate owner,
     and dependencies without calling one option universally optimal.
3. Compare **Baseline**, **Operational Package**, and **Capital Package**.
   - State package inputs before scenario outcomes.
4. Change the time horizon.
   - Explain one-time capital, recurring operations, included matches, and omissions.
5. Open **Detailed Comparison**.
   - Distinguish the 11-city physical access priority from strict MRS and evidence screening.
6. Open **City & Match**.
   - Show hourly uncertainty, selected map layers, and the exact scenario download.
7. Open **Methods & QA**.
   - Trace one metric to its contract field, URL, retrieval time, hash, factor,
     validation result, and test.
8. Close with the decision:
   - “For `[city]`, this evidence supports evaluating `[intervention]` because it
     addresses `[documented gap]`. The modeled range is `[range]`, planning cost
     is `[range]`, lead time is `[band]`, and local agency review remains required.”

## Language guardrails

- Say “planning scenario,” “modeled range,” “scheduled capacity,” “venue-area
  vehicle trips,” and “network evidence.”
- Do not describe retail visits as match attendance or origin records as fans.
- Do not present scheduled transit capacity as ridership or reliability.
- Do not present an OSM route as an ADA, safety, or sidewalk audit.
- Do not present scenario differences as observed outcomes or causal effects.
- Do not describe a pressure proxy as roadway congestion.
