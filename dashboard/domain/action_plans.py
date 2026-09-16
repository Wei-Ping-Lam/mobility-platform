"""Hand-authored, city-specific action plans for the City action plan page.

Each plan pairs the shared, structural problem every host faces with the one
real, already-sourced friction point specific to that host (see the "Current
strategies" section, sourced from dashboard/pipeline/public/strategy_benchmarks.py,
for the underlying citations), then a single recommended first action and why
it beats the alternatives already screened in the comparison table below it.

This is decision support - an analyst's synthesis of the real evidence
gathered elsewhere in this app - not a locally engineered, funded, or
approved plan. It does not replace the quantified, scenario-labeled
intervention screen; it reframes which option that screen's own numbers
should lead with, given the specific real-world constraint at each venue.
"""

from __future__ import annotations

from typing import Any

# Real, independently-verified coordinates for the specific place(s) each
# host's recommended_action names - not the engine's own, separately-modeled
# regional-hub pick (dashboard/models/traffic_strategy.py), which answers a
# different question (bounded GTFS connectivity screening) and often doesn't
# correspond to what the recommendation actually targets. Dallas's hubs are
# the same real Victory/Fort Worth Central stations already pinned in
# dashboard/pipeline/public/traffic_management.py's published Dallas plan;
# the rest were verified via web search (Wikipedia/Amtrak/SEPTA/racetrack
# listings) since this app never guesses coordinates. Cities omitted here
# don't name a single confidently-identifiable real place (e.g. Kansas
# City's gate-operations fix, Miami's unspecified "four hubs") - the UI shows
# the venue alone for those rather than pointing at a guessed location.
RECOMMENDATION_FOCUS_POINTS: dict[str, tuple[dict[str, Any], ...]] = {
    "Dallas": (
        {"name": "Victory Station", "lat": 32.789607, "lon": -96.812513},
        {"name": "Fort Worth Central Station", "lat": 32.751796, "lon": -97.325397},
    ),
    "New York/NJ": (
        {"name": "Meadowlands Racetrack (sanctioned rideshare lot)", "lat": 40.8175, "lon": -74.0725},
    ),
    "Philadelphia": (
        {"name": "NRG Station (Broad Street Line)", "lat": 39.9054, "lon": -75.1732},
    ),
}

