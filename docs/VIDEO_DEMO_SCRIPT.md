# Video Demo Script

## FIFA 2026 Host City Mobility Readiness

Target length: 3 minutes, including short pauses for chart transitions.
Featured city: Houston. Track: Transportation & Access.
Prepared against the app on September 12, 2026.

Read only the quoted narration. On-screen directions and production notes are not spoken.

## 0:00-0:15 | The Problem

On screen: Start in Portfolio > Overview. Keep the host-city ranking and map visible. Begin speaking immediately; no separate title slide is needed.

> A stadium can welcome tens of thousands of fans. The harder question is how they get there without overwhelming nearby streets. Our platform helps cities connect event-access problems to practical, lower-emission transportation decisions.

## 0:15-0:35 | Compare the Hosts

On screen: Point briefly to the ranking and map. Scroll to the readiness heatmap, showing First/last-mile access, Traffic management, Heat safety, and Venue support. Keep Comparison settings collapsed.

> We start with all eleven U.S. host cities. The ranking gives a quick comparison, while the heatmap shows what drives it: venue access, traffic management, heat safety, and nearby support. These are screening scores, helping planners decide where to look more closely.

## 0:35-0:57 | Understand the Peak

On screen: Open Visitor movement > Peak timing. Select Houston below the hourly curve. Hover once near the departure peak, then move the cursor away so the uncertainty band is visible.

> Next, we model when visitors arrive and leave. Houston's curve highlights the concentrated demand around a match. The shaded range varies attendance from eighty-five to one hundred percent occupancy, with ninety-five percent as the base. These are planning scenarios, not observed crowd counts.

## 0:57-1:14 | Reveal the Tradeoff

On screen: Open Venue access. Show the sustainability-versus-access scatterplot, briefly hover Houston, then scroll just enough to reveal the input heatmap.

> Good access and sustainability are not always the same thing. More parking can improve access while reinforcing car dependence. This view makes that tradeoff visible, and the input heatmap shows which transit, parking, and pedestrian factors contribute to each score.

## 1:14-1:34 | Move from Baseline to an Idea

On screen: Switch the sidebar workspace to City action plan and select Houston. Briefly show City overview, then open Transit solution. Stop at Recommended first action and Why this action.

> Let's turn that comparison into an action. Houston's recommended approach targets the final stretch to NRG: a reserved electric shuttle. It would help people facing a long walk while replacing some local car and rideshare trips. Departures depend on sufficient booked demand.

## 1:34-2:02 | Show the Payoff

On screen: Center all four Projected impact metrics. Let the numbers remain visible for at least five seconds. Briefly open Estimate assumptions and scenario range, then close it.

> Under the base assumptions, that means about one thousand passengers addressed, one hundred twenty-seven kilograms of CO2-equivalent avoided, and roughly five hundred vehicle-miles saved per match, at a planning cost of about six thousand dollars. These are conditional estimates. We subtract shuttle emissions and require enough riders to replace car trips; the assumptions and alternative cases are available here.

## 2:02-2:29 | Compare the Choices

On screen: Scroll to Compare transit solutions. Hover the R star, then the electric-fleet point. Keep the chart key visible, including Existing approach, Related approach, or Published plan labels.

> Cities can also compare dedicated bus lanes, remote park-and-ride hubs, increased transit frequency, and electric fleets. The chart compares passengers addressed with net emissions avoided. The star marks Houston's recommended action; the other labels connect alternatives to the city's documented approaches. Electrifying existing buses benefits riders without claiming that it creates new passenger capacity.

## 2:29-2:45 | Connect to Street Operations

On screen: Open Traffic management solution. Show the documented traffic-control map, then the short recommended traffic-management action. Leave the engine-derived alternative collapsed.

> Transit also needs a workable street plan. This tab connects documented closures and control locations to a city-specific traffic-management recommendation, helping planners see where a proposed service must fit into existing operations.

## 2:45-3:00 | Close on the Decision

On screen: Return to Transit solution and finish on the impact metrics or comparison chart. Hold the last frame for two seconds.

