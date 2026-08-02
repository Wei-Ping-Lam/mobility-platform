# Competition demo script

Use this script only after checking the run-specific release report. Bracketed
items are presenter prompts, not values to read aloud.

## Current branch demonstration

1. “The six Rice datasets are our canonical supplied evidence. They describe
   commercial activity, weather, urban heat, POIs, origin context, and spending.”
2. Open **Methods & QA**. Show source status, missing weather coverage,
   combined-market allocation, model validation, and artifact downloads.
3. Open **Explorer**. “The current event band is a planning scenario. It is not
   observed match attendance, and the current model has not passed both annual
   holdout gates.”
4. Show the transit status. “Strict transit comparison is unavailable until a
   pinned, event-valid GTFS snapshot is integrated. We do not substitute an
   expert score.”
5. “Contract 0.3 defines the release-ready schedule, hourly movement, physical
   access-gap, intervention-outcome, and investment-recommendation interfaces.
   Those interfaces are not evidence that the results are complete.”

Stop here if the competition-ready release gates have not passed.

## Release demonstration after all gates pass

1. Open **Executive** and select `[city]` and `[match]`.
   - “The base planning scenario has `[peak_demand_per_hour]` peak passengers
     per hour and `[residual_passengers]` passengers beyond modeled scheduled
     capacity.”
   - State evidence status and one material limitation.
2. Open the priority-corridor map.
   - Show GTFS routes/stops, OSM network walk distance, UHI, POIs, and source
     coverage.
   - “This is a network-planning view. It is not an accessibility certification.”
3. Compare **Baseline**, **Operational Package**, and **Capital Package**.
   - State package inputs before outcomes.
   - Read the modeled ranges for gap resolved, venue-area vehicle trips, net
     VMT, net CO2e, heat exposure, and cost.
   - “These are scenario differences under documented assumptions.”
4. Open the tradeoff view.
   - Compare cost per passenger, net CO2e, lead time, and evidence quality.
   - Explain why one package suits the selected objective without calling it
     universally optimal.
5. Open **Methods & QA**.
   - Trace one metric to its contract field, source URL, retrieval time, hash,
     factor range, and test result.
   - Download the scenario and verify that it matches the displayed values.
6. Close with the decision:
   - “For `[city]`, this evidence supports evaluating `[intervention]` because
     it addresses `[documented gap]`. The modeled range is `[range]`, the
     order-of-magnitude cost is `[range]`, and the implementation lead time is
     `[band]`. Agency review and local engineering remain required.”

## Language guardrails

- Say “planning scenario,” “modeled range,” “scheduled capacity,” “venue-area
  vehicle trips,” and “network evidence.”
- Do not describe retail visits as match attendance or origin records as fans.
- Do not present scheduled transit capacity as ridership or reliability.
- Do not present an OSM route as an ADA or safety audit.
- Do not present scenario differences as observed outcomes or causal effects.
- Do not describe a pressure proxy as roadway congestion.