CITY_ACTION_PLANS: dict[str, dict[str, str]] = {
    "Atlanta": {
        "expected_impact": "Less driving",
        "impact_metric": "Rail mode share",
        "impact_metric_definition": "Share of attendees arriving by rail (%)",
        "impact_inputs": "Parking-price response and station-level passenger counts.",
        "specific_problem": (
            "Atlanta's access is already excellent (five-minute MARTA headways, dual "
            "downtown stations) - its real weak point is abundant nearby parking, which "
            "keeps car-dependent design viable even where transit doesn't require it."
        ),
        "recommended_action": (
            "Manage the existing parking supply toward transit rather than add capacity: "
            "price or restrict event-day parking near the two MARTA stations to nudge mode "
            "share toward rail."
        ),
        "rationale": (
            "Frequent MARTA service already supports the venue, but abundant nearby parking still encourages driving."
        ),
    },
    "Boston": {
        "expected_impact": "Lower fares and service emissions",
        "impact_metric": "Cost per rider",
        "impact_metric_definition": "Round-trip out-of-pocket cost ($)",
        "impact_inputs": "Fare-credit uptake, existing bus bookings, route mileage, fleet emissions, and charging costs.",
        "specific_problem": (
            "Getting to Foxborough without a car is expensive and requires advance planning, "
            "while road congestion makes reliable regional access difficult."
        ),
        "recommended_action": (
            "Offer fare support on existing stadium trains and express buses, and replace conventional "
            "express buses with electric vehicles where range and charging allow. Add routes only where "
            "booking and travel data demonstrate an unmet need."
        ),
        "rationale": (
            "The published plan already included direct Rhode Island express buses, but $80 train and $95 bus "
            "round trips made car-free travel costly. Improve those services before duplicating them."
        ),
    },
    "Dallas": {
        "expected_impact": "Shorter queues",
        "impact_metric": "Transfer wait",
        "impact_metric_definition": "Peak transfer wait at both hubs (min)",
        "impact_inputs": "Pre-positioned fleet, dispatch headways, bus loads, and baseline queues.",
        "specific_problem": (
            "The TRE-to-charter-bus bridge is a real, working published plan, but overflow "
            "buses are dispatched reactively - only \"when TRE reaches capacity and "
            "passenger lines form.\""
        ),
        "recommended_action": (
            "Pre-position electric overflow buses at Victory and Fort Worth Central, replacing equivalent "
            "conventional overflow trips. Size departures to bookings and the match forecast before queues form."
        ),
        "rationale": (
            "The published plan triggers overflow dispatch only after TRE reaches capacity and passenger lines form."
        ),
    },
    "Houston": {
        "expected_impact": "Less walking",
        "impact_metric": "Walk distance",
        "impact_metric_definition": "Final walking distance per shuttle rider (mi)",
        "impact_inputs": "Shuttle stops, route length, fleet size, and expected uptake.",
        "specific_problem": (
            "The 14-mile Green Corridor has real shade structures, tree canopy, and water "
            "stations, but local reporting describes the roughly 5.5-mile walk to NRG as a "
            "rough trek in practice despite the amenities."
        ),
        "recommended_action": (
            "Run a reserved electric shuttle for the final one to two miles nearest NRG. "
            "Serve walkers and replace local car/rideshare trips; dispatch only when bookings meet the emissions break-even target."
        ),
        "rationale": (
            "The Green Corridor already provides shade and water, but the remaining walking distance can still deter visitors."
        ),
    },
    "Kansas City": {
        "expected_impact": "Faster entry",
        "impact_metric": "Gate throughput",
        "impact_metric_definition": "Vehicles admitted per hour",
        "impact_inputs": "Gate staffing, booked shuttle loads, conventional fleet baseline, and electric-bus availability.",
        "specific_problem": (
            "The documented 2026 failure at Arrowhead was not transit capacity - only two "
            "of seven stadium entrances were open, causing gridlock severe enough that fans "
            "abandoned vehicles and walked over a mile."
        ),
        "recommended_action": (
            "Open more entrances with dedicated traffic marshals, and replace four conventional Stadium Direct "
            "buses with electric buses on the same booked trips. Improve entry while reducing shuttle emissions."
        ),
        "rationale": (
            "Only two of seven entrances were open during the documented gridlock; the existing shuttle network also offers a fleet-upgrade opportunity."
        ),
    },
    "Los Angeles": {
        "expected_impact": "Faster bus trips",
        "impact_metric": "Connector time",
        "impact_metric_definition": "Peak bus connector journey time (min)",
        "impact_inputs": "Connector operating plan, existing bus mileage and emissions, electric fleet and charging, and signal priority.",
        "specific_problem": (
            "The rail connection promised to SoFi Stadium (the Inglewood Transit "
            "Connector) was cancelled in October 2024; the fallback is dedicated bus lanes "
            "to the Metro K and C Lines, which exist on paper but aren't yet enforced."
        ),
        "recommended_action": (
            "Enforce the connector bus lanes and transit signal priority, paired with six electric buses "
            "replacing conventional connector trips. Keep the same route and service coverage."
        ),
        "rationale": (
            "With the rail connector cancelled, access depends on reliable bus links to the Metro K and C Lines."
        ),
    },
    "Miami": {
        "expected_impact": "Faster egress",
        "impact_metric": "Boarding wait",
        "impact_metric_definition": "Post-match shuttle boarding wait (min)",
        "impact_inputs": "Staged fleet, dispatch timing, bus capacity, and demand at each hub.",
        "specific_problem": (
            "Hard Rock Stadium is explicitly not walkable and has no rail; the real "
            "four-hub Game Day Express shuttle network is a working concept, but egress "
            "capacity right after the final whistle is the risk."
        ),
        "recommended_action": (
            "Pre-stage electric buses at the four existing hubs before the final whistle. "
            "Size added departures to reservations and require enough car-trip replacement to reduce operating emissions."
        ),
        "rationale": (
            "The existing hub network serves a venue without rail access, making the concentrated post-match departure surge a key risk."
        ),
    },
    "New York/NJ": {
        "expected_impact": "Better pedestrian flow",
        "impact_metric": "Path throughput",
        "impact_metric_definition": "Pedestrians passing the bottleneck per minute",
        "impact_inputs": "Existing and proposed path widths, pedestrian counts, and accessible-path design.",
        "specific_problem": (
            "The dedicated Meadowlands Rail Line (a 40,000-riders-per-matchday commitment) "
            "is the single largest real transit commitment of any host, but walking to the "
            "stadium is banned and police-enforced - the only sanctioned route is a "
            "1.3-mile path from the rideshare lot."
        ),
        "recommended_action": (
            "Widen and improve that one sanctioned pedestrian path, rather than add more "
            "rail capacity - rail is already this host's strength; the path is the physical "
            "bottleneck."
        ),
        "rationale": (
            "Pedestrians are funneled onto a single sanctioned 1.3-mile route from the rideshare lot despite strong rail service."
        ),
    },
    "Philadelphia": {
        "expected_impact": "Less crowding",
        "impact_metric": "Platform density",
        "impact_metric_definition": "Peak platform occupancy (people per square metre)",
        "impact_inputs": "Platform operating plan, spare train capacity, incentive uptake, and verified displaced car trips.",
        "specific_problem": (
            "Access here is close to best-in-class (SEPTA's Broad Street Line every eight "
            "minutes or less, a fully electrified fleet, a real pedestrian district) - the "
            "residual risk is platform crowding at the single stadium-complex subway stop "
            "during peak egress."
        ),
        "recommended_action": (
            "Pair platform crowd management and signage with targeted rail-travel credits for attendees "
            "who would otherwise drive. Confirm spare train capacity before offering incentives."
        ),
        "rationale": (
            "NRG Station concentrates post-match crowds at one chokepoint in an otherwise strong transit network."
        ),
    },
    "San Francisco": {
        "expected_impact": "Clearer walking and cycling access",
        "impact_metric": "Detour users assisted",
        "impact_metric_definition": "People benefiting from approved-detour improvements",
        "impact_inputs": "Route audits, affected-user counts, wayfinding costs, and observed travel-mode changes.",
        "specific_problem": (
            "Event-day trail closures disrupt direct walking and cycling access for some visitors "
            "and local residents. Stadium transit remains available; the affected routes and extra "
            "travel distance depend on each person's journey."
        ),
        "recommended_action": (
            "Improve wayfinding and crossing guidance on the approved pedestrian and bicycle detours "
            "around the San Tomas Aquino Creek Trail closure. Audit accessibility and user demand "
            "before proposing new infrastructure, while respecting the event security perimeter."
        ),
        "rationale": (
            "Separate walking and cycling detours already exist. This is a localized access improvement, "
            "not evidence of a systemwide transit gap or a need for a permanent bypass."
        ),
        "additional_recommended_action": (
            "Improve post-match transfers at Mountain View and Milpitas: use measured queues and "
            "missed connections to coordinate departures, passenger guidance, and existing contingency buses."
        ),
        "additional_rationale": (
            "VTA already planned extra service and transit ambassadors. Build on that operation; "
            "add capacity only where observed demand shows a gap."
        ),
        "additional_source_url": "https://www.vta.gov/blog/how-will-vta-handle-crowds-world-cup",
        "impact_scope_note": (
            "Detour improvements only. Transfer-improvement benefits and costs are not yet estimated."
        ),
    },
    "Seattle": {
        "expected_impact": "Fewer car trips",
        "impact_metric": "Car trips replaced",
        "impact_metric_definition": "Attendees switching from private vehicles to existing transit",
        "impact_inputs": "Spare transit capacity, intended travel mode, credit redemption, and verified car-trip replacement.",
        "specific_problem": (
            "Seattle already has strong transit and walking access. The remaining sustainability "
            "opportunity is to shift attendees who still plan to drive onto existing service, subject to spare capacity."
        ),
        "recommended_action": (
            "Offer targeted rail-travel credits and station guidance to attendees who would otherwise drive. "
            "Use confirmed spare capacity on existing transit rather than adding vehicle service."
        ),
        "rationale": (
            "The stadium's walkable downtown setting and nearby rail support reducing car use without expanding service."
        ),
    },
}