> The goal is to move from baseline to a testable idea: identify the constraint, compare the response, and make the assumptions visible. With updated event data, this same workflow could support concerts, conferences, and future sporting events beyond FIFA.

## Recording Setup

- Record at 1920 x 1080 with browser zoom near 90-100%; confirm charts and legends fit before recording.
- Preload Houston's views once. Start the final take back in Portfolio > Overview.
- Use the Balanced mobility profile. Select Houston in Peak timing and City action plan.
- Keep advanced composite model tests and large data tables collapsed.
- Move the cursor slowly. Use one short hover per chart; avoid tooltips covering the main visual.
- Capture screen footage first if transitions take time, then record the voiceover. Trim loading pauses without changing the displayed results.
- Rehearse once with a timer. Aim for natural speech, with the longest pause on the four impact numbers.

## Verified Numbers and Recording Notes

Houston's current base recommendation displays:

- Passengers addressed / match: 1,012. Say "about one thousand."
- Net CO2e avoided / match: 127 kg. Say "one hundred twenty-seven kilograms."
- Net vehicle-miles saved / match: 496 mi. Say "roughly five hundred vehicle-miles."
- Estimated first-event cost: about $6K, displayed as $0 upfront plus about $6K per match.

These values were checked in the running application code using Streamlit AppTest, with no app exceptions. Recheck them against the screen before recording if the model or source inputs change.

The Houston scenario assumes up to four electric buses, a matched four-mile return corridor, and a 40% car-trip replacement target among riders. Electric operation assumes 40% of the conventional operating-emissions proxy, with a 20% bus-hour cost premium. These are design assumptions to validate, not measured local performance or procurement quotes.

Passengers addressed includes beneficiaries; it is not a count of additional transit riders or unique tournament visitors. Vehicle-miles saved is not a measured reduction in travel delay. Operating-emissions results do not include vehicle manufacturing or construction emissions.

The solution chart's city-approach labels indicate overlap with the evidence snapshot, not verified implementation of the exact modeled package. The recommended star uses the action-specific estimate; the four comparison points use separate, illustrative designs, not equal-budget alternatives.

## Shorter Backup Cut | About 90 Seconds

On screen: Portfolio ranking/map > Houston Peak timing > Houston Transit solution impact metrics > comparison chart. Omit the Venue access and Traffic management stops.

> Hosting a major event is not just about filling a stadium. It is about getting people there without overwhelming the surrounding city.

> Our platform compares all eleven U.S. FIFA host cities, models arrival and departure demand, and connects venue-access problems to transportation choices.

> Here in Houston, the planning curve shows when movement concentrates. The attendance band makes the uncertainty visible.

> The recommended action is a reserved electric shuttle for the final stretch to NRG. Under the base assumptions, it addresses about one thousand passengers, avoids one hundred twenty-seven kilograms of CO2-equivalent, and saves roughly five hundred vehicle-miles per match, at a planning cost of about six thousand dollars.

> Those benefits depend on booked demand and enough riders replacing car trips. The app shows the assumptions instead of presenting the estimates as measured results.

> We also compare bus lanes, park-and-ride hubs, more frequent transit, and electric fleets. The star identifies the recommended action, while city-approach labels show where existing strategies overlap.

> This helps planners move from a baseline to a testable intervention, with a workflow that could be reused for future sports, concerts, and conferences.

## Presenter Notes | Not Spoken

- Impact: Give the four Houston metrics the clearest, longest shot.
- Data analytics: Show the occupancy band and briefly reveal assumptions. Do not describe these as validated crowd predictions or statistical confidence intervals.
- Innovation: Emphasize the connection between city comparison, the local constraint, and an action-specific estimate.
- Feasibility: The next step is validation with the transit agency and venue operator: route, reservations, accessible boarding, charging, staffing, and local bids. Do not imply this validation has already occurred.
- Legacy: Describe future-event reuse as an opportunity, not a demonstrated long-term result.
- Resilience: If asked, explain that stress-test calculations remain in the underlying model and detailed evidence; the current Portfolio does not have a standalone Transportation resilience tab. Do not narrate a view that is no longer present.
- This is a visual demo, not a tour of every control. Do not spend the main take reading formulas or scrolling through large tables.
