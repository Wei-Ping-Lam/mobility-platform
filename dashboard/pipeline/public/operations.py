"""Build and validate compact FIFA 2026 operational-evidence snapshots.

The checked snapshot contains manually reviewed facts from official agency and
government publications. Raw HTTP responses are retained only in the ignored
``data/raw`` tree; their hashes make each transcription auditable without
shipping mutable webpages or large source files with the application.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import (
    VALID_STATUSES,
    artifact_hash,
    base_snapshot,
    read_json,
    sha256_bytes,
    validate_source,
    write_json,
)

SCHEMA_VERSION = "1.2.0"
DEFAULT_RAW_ROOT = Path("data/raw/operations")
DEFAULT_OUTPUT = Path("data/snapshots/operations/world_cup_2026_operations.json")


SOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "marta_world_cup_situation_2026": {
        "city": "Atlanta",
        "source": "MARTA World Cup Situation Report",
        "url": "https://itsmarta.com/marta-world-cup-situation-report.aspx",
        "publisher": "Metropolitan Atlanta Rapid Transit Authority",
        "version": "Updated through 2026-07-15",
        "license": "Official public information; retain publisher attribution and source terms",
        "coverage_start": "2026-06-11",
        "coverage_end": "2026-07-15",
        "status": "observed",
        "raw_filename": "atlanta_marta_world_cup_situation.html",
        "source_type": "post-event operational report",
        "verification_terms": ["4,655,000", "240,000"],
    },
    "mass_world_cup_outcomes_2026": {
        "city": "Boston",
        "source": "MBTA and Keolis Deliver Unprecedented Boston Stadium Train Service",
        "url": "https://www.keolis.com/en/newsroom-en/news/mbta-and-keolis-deliver-unprecedented-boston-stadium-train-service",
        "publisher": "Keolis Commuter Services, MBTA operating partner",
        "version": "Published 2026-07-20",
        "license": "Official operator publication; retain attribution and source terms",
        "coverage_start": "2026-06-13",
        "coverage_end": "2026-07-09",
        "status": "observed",
        "raw_filename": "boston_keolis_world_cup_operations.html",
        "source_type": "post-event operational report",
        "verification_terms": ["108,940", "88%"],
    },
    "dart_world_cup_service_2026": {
        "city": "Dallas",
        "source": "DART Returns to Normal Service Frequency",
        "url": "https://www.dart.org/about/news-and-events/newsreleases/newsrelease-detail/dart-returns-to-normal-service-frequency",
        "publisher": "Dallas Area Rapid Transit",
        "version": "Published 2026-07-15",
        "license": "Official agency publication; retain attribution",
        "coverage_start": "2026-06-08",
        "coverage_end": "2026-07-19",
        "status": "observed",
        "raw_filename": "dallas_dart_world_cup_service.html",
        "source_type": "post-event operational report",
        "verification_terms": ["12.9%"],
    },
    "houston_host_committee_world_cup_metrics_2026": {
        "city": "Houston",
        "source": "Houston Host Committee Operational, Attendance and Transportation Metrics",
        "url": "https://www.fwc26houston.com/post/fifa-world-cup-2026-houston-host-committee-reports-operational-attendance-and-transportation-metri",
        "publisher": "FIFA World Cup 2026 Houston Host Committee",
        "version": "First 15 tournament days; accessed 2026-08-02",
        "license": "Official host-committee publication; retain attribution and source terms",
        "coverage_start": "2026-06-14",
        "coverage_end": "2026-06-23",
        "status": "partial",
        "raw_filename": "houston_host_committee_transportation_metrics.html",
        "source_type": "in-tournament operational report",
        "verification_terms": ["246,169", "69,765", "25,000 to 30,000"],
    },
    "kc_streetcar_world_cup_recap_2026": {
        "city": "Kansas City",
        "source": "World Cup Month + KC Streetcar Recap",
        "url": "https://kcstreetcar.org/world-cup-recap/",
        "publisher": "Kansas City Streetcar Authority",
        "version": "Published 2026-07-21",
        "license": "Official public-authority publication; retain attribution and source terms",
        "coverage_start": "2026-06-11",
        "coverage_end": "2026-07-11",
        "status": "observed",
        "raw_filename": "kansas_city_streetcar_world_cup_recap.html",
        "source_type": "post-event operational report",
        "verification_terms": ["838,826", "55,973", "1,680"],
    },
    "la_metro_world_cup_outcomes_2026": {
        "city": "Los Angeles",
        "source": "Metro Delivers Golden Boot Service for World Cup Fans",
        "url": "https://www.metro.net/about/metro-delivers-golden-boot-service-for-world-cup-fans-delivering-more-than-210000-rides-celebratory-customer-experience/",
        "publisher": "Los Angeles County Metropolitan Transportation Authority",
        "version": "Published 2026-07-16",
        "license": "Official agency publication; retain attribution",
        "coverage_start": "2026-06-12",
        "coverage_end": "2026-07-10",
        "status": "observed",
        "raw_filename": "los_angeles_metro_world_cup_outcomes.html",
        "source_type": "post-event operational report",
        "verification_terms": ["212,865", "9.6 million"],
    },
    "miami_dade_world_cup_outcomes_2026": {
        "city": "Miami",
        "source": "Miami-Dade World Cup Tournament Conclusion",
        "url": "https://www.miamidade.gov/global/release.page?Mduid_release=rel1784578276391561",
        "publisher": "Miami-Dade County",
        "version": "Post-tournament release accessed 2026-08-02",
        "license": "Official county publication; retain attribution",
        "coverage_start": "2026-06-15",
        "coverage_end": "2026-07-18",
        "status": "observed",
        "raw_filename": "miami_dade_world_cup_outcomes.html",
        "source_type": "post-event operational report",
        "verification_terms": ["230,000", "203,000", "836,000"],
    },
    "nj_transit_world_cup_aar_2026": {
        "city": "New York/NJ",
        "source": "New Jersey Interagency Transportation After Action Report at NJNY Stadium",
        "url": "https://www.njtransit.com/press-releases/new-jersey-interagency-transportation-after-action-report-aar-njny-stadium-fifa",
        "publisher": "New Jersey Transit Corporation",
        "version": "Report dated 2026-07-21",
        "license": "Official agency publication; retain attribution and source terms",
        "coverage_start": "2026-06-13",
        "coverage_end": "2026-07-19",
        "status": "observed",
        "raw_filename": "new_york_new_jersey_transportation_aar.html",
        "source_type": "post-event interagency after-action report",
        "verification_terms": ["370,000", "24,000", "American Dream Pedestrian Count"],
    },
    "septa_june_2026_ridership": {
        "city": "Philadelphia",
        "source": "SEPTA Ridership: June 2026",
        "url": "https://wwww.septa.org/news/ridership-june-2026/",
        "publisher": "Southeastern Pennsylvania Transportation Authority",
        "version": "Published 2026-07-17",
        "license": "Official agency publication; retain attribution",
        "coverage_start": "2026-06-01",
        "coverage_end": "2026-06-30",
        "status": "observed",
        "raw_filename": "philadelphia_septa_june_2026_ridership.html",
        "source_type": "monthly operational report with event comparisons",
        "verification_terms": ["25,671", "82%", "19%"],
    },
    "bart_vta_world_cup_opening_2026": {
        "city": "San Francisco",
        "source": "Public Transit Ridership Records Broken for FIFA World Cup Stadium Opener",
        "url": "https://www.bart.gov/news/articles/2026/news20260615-0",
        "publisher": "Bay Area Rapid Transit, reporting coordinated VTA, Caltrain, ACE, and Capitol Corridor results",
        "version": "Published 2026-06-15",
        "license": "Official agency publication; retain attribution and source terms",
        "coverage_start": "2026-06-13",
        "coverage_end": "2026-06-13",
        "status": "partial",
        "raw_filename": "san_francisco_bart_vta_world_cup_opening.html",
        "source_type": "match-specific operational report",
        "verification_terms": ["37,642", "less than 90 minutes", "nearly 7,000"],
    },
    "sound_transit_world_cup_2026": {
        "city": "Seattle",
        "source": "A Tournament to Remember",
        "url": "https://www.soundtransit.org/blog/platform/tournament-to-remember",
        "publisher": "Sound Transit",
        "version": "Published 2026-07-10",
        "license": "Official agency publication; retain attribution and source terms",
        "coverage_start": "2026-06-01",
        "coverage_end": "2026-07-06",
        "status": "observed",
        "raw_filename": "seattle_sound_transit_world_cup_outcomes.html",
        "source_type": "post-event operational report",
        "verification_terms": ["5.4 million", "174"],
    },
}


METRICS: tuple[dict[str, Any], ...] = (
    {
        "metric_id": "atl_rail_trips_world_cup_period",
        "city": "Atlanta",
        "metric": "Rail passenger trips during World Cup operating period",
        "value": 4_655_000,
        "unit": "unlinked passenger trips",
        "status": "observed",
        "granularity": "35-day systemwide total",
        "sample_size": 35,
        "source_id": "marta_world_cup_situation_2026",
        "source_locator": "Rail Ridership table, Total row",
        "calibration_use": "Systemwide event-period ridership context and daily-baseline comparison",
        "not_suitable_for": ["stadium attendance", "match-hour arrivals", "venue mode share"],
        "notes": "Includes matches, Fan Fest activations, other events, and non-FIFA days.",
    },
    {
        "metric_id": "atl_peak_daily_rail_trips",
        "city": "Atlanta",
        "metric": "Peak daily rail passenger trips during reported period",
        "value": 240_000,
        "unit": "unlinked passenger trips/day",
        "status": "observed",
        "granularity": "systemwide day",
        "sample_size": 1,
        "source_id": "marta_world_cup_situation_2026",
        "source_locator": "Rail Ridership table, 2026-06-24 row",
        "calibration_use": "Upper-bound daily transit demand benchmark",
        "not_suitable_for": ["station load", "match-hour arrivals", "venue mode share"],
        "notes": "Reported as 2.6 times typical daily rail ridership and includes Fan Fest activity.",
    },
    {
        "metric_id": "bos_special_train_tickets",
        "city": "Boston",
        "metric": "World Cup special-train round-trip tickets sold",
        "value": 108_940,
        "unit": "round-trip tickets",
        "status": "observed",
        "granularity": "seven-match tournament total",
        "sample_size": 7,
        "source_id": "mass_world_cup_outcomes_2026",
        "source_locator": "Transportation operations bullet list",
        "calibration_use": "Observed special-rail demand benchmark",
        "not_suitable_for": ["unlinked trips", "hourly platform load", "all-mode attendance"],
        "notes": "Ticket sales are not interchangeable with completed passenger trips.",
    },
    {
        "metric_id": "bos_two_hour_egress_share",
        "city": "Boston",
        "metric": "Passengers departed Foxboro by train within two hours after matches",
        "value": 88,
        "unit": "percent of passengers",
        "status": "observed",
        "granularity": "seven-match service reliability summary",
        "sample_size": 7,
        "source_id": "mass_world_cup_outcomes_2026",
        "source_locator": "World Cup train service by the numbers",
        "calibration_use": "Observed post-match rail-egress benchmark",
        "not_suitable_for": ["hourly egress profile", "individual train load", "all-mode departure time"],
        "notes": "The publication reports an aggregate threshold share, not passenger-level timestamps.",
    },
    {
        "metric_id": "dal_enhanced_period_ridership_change",
        "city": "Dallas",
        "metric": "Ridership change during enhanced-service period",
        "value": 12.9,
        "unit": "percent increase",
        "status": "observed",
        "granularity": "agencywide enhanced-service period",
        "sample_size": None,
        "source_id": "dart_world_cup_service_2026",
        "source_locator": "Post-event service summary, second paragraph",
        "calibration_use": "Agencywide tournament uplift benchmark",
        "not_suitable_for": ["match ridership", "Arlington shuttle throughput", "mode share"],
        "notes": "The public release does not define the comparison denominator in sufficient detail for causal attribution.",
    },
    {
        "metric_id": "hou_first_four_matchday_rail_riders",
        "city": "Houston",
        "metric": "METRORail riders across the first four matchdays",
        "value": 246_169,
        "unit": "unlinked passenger trips",
        "status": "observed",
        "granularity": "four matchday systemwide total",
        "sample_size": 4,
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations section",
        "calibration_use": "Observed matchday rail-demand context and match-to-match scaling",
        "not_suitable_for": ["stadium attendance", "unique riders", "station-level arrivals"],
        "notes": "Systemwide matchday rail ridership includes ordinary travel and non-stadium event activity.",
    },
    {
        "metric_id": "hou_peak_reported_matchday_rail_riders",
        "city": "Houston",
        "metric": "Highest reported METRORail matchday ridership",
        "value": 69_765,
        "unit": "unlinked passenger trips/day",
        "status": "observed",
        "granularity": "Portugal vs. Uzbekistan matchday",
        "sample_size": 1,
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations matchday list",
        "calibration_use": "Observed upper matchday rail-demand benchmark",
        "not_suitable_for": ["post-match egress", "stadium mode share", "peak passengers/hour"],
        "notes": "This is a full-day systemwide rail count, not a venue-only passenger count.",
    },
    {
        "metric_id": "hou_post_match_egress_midpoint",
        "city": "Houston",
        "metric": "Estimated post-match METRO egress surge midpoint",
        "value": 27_500,
        "unit": "riders",
        "status": "estimated",
        "granularity": "Portugal vs. Uzbekistan post-match egress",
        "sample_size": 1,
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations closing paragraph",
        "calibration_use": "Sensitivity range for venue egress demand",
        "not_suitable_for": ["observed exact count", "15-minute egress profile", "all-mode departures"],
        "notes": "Source range is 25,000-30,000 riders; 27,500 is its arithmetic midpoint and remains estimated.",
    },
    {
        "metric_id": "kc_streetcar_tournament_period_trips",
        "city": "Kansas City",
        "metric": "KC Streetcar passenger trips during the tournament period",
        "value": 838_826,
        "unit": "unlinked passenger trips",
        "status": "observed",
        "granularity": "2026-06-11 through 2026-07-11 system total",
        "sample_size": 31,
        "source_id": "kc_streetcar_world_cup_recap_2026",
        "source_locator": "World Cup Month recap opening paragraph",
        "calibration_use": "Downtown tournament-period transit-demand context",
        "not_suitable_for": ["stadium shuttle demand", "unique visitors", "match mode share"],
        "notes": "The count excludes Streetcar Link bus trips and includes everyday non-event travel.",
    },
    {
        "metric_id": "kc_streetcar_peak_daily_trips",
        "city": "Kansas City",
        "metric": "Peak KC Streetcar daily passenger trips",
        "value": 55_973,
        "unit": "unlinked passenger trips/day",
        "status": "observed",
        "granularity": "2026-07-11 systemwide day",
        "sample_size": 1,
        "source_id": "kc_streetcar_world_cup_recap_2026",
        "source_locator": "World Cup Month results paragraph",
        "calibration_use": "Observed peak downtown rail-demand benchmark",
        "not_suitable_for": ["stadium attendance", "hourly vehicle load", "venue access mode share"],
        "notes": "The date included the FIFA Fan Festival and a stadium match; attribution is not separable.",
    },
    {
        "metric_id": "kc_fan_fest_average_daily_trips",
        "city": "Kansas City",
        "metric": "Average KC Streetcar trips on FIFA Fan Festival days",
        "value": 33_689,
        "unit": "unlinked passenger trips/day",
        "status": "observed",
        "granularity": "FIFA Fan Festival day average",
        "sample_size": None,
        "source_id": "kc_streetcar_world_cup_recap_2026",
        "source_locator": "World Cup Month results paragraph",
        "calibration_use": "Event-day downtown activity benchmark",
        "not_suitable_for": ["stadium access demand", "causal event uplift", "unique visitors"],
        "notes": "The publication does not state the number of days included in this average.",
    },
    {
        "metric_id": "kc_streetcar_peak_fleet",
        "city": "Kansas City",
        "metric": "Maximum streetcars operated during peak festival hours",
        "value": 12,
        "unit": "streetcars",
        "status": "observed",
        "granularity": "peak festival-hour deployment upper bound",
        "sample_size": None,
        "source_id": "kc_streetcar_world_cup_recap_2026",
        "source_locator": "Service expansion paragraph",
        "calibration_use": "Observed event fleet-deployment bound",
        "not_suitable_for": ["passenger capacity without vehicle specification", "scheduled departures", "load factor"],
        "notes": "The source reports a range of 9-12 streetcars and 6-8 supplemental buses.",
    },
    {
        "metric_id": "kc_streetcar_ambassador_hours",
        "city": "Kansas City",
        "metric": "Streetcar Ambassador deployment during the tournament",
        "value": 1_680,
        "unit": "staff-hours",
        "status": "observed",
        "granularity": "tournament-period total",
        "sample_size": None,
        "source_id": "kc_streetcar_world_cup_recap_2026",
        "source_locator": "Teamwork section",
        "calibration_use": "Operational staffing-scale benchmark",
        "not_suitable_for": ["total transit staffing", "labor cost", "staff productivity"],
        "notes": "Ambassador hours exclude other operations, safety, maintenance, and contracted labor.",
    },
    {
        "metric_id": "la_direct_stadium_service_rides",
        "city": "Los Angeles",
        "metric": "Direct enhanced-service rides to and from the stadium",
        "value": 212_865,
        "unit": "passenger rides",
        "status": "observed",
        "granularity": "eight-match tournament total",
        "sample_size": 8,
        "source_id": "la_metro_world_cup_outcomes_2026",
        "source_locator": "Opening results paragraph",
        "calibration_use": "Direct shuttle and feeder-service throughput benchmark",
        "not_suitable_for": ["unique passengers", "all-transit mode share", "hourly hub loads"],
        "notes": "The total covers direct service between the stadium and 15 parking/transit hubs.",
    },
    {
        "metric_id": "la_world_cup_transit_funding",
        "city": "Los Angeles",
        "metric": "FTA funding coordinated for enhanced World Cup service",
        "value": 9_600_000,
        "unit": "USD",
        "status": "observed",
        "granularity": "program allocation",
        "sample_size": None,
        "source_id": "la_metro_world_cup_outcomes_2026",
        "source_locator": "Funding paragraph",
        "calibration_use": "Implementation-scale and funding benchmark",
        "not_suitable_for": ["actual expenditure", "per-match operating cost", "benefit-cost ratio"],
        "notes": "Allocated funding is not the same as audited expenditure.",
    },
    {
        "metric_id": "mia_metrorail_match_riders",
        "city": "Miami",
        "metric": "Metrorail riders carried to all matches",
        "value": 230_000,
        "unit": "riders",
        "status": "observed",
        "granularity": "seven-match tournament total",
        "sample_size": 7,
        "source_id": "miami_dade_world_cup_outcomes_2026",
        "source_locator": "Moving the Masses results section",
        "calibration_use": "Tournament rail-demand benchmark",
        "not_suitable_for": ["unique visitors", "hourly station load", "all-mode attendance"],
        "notes": "The publication does not provide match-by-match or station-time records.",
    },
    {
        "metric_id": "mia_game_day_shuttle_passengers",
        "city": "Miami",
        "metric": "Game Day Express passengers moved to and from the stadium",
        "value": 203_000,
        "unit": "passenger boardings",
        "status": "observed",
        "granularity": "seven-match tournament total",
        "sample_size": 7,
        "source_id": "miami_dade_world_cup_outcomes_2026",
        "source_locator": "Moving the Masses results section",
        "calibration_use": "Observed shuttle throughput benchmark",
        "not_suitable_for": ["unique passengers", "hourly hub capacity", "vehicle occupancy"],
        "notes": "The source describes passengers moved in both directions; the artifact avoids treating the total as unique people.",
    },
    {
        "metric_id": "mia_fan_fest_metromover_trips",
        "city": "Miami",
        "metric": "Metromover trips during Fan Festival period",
        "value": 836_000,
        "unit": "unlinked passenger trips",
        "status": "observed",
        "granularity": "Fan Festival period total",
        "sample_size": None,
        "source_id": "miami_dade_world_cup_outcomes_2026",
        "source_locator": "Moving the Masses results section",
        "calibration_use": "Downtown event-activity transit benchmark",
        "not_suitable_for": ["stadium demand", "match mode share", "unique visitors"],
        "notes": "Fan Festival movement is separate from stadium access.",
    },
    {
        "metric_id": "nynj_event_related_passenger_lower_bound",
        "city": "New York/NJ",
        "metric": "Event-related passengers moved during eight matches",
        "value": 370_000,
        "unit": "passengers",
        "status": "partial",
        "granularity": "eight-match tournament lower bound",
        "sample_size": 8,
        "source_id": "nj_transit_world_cup_aar_2026",
        "source_locator": "Executive Summary, Record Ridership Volume",
        "calibration_use": "Tournament transportation-volume lower bound",
        "not_suitable_for": ["exact total", "unique passengers", "single-mode ridership"],
        "notes": "The report states over 370,000; the stored value is a lower bound, not an exact count.",
    },
    {
        "metric_id": "nynj_average_peak_throughput",
        "city": "New York/NJ",
        "metric": "Average peak transportation throughput",
        "value": 24_000,
        "unit": "passengers/hour",
        "status": "observed",
        "granularity": "eight-match operational average",
        "sample_size": 8,
        "source_id": "nj_transit_world_cup_aar_2026",
        "source_locator": "Strengths / Successes item 1",
        "calibration_use": "Observed venue transportation-throughput benchmark",
        "not_suitable_for": ["15-minute profile", "mode-specific load factor", "roadway congestion"],
        "notes": "The report presents an average and does not publish interval observations behind it.",
    },
    {
        "metric_id": "nynj_average_penn_to_stadium_trip",
        "city": "New York/NJ",
        "metric": "Average New York Penn Station to stadium trip time",
        "value": 35,
        "unit": "minutes",
        "status": "observed",
        "granularity": "tournament operational average",
        "sample_size": None,
        "source_id": "nj_transit_world_cup_aar_2026",
        "source_locator": "Strengths / Successes item 7",
        "calibration_use": "Observed regional transit travel-time benchmark",
        "not_suitable_for": ["walking time", "reliability distribution", "door-to-door visitor time"],
        "notes": "The publication does not state sample size or travel-time dispersion.",
    },
    {
        "metric_id": "nynj_ambassador_shifts",
        "city": "New York/NJ",
        "metric": "Transportation ambassador shifts staffed",
        "value": 4_000,
        "unit": "staff shifts",
        "status": "partial",
        "granularity": "eight-match tournament total lower bound",
        "sample_size": None,
        "source_id": "nj_transit_world_cup_aar_2026",
        "source_locator": "Strengths / Successes item 7",
        "calibration_use": "Operational staffing-scale benchmark",
        "not_suitable_for": ["staff-hours", "labor cost", "all-agency staffing"],
        "notes": "The report states more than 4,000 shifts and more than 700 ambassadors.",
    },
    {
        "metric_id": "phl_nrg_post_match_egress",
        "city": "Philadelphia",
        "metric": "Average passengers moved out of NRG Station after a match",
        "value": 25_671,
        "unit": "passengers/match",
        "status": "observed",
        "granularity": "average post-match station egress",
        "sample_size": None,
        "source_id": "septa_june_2026_ridership",
        "source_locator": "June ridership event comparison paragraph",
        "calibration_use": "Observed post-match rail-egress benchmark",
        "not_suitable_for": ["peak passengers/hour", "all-mode attendance", "individual match distribution"],
        "notes": "The source reports an average and does not publish the averaging sample or time interval.",
    },
    {
        "metric_id": "phl_b_line_match_day_change",
        "city": "Philadelphia",
        "metric": "Average B Line ridership change on match days",
        "value": 82,
        "unit": "percent increase",
        "status": "observed",
        "granularity": "June match-day average",
        "sample_size": None,
        "source_id": "septa_june_2026_ridership",
        "source_locator": "June ridership event comparison paragraph",
        "calibration_use": "Line-level match-day uplift benchmark",
        "not_suitable_for": ["causal impact", "station load", "mode share"],
        "notes": "The comparison baseline is the agency's published match-day comparison, not reconstructed here.",
    },
    {
        "metric_id": "phl_system_match_day_change",
        "city": "Philadelphia",
        "metric": "System ridership change on World Cup match days",
        "value": 19,
        "unit": "percent increase",
        "status": "observed",
        "granularity": "June match-day average",
        "sample_size": None,
        "source_id": "septa_june_2026_ridership",
        "source_locator": "June ridership closing paragraph",
        "calibration_use": "Systemwide match-day uplift benchmark",
        "not_suitable_for": ["causal impact", "venue demand", "mode share"],
        "notes": "Systemwide change includes ordinary travel and other activity on match days.",
    },
    {
        "metric_id": "sf_opening_match_vta_passengers",
        "city": "San Francisco",
        "metric": "VTA passengers for the opening stadium match",
        "value": 37_642,
        "unit": "passengers",
        "status": "observed",
        "granularity": "Match M008 ingress and egress total",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Opening-match results paragraph",
        "calibration_use": "Observed match-specific VTA demand benchmark",
        "not_suitable_for": ["unique passengers", "all-transit mode share", "hourly profile"],
        "notes": "The source combines travel to and from the match.",
    },
    {
        "metric_id": "sf_opening_match_platform_clearance",
        "city": "San Francisco",
        "metric": "Maximum reported post-match platform-clearance time",
        "value": 90,
        "unit": "minutes",
        "status": "partial",
        "granularity": "Match M008 post-match upper bound",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Platform-clearance results paragraph",
        "calibration_use": "Observed upper bound for opening-match VTA egress",
        "not_suitable_for": ["exact clearance time", "passenger-level egress curve", "all-mode departure time"],
        "notes": "The source states less than 90 minutes; the stored value is an upper bound.",
    },
    {
        "metric_id": "sf_opening_match_caltrain_passengers",
        "city": "San Francisco",
        "metric": "Caltrain passengers for the opening stadium match",
        "value": 7_000,
        "unit": "passengers",
        "status": "partial",
        "granularity": "Match M008 ingress and egress approximate total",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Caltrain partner-results paragraph",
        "calibration_use": "Regional rail contribution benchmark",
        "not_suitable_for": ["exact ridership", "unique passengers", "hourly transfer load"],
        "notes": "The source states nearly 7,000; the stored value is approximate.",
    },
    {
        "metric_id": "sf_opening_match_capitol_corridor_trips",
        "city": "San Francisco",
        "metric": "Capitol Corridor opening-match trips",
        "value": 2_400,
        "unit": "passenger trips",
        "status": "partial",
        "granularity": "Match M008 approximate total",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Regional rail partner-results paragraph",
        "calibration_use": "Intercity rail contribution benchmark",
        "not_suitable_for": ["exact ridership", "unique passengers", "hourly transfer load"],
        "notes": "The source states nearly 2,400 trips.",
    },
    {
        "metric_id": "sf_opening_match_ace_trips",
        "city": "San Francisco",
        "metric": "ACE opening-match trips",
        "value": 1_600,
        "unit": "passenger trips",
        "status": "partial",
        "granularity": "Match M008 approximate total",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Regional rail partner-results paragraph",
        "calibration_use": "Regional rail contribution benchmark",
        "not_suitable_for": ["exact ridership", "unique passengers", "hourly transfer load"],
        "notes": "The source states almost 1,600 trips.",
    },
    {
        "metric_id": "sf_opening_match_bart_milpitas_uplift",
        "city": "San Francisco",
        "metric": "BART Milpitas ridership increase versus previous weekend",
        "value": 160,
        "unit": "percent increase lower bound",
        "status": "partial",
        "granularity": "Match M008 station-day comparison",
        "sample_size": 1,
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "BART partner-results paragraph",
        "calibration_use": "Observed station uplift lower bound",
        "not_suitable_for": ["causal effect", "absolute passenger count", "venue mode share"],
        "notes": "The source states more than 160 percent; the stored value is a lower bound.",
    },
    {
        "metric_id": "sea_june_link_boardings",
        "city": "Seattle",
        "metric": "June Link light-rail boardings",
        "value": 5_400_000,
        "unit": "boardings",
        "status": "partial",
        "granularity": "monthly systemwide total",
        "sample_size": 30,
        "source_id": "sound_transit_world_cup_2026",
        "source_locator": "Record results section",
        "calibration_use": "Event-month systemwide rail-demand benchmark",
        "not_suitable_for": ["stadium attendance", "match-hour arrivals", "unique passengers"],
        "notes": "Sound Transit labels these rapid-turnaround APC estimates as preliminary and subject to revision.",
    },
    {
        "metric_id": "sea_match_day_railcars",
        "city": "Seattle",
        "metric": "Light-rail vehicles placed in service on each match day",
        "value": 174,
        "unit": "railcars",
        "status": "observed",
        "granularity": "each of six match days",
        "sample_size": 6,
        "source_id": "sound_transit_world_cup_2026",
        "source_locator": "Preparation pays off section",
        "calibration_use": "Observed fleet-deployment benchmark",
        "not_suitable_for": ["passenger capacity without vehicle configuration", "hourly departures", "load factor"],
        "notes": "Fleet deployed does not by itself establish scheduled or realized passenger capacity.",
    },
)


def _measurement(value: float, unit: str, status: str, interpretation: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "status": status, "interpretation": interpretation}


_NJ_MATCH_VALUES = (
    ("M007", "2026-06-13", 80_000, 6_006, 240, 16_013, 150, 21_271, 21_695, 60, 10_035, 53_000),
    ("M017", "2026-06-16", 78_401, 8_300, 240, 12_000, 150, 25_797, 26_221, 70, 10_085, 42_000),
    ("M041", "2026-06-22", 72_777, 10_800, 180, 12_000, 120, 25_568, 25_946, 60, 9_125, 42_000),
    ("M056", "2026-06-25", 80_663, 12_950, 180, 12_000, 150, 20_593, 20_857, 60, 8_615, 56_000),
    ("M067", "2026-06-27", 80_663, 8_500, 150, 17_166, 120, 25_702, 26_009, 60, 9_000, 50_000),
    ("M077", "2026-06-30", 73_115, 8_500, 150, 17_877, 135, 22_631, 22_816, 60, 10_480, 45_000),
    ("M091", "2026-07-05", 74_273, 11_100, 150, 18_000, 150, 21_856, 22_258, 60, 7_195, 46_000),
    ("M104", "2026-07-19", 80_663, 16_200, 180, 11_168, 120, 20_114, 21_024, 60, 9_310, 65_000),
)


EVENT_RECORDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "city": "New York/NJ",
            "event_id": match_id,
            "event_date": event_date,
            "source_id": "nj_transit_world_cup_aar_2026",
            "source_locator": "Ridership & Service Data table",
            "measurements": {
                "fifa_ticket_holders": _measurement(ticket_holders, "ticket holders", "observed", "Reported stadium ticket-holder count"),
                "uber_passengers": _measurement(uber, "passengers", "partial", "Published modal count; collection method not stated"),
                "uber_egress_minutes": _measurement(uber_minutes, "minutes", "observed", "Published egress duration"),
                "host_committee_shuttle_passengers": _measurement(shuttle, "passengers", "observed", "Published shuttle passenger count"),
                "host_committee_shuttle_egress_minutes": _measurement(shuttle_minutes, "minutes", "observed", "Published egress duration"),
                "nj_transit_ingress": _measurement(njt_ingress, "passengers", "observed", "Published NJ TRANSIT ingress count"),
                "nj_transit_egress": _measurement(njt_egress, "passengers", "observed", "Published NJ TRANSIT egress count"),
                "nj_transit_egress_minutes": _measurement(njt_minutes, "minutes", "observed", "Published egress duration"),
                "american_dream_parking": _measurement(parking, "spaces used", "partial", "Published parking count; underlying sales/occupancy method is not fully specified"),
                "american_dream_pedestrians": _measurement(pedestrians, "pedestrians", "estimated", "Report footnote identifies likely pedestrian equivalent to vehicle sales"),
            },
            "not_suitable_for": ["15-minute flow profile", "causal mode choice", "roadway speed or delay"],
            "notes": "Wide match record preserves the agency table without converting estimates or lower-confidence modes into observed counts.",
        }
        for (
            match_id,
            event_date,
            ticket_holders,
            uber,
            uber_minutes,
            shuttle,
            shuttle_minutes,
            njt_ingress,
            njt_egress,
            njt_minutes,
            parking,
            pedestrians,
        ) in _NJ_MATCH_VALUES
    ),
    {
        "city": "Houston",
        "event_id": "M010",
        "event_date": "2026-06-14",
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations matchday list",
        "measurements": {"systemwide_metrorail_riders": _measurement(48_183, "unlinked passenger trips/day", "observed", "Full matchday systemwide rail ridership")},
        "not_suitable_for": ["stadium attendance", "station load", "peak passengers/hour"],
        "notes": "Germany vs. Curacao matchday; ordinary and other event travel are included.",
    },
    {
        "city": "Houston",
        "event_id": "M023",
        "event_date": "2026-06-17",
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations matchday list",
        "measurements": {"systemwide_metrorail_riders": _measurement(59_937, "unlinked passenger trips/day", "observed", "Full matchday systemwide rail ridership")},
        "not_suitable_for": ["stadium attendance", "station load", "peak passengers/hour"],
        "notes": "Portugal vs. Democratic Republic of Congo matchday; ordinary and other event travel are included.",
    },
    {
        "city": "Houston",
        "event_id": "M035",
        "event_date": "2026-06-20",
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations matchday list",
        "measurements": {"systemwide_metrorail_riders": _measurement(69_765, "unlinked passenger trips/day", "observed", "Full matchday systemwide rail ridership")},
        "not_suitable_for": ["stadium attendance", "station load", "peak passengers/hour"],
        "notes": "Netherlands vs. Sweden matchday; ordinary and other event travel are included.",
    },
    {
        "city": "Houston",
        "event_id": "M047",
        "event_date": "2026-06-23",
        "source_id": "houston_host_committee_world_cup_metrics_2026",
        "source_locator": "Transportation Operations matchday list",
        "measurements": {
            "systemwide_metrorail_riders": _measurement(68_284, "unlinked passenger trips/day", "observed", "Full matchday systemwide rail ridership"),
            "post_match_egress_low": _measurement(25_000, "riders", "estimated", "Published lower estimate"),
            "post_match_egress_high": _measurement(30_000, "riders", "estimated", "Published upper estimate"),
        },
        "not_suitable_for": ["exact egress count", "15-minute egress profile", "all-mode departures"],
        "notes": "Portugal vs. Uzbekistan matchday; the post-match egress count is explicitly estimated by the source.",
    },
    {
        "city": "San Francisco",
        "event_id": "M008",
        "event_date": "2026-06-13",
        "source_id": "bart_vta_world_cup_opening_2026",
        "source_locator": "Opening-match partner results",
        "measurements": {
            "vta_passengers": _measurement(37_642, "passengers", "observed", "Combined match ingress and egress"),
            "platform_clearance_upper_bound": _measurement(90, "minutes", "partial", "Source states less than 90 minutes"),
            "caltrain_passengers": _measurement(7_000, "passengers", "partial", "Source states nearly 7,000"),
            "capitol_corridor_trips": _measurement(2_400, "passenger trips", "partial", "Source states nearly 2,400"),
            "ace_trips": _measurement(1_600, "passenger trips", "partial", "Source states almost 1,600"),
            "bart_milpitas_uplift": _measurement(160, "percent increase lower bound", "partial", "Source states more than 160 percent versus prior weekend"),
        },
        "not_suitable_for": ["all-six-match average", "unique passengers", "15-minute transfer profile"],
        "notes": "Opening match only; later San Francisco matches remain outside this source's coverage.",
    },
)


ACQUISITION_GAPS: dict[str, list[str]] = {
    city: [
        "15-minute APC or faregate entries/exits by venue-relevant station and direction",
        "match-specific arrivals and departures by mode",
        "actual trips operated, cancellations, vehicle assignments, and passenger loads",
        "shuttle boardings by hub and departure time",
        "parking occupancy, rideshare/curb throughput, and pedestrian counts by interval",
        "venue-corridor traffic volumes, speeds, incidents, and signal-operation logs",
        "actual staffing, fleet, contract, fuel, and overtime costs",
    ]
    for city in HOST_CITIES
}


def refresh_source_files(raw_root: Path = DEFAULT_RAW_ROOT, timeout_seconds: int = 60) -> None:
    """Download official source pages explicitly; dashboard runtime never calls this."""

    raw_root.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for source_id, definition in SOURCE_DEFINITIONS.items():
        response = requests.get(definition["url"], headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        target = raw_root / definition["raw_filename"]
        target.write_bytes(response.content)
        if not response.content:
            raise ValueError(f"Empty response for {source_id}")


def missing_verification_terms(definition: Mapping[str, Any], payload: bytes) -> list[str]:
    """Return required human-review terms absent from a downloaded response."""

    source_text = payload.decode("utf-8", errors="replace")
    return [term for term in definition["verification_terms"] if term not in source_text]


def build_snapshot(raw_root: Path, generated_at_utc: str) -> dict[str, Any]:
    """Build a deterministic compact artifact from locally pinned raw pages."""

    sources: dict[str, dict[str, Any]] = {}
    for source_id, definition in SOURCE_DEFINITIONS.items():
        raw_path = raw_root / definition["raw_filename"]
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing pinned operational source: {raw_path}")
        payload = raw_path.read_bytes()
        if not payload:
            raise ValueError(f"Pinned operational source is empty: {raw_path}")
        missing_terms = missing_verification_terms(definition, payload)
        if missing_terms:
            raise ValueError(
                f"Pinned operational source {source_id} is missing review terms: {', '.join(missing_terms)}"
            )
        sources[source_id] = {
            "source": definition["source"],
            "url": definition["url"],
            "publisher": definition["publisher"],
            "retrieved_at_utc": generated_at_utc,
            "version": definition["version"],
            "sha256": sha256_bytes(payload),
            "license": definition["license"],
            "coverage_start": definition["coverage_start"],
            "coverage_end": definition["coverage_end"],
            "status": definition["status"],
            "notes": (
                f"SHA-256 covers raw HTTP response bytes stored locally as {definition['raw_filename']}; "
                "raw files are intentionally ignored by Git."
            ),
            "city": definition["city"],
            "source_type": definition["source_type"],
            "raw_filename": definition["raw_filename"],
            "verification_terms": list(definition["verification_terms"]),
        }

    city_coverage = {}
    for city in HOST_CITIES:
        city_metrics = [row for row in METRICS if row["city"] == city]
        city_events = [row for row in EVENT_RECORDS if row["city"] == city]
        city_coverage[city] = {
            "outcome_status": "observed" if city_metrics else "unavailable",
            "metric_count": len(city_metrics),
            "event_record_count": len(city_events),
            "source_ids": [source_id for source_id, row in SOURCE_DEFINITIONS.items() if row["city"] == city],
            "match_hour_calibration_ready": False,
            "open_request_fields": ACQUISITION_GAPS[city],
        }

    snapshot = {
        **base_snapshot("world_cup_operational_evidence", generated_at_utc),
        "schema_version": SCHEMA_VERSION,
        "status": "partial",
        "source_hash_scope": "Raw HTTP response bytes in ignored data/raw/operations files",
        "extraction_method": "Manual transcription of explicitly located facts; independently review before model calibration",
        "sources": sources,
        "metrics": [dict(row) for row in METRICS],
        "event_records": [dict(row) for row in EVENT_RECORDS],
        "city_coverage": city_coverage,
        "acquisition_note": (
            "Published aggregates improve benchmark context but do not replace interval-level APC/AFC, shuttle, curb, "
            "parking, pedestrian, or roadway records. No metric in this snapshot currently qualifies a match-hour model."
        ),
    }
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Fail closed when operational provenance or semantic limits are incomplete."""

    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Operational snapshot contract mismatch")
    if snapshot.get("snapshot_kind") != "world_cup_operational_evidence":
        raise ValueError("Unexpected operational snapshot kind")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Operational snapshot schema mismatch")
    if snapshot.get("artifact_sha256") != artifact_hash(dict(snapshot)):
        raise ValueError("Operational snapshot content hash mismatch")

    sources = snapshot.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != set(SOURCE_DEFINITIONS):
        raise ValueError("Operational source inventory is incomplete")
    for source_id, source in sources.items():
        validate_source(dict(source))
        if source.get("city") not in HOST_CITIES:
            raise ValueError(f"Unknown source city for {source_id}")
        if not source.get("source_type") or not source.get("raw_filename"):
            raise ValueError(f"Operational source metadata incomplete for {source_id}")
        if not source.get("verification_terms"):
            raise ValueError(f"Operational source review terms missing for {source_id}")

    coverage = snapshot.get("city_coverage")
    if not isinstance(coverage, Mapping) or set(coverage) != set(HOST_CITIES):
        raise ValueError("Operational coverage must include all host cities")

    metric_ids: set[str] = set()
    metrics = snapshot.get("metrics")
    if not isinstance(metrics, list):
        raise ValueError("Operational metrics must be a list")
    required = {
        "metric_id",
        "city",
        "metric",
        "value",
        "unit",
        "status",
        "granularity",
        "sample_size",
        "source_id",
        "source_locator",
        "calibration_use",
        "not_suitable_for",
        "notes",
    }
    for row in metrics:
        if not isinstance(row, Mapping):
            raise ValueError("Operational metric rows must be objects")
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(f"Operational metric metadata missing: {', '.join(missing)}")
        metric_id = str(row["metric_id"])
        if metric_id in metric_ids:
            raise ValueError(f"Duplicate operational metric ID: {metric_id}")
        metric_ids.add(metric_id)
        if row["city"] not in HOST_CITIES or row["source_id"] not in sources:
            raise ValueError(f"Operational metric {metric_id} has an invalid city or source")
        if str(row["status"]) not in VALID_STATUSES:
            raise ValueError(f"Operational metric {metric_id} has an invalid status")
        if not isinstance(row["value"], (int, float)) or not row["unit"] or not row["granularity"]:
            raise ValueError(f"Operational metric {metric_id} lacks a physical value, unit, or granularity")
        if not row["source_locator"] or not row["calibration_use"] or not row["not_suitable_for"]:
            raise ValueError(f"Operational metric {metric_id} lacks review limits")

    event_records = snapshot.get("event_records")
    if not isinstance(event_records, list):
        raise ValueError("Operational event records must be a list")
    event_keys: set[tuple[str, str]] = set()
    for record in event_records:
        if not isinstance(record, Mapping):
            raise ValueError("Operational event records must be objects")
        required_event = {
            "city",
            "event_id",
            "event_date",
            "source_id",
            "source_locator",
            "measurements",
            "not_suitable_for",
            "notes",
        }
        missing = sorted(required_event - set(record))
        if missing:
            raise ValueError(f"Operational event metadata missing: {', '.join(missing)}")
        key = (str(record["city"]), str(record["event_id"]))
        if key in event_keys:
            raise ValueError(f"Duplicate operational event record: {key[0]} {key[1]}")
        event_keys.add(key)
        if record["city"] not in HOST_CITIES or record["source_id"] not in sources:
            raise ValueError(f"Operational event {key} has an invalid city or source")
        measurements = record["measurements"]
        if not isinstance(measurements, Mapping) or not measurements:
            raise ValueError(f"Operational event {key} has no measurements")
        for measurement_id, measurement in measurements.items():
            if not isinstance(measurement, Mapping):
                raise ValueError(f"Operational event measurement {key} {measurement_id} must be an object")
            if not {"value", "unit", "status", "interpretation"}.issubset(measurement):
                raise ValueError(f"Operational event measurement {key} {measurement_id} is incomplete")
            if str(measurement["status"]) not in VALID_STATUSES:
                raise ValueError(f"Operational event measurement {key} {measurement_id} has an invalid status")
            if not isinstance(measurement["value"], (int, float)) or not measurement["unit"]:
                raise ValueError(f"Operational event measurement {key} {measurement_id} lacks a physical value")

    for city, row in coverage.items():
        expected_count = sum(metric["city"] == city for metric in metrics)
        expected_events = sum(record["city"] == city for record in event_records)
        if row.get("metric_count") != expected_count:
            raise ValueError(f"Operational metric coverage count mismatch for {city}")
        if row.get("event_record_count") != expected_events:
            raise ValueError(f"Operational event coverage count mismatch for {city}")
        if row.get("match_hour_calibration_ready") is not False:
            raise ValueError("Published aggregate evidence must not silently qualify match-hour calibration")
        if not row.get("open_request_fields"):
            raise ValueError(f"Operational acquisition gaps missing for {city}")


def load_snapshot(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    snapshot = read_json(path)
    validate_snapshot(snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--retrieved-at", required=True, help="UTC ISO timestamp used for deterministic provenance")
    parser.add_argument("--refresh", action="store_true", help="Explicitly download official pages before building")
    args = parser.parse_args()
    if args.refresh:
        refresh_source_files(args.raw_root)
    snapshot = build_snapshot(args.raw_root, args.retrieved_at)
    write_json(args.output, snapshot)


if __name__ == "__main__":
    main()