# Hand-curated analyst judgment (0-100), not a raw formula over unstructured
# text - each score and rationale is grounded in this host's real, cited
# dashboard/pipeline/public/strategy_benchmarks.py congestion_management_evidence
# plus the same web-verified reporting behind CITY_ACTION_PLANS/
# CITY_TRAFFIC_MANAGEMENT_PLANS below. This is decision support, exactly like
# CITY_ACTION_PLANS - it feeds dashboard/domain/scoring.py's readiness
# composite as a "derived" dimension (real evidence behind every score, not a
# guess), but it is an analyst's synthesis of that evidence, not a directly
# measured or observed quantity.
TRAFFIC_MANAGEMENT_SCORES: dict[str, dict[str, Any]] = {
    "Atlanta": {
        "score": 85,
        "rationale": (
            "Real, proactive command structure (linked APD/GDOT command posts, real-time "
            "511 signal-timing control) with no documented match-day traffic failure."
        ),
    },
    "Boston": {
        "score": 45,
        "rationale": (
            "Real closures are planned, but Foxborough's own police chief documented that "
            "traffic from an earlier 2026 match at this venue \"sucked,\" and the $80 event "
            "fare is real evidence the transit side of the plan is under strain too."
        ),
    },
    "Dallas": {
        "score": 80,
        "rationale": (
            "The most detailed real, published closure plan of any host (exact street "
            "segments, channel separation for rideshare/shuttle/pedestrian flows) - only "
            "docked for a reactive, not pre-scheduled, overflow-bus trigger."
        ),
    },
    "Houston": {
        "score": 55,
        "rationale": (
            "Real closures are published, but the Houston-Galveston Area Council's own "
            "warning that commutes could double citywide is a real, documented risk beyond "
            "the venue-adjacent closure zone itself."
        ),
    },
    "Kansas City": {
        "score": 25,
        "rationale": (
            "The clearest documented traffic-management failure of any host: only 2 of 7 "
            "real stadium entrances were opened for the June 16, 2026 match, and KC2026 "
            "itself admitted the resulting gridlock was an operational failure."
        ),
    },
    "Los Angeles": {
        "score": 35,
        "rationale": (
            "A real, documented controversy (police blocking Inglewood residents from their "
            "own streets, forcing a public denial from the mayor and Metro) plus Caltrans' "
            "own warning of I-405 gridlock up to 4 hours before kickoff."
        ),
    },
    "Miami": {
        "score": 65,
        "rationale": (
            "A real, mature, resident-conscious plan (timed closures, local-access passes), "
            "docked only because this same stadium has a real, documented crowd-control "
            "failure precedent (the July 2024 Copa America final gate-storming)."
        ),
    },
    "New York/NJ": {
        "score": 30,
        "rationale": (
            "Despite the largest real dedicated-transit commitment of any host (a 40,000-"
            "rider Meadowlands Rail Line), a real documented failure occurred when rideshare "
            "pickup was cut off at 10:15pm, stranding fans in gridlock for 3+ hours."
        ),
    },
    "Philadelphia": {
        "score": 55,
        "rationale": (
            "The city is real and proactive here (a new post-game reroute already tested in "
            "Nov. 2025), but that test exists specifically because chronic gridlock at this "
            "venue is a real, acknowledged, still-unresolved problem."
        ),
    },
    "San Francisco": {
        "score": 65,
        "rationale": (
            "A real, proven closure footprint reused directly from Super Bowl LX, docked "
            "only for the one real, still-open friction point: the San Tomas Aquino Trail "
            "closure forcing a documented on-street detour."
        ),
    },
    "Seattle": {
        "score": 80,
        "rationale": (
            "A real, well-coordinated plan (direction-based station routing, Pioneer Square "
            "pedestrianization, an expected 80% non-driving mode share) with no documented "
            "match-day traffic failure."
        ),
    },
}

# Hand-authored, city-specific ROAD/CURB/PATROL solutions for the Traffic
# management solution tab - the traffic-operations counterpart to
# CITY_ACTION_PLANS' transit-mode recommendations above. Same conventions:
# decision support grounded in real, cited evidence, not an approved or
# funded plan, and not a replacement for local traffic-engineering judgment.
CITY_TRAFFIC_MANAGEMENT_PLANS: dict[str, dict[str, str]] = {
    "Atlanta": {
        "recommended_action": (
            "Keep the existing GDOT/APD joint command-post structure and the real-time "
            "511 signal-timing control on I-75/85 and Centennial Olympic Park Drive as the "
            "standing model for every match - no new infrastructure needed."
        ),
        "rationale": (
            "This is already the strongest-documented traffic operation of any host; the "
            "highest-value action is protecting and repeating it, not changing it."
        ),
    },
    "Boston": {
        "recommended_action": (
            "Add hard vehicle caps at the Route 1 approaches to Gillette Stadium and "
            "pre-position state police at the two junctions Foxborough already closes to "
            "block navigation-app rerouting, rather than relying on closures alone."
        ),
        "rationale": (
            "Foxborough's own police chief already documented real, severe congestion from "
            "an earlier 2026 match at this venue; the published closures alone did not "
            "prevent it."
        ),
    },
    "Dallas": {
        "recommended_action": (
            "Keep the published channel-separated closures exactly as they are, but convert "
            "the reactive overflow-bus trigger into a pre-scheduled dispatch tied to each "
            "match's forecasted attendance tier."
        ),
        "rationale": (
            "The closure geometry is already real and well-documented; the one real gap is "
            "that overflow response currently waits for queues to form instead of "
            "anticipating them."
        ),
    },
    "Houston": {
        "recommended_action": (
            "Pair the existing NRG-area closures (Fannin, Greenbriar, Cambridge, Holly Hall, "
            "Lantern Point, Kirby) with variable-message signage on I-610/the Loop to divert "
            "through-traffic before it reaches the sports-complex grid."
        ),
        "rationale": (
            "The Houston-Galveston Area Council's own warning is about citywide commute "
            "impact, not just the venue perimeter - the fix has to start upstream of the "
            "closures already in place."
        ),
    },
    "Kansas City": {
        "recommended_action": (
            "Reopen all 7 Truman Sports Complex entrances (not the 2 used on June 16) and "
            "station traffic patrols on each open gate's approach road."
        ),
        "rationale": (
            "This is a documented, admitted operational failure, not a capacity problem - "
            "the fix KC2026 itself pointed to is entrance count, not new infrastructure."
        ),
    },
    "Los Angeles": {
        "recommended_action": (
            "Replace informal street-blocking in Inglewood with a published resident-permit "
            "access system, and station CHP at the I-405 on-ramps nearest SoFi starting 4 "
            "hours before kickoff."
        ),
        "rationale": (
            "The current approach produced a real, public controversy the mayor and Metro "
            "had to publicly deny was policy; a published permit system is the same real "
            "resident-access goal without the ad hoc enforcement."
        ),
    },
    "Miami": {
        "recommended_action": (
            "Keep the timed-closure and local-access-pass system as published, and add "
            "dedicated gate-area crowd-control patrols specifically for egress."
        ),
        "rationale": (
            "The road-closure plan itself is real and mature; the real risk this venue has "
            "already demonstrated (the 2024 Copa America gate-storming) is crowd control at "
            "the gates, not the roads."
        ),
    },
    "New York/NJ": {
        "recommended_action": (
            "Keep rideshare pickup open continuously through egress at the Meadowlands "
            "staging area instead of a hard cutoff time."
        ),
        "rationale": (
            "This is the exact, documented point of failure - a 10:15pm rideshare cutoff "
            "stranded real fans in gridlock for 3+ hours after the Brazil-Morocco match, "
            "despite otherwise-strong real transit performance that night."
        ),
    },
    "Philadelphia": {
        "recommended_action": (
            "Make the Darien Street/Walt Whitman Bridge post-game reroute tested in Nov. "
            "2025 the permanent match-day standard."
        ),
        "rationale": (
            "The city already built and tested this fix for a real, acknowledged, chronic "
            "gridlock problem at this exact venue - adopting it permanently costs nothing "
            "new."
        ),
    },
    "San Francisco": {
        "recommended_action": (
            "Follow the approved match-day traffic plan and coordinate crossing guidance with the "
            "separate pedestrian and bicycle detours around the San Tomas Aquino Creek Trail closure."
        ),
        "rationale": (
            "The published plan provides separate routes for pedestrians and cyclists. "
            "Clear guidance can support access without routing users through the security perimeter."
        ),
    },
    "Seattle": {
        "recommended_action": (
            "No new traffic-management spend; document the direction-based station-routing "
            "and Pioneer Square pedestrianization approach as the reference model for other "
            "hosts."
        ),
        "rationale": (
            "No documented match-day traffic failure exists here - further spend would be "
            "solving a problem Seattle doesn't have, consistent with its overall "
            "strongest-performer status."
        ),
    },
}
