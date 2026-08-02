from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pytest

from dashboard.mobility_platform import contracts

ROOT = Path(__file__).parents[3]
MATRIX = ROOT / "docs" / "EVIDENCE_TO_CLAIM_MATRIX.md"
SOURCE_REGISTER = ROOT / "docs" / "SOURCE_REGISTER.md"
JUDGING_MAP = ROOT / "docs" / "JUDGING_CRITERIA.md"
PRESENTATION_FILES = (
    ROOT / "SUBMISSION_NARRATIVE.md",
    ROOT / "docs" / "DEMO_SCRIPT.md",
    ROOT / "dashboard" / "README.md",
)

PROHIBITED_POSITIVE_CLAIMS = {
    "measured congestion": re.compile(r"\b(?:measures?|measured) (?:roadway )?congestion\b", re.I),
    "visitor prediction": re.compile(r"\b(?:predicts?|predicted) (?:visitor|fan) movement\b", re.I),
    "ADA certification": re.compile(r"\b(?:is|are|certifies?|certified) ADA[- ]compliant\b", re.I),
    "causal outcome": re.compile(r"\b(?:caused|causes|proves?|proven) (?:a |the )?(?:reduction|increase|impact|effect)\b", re.I),
    "observed mode shift": re.compile(r"\bobserved mode shift\b", re.I),
}
NEGATION = re.compile(r"\b(?:not|never|no|does not|do not|must not|cannot)\b", re.I)
PRESENTATION_CONTRACTS = (
    "MatchEvent",
    "MovementScenario",
    "AccessGapResult",
    "InterventionOutcome",
    "InvestmentRecommendation",
)


def find_prohibited_positive_claims(text: str) -> list[tuple[str, str]]:
    findings = []
    for line in text.splitlines():
        if NEGATION.search(line):
            continue
        for label, pattern in PROHIBITED_POSITIVE_CLAIMS.items():
            if pattern.search(line):
                findings.append((label, line.strip()))
    return findings


def test_evidence_matrix_fields_exist_in_contract_0_3():
    text = MATRIX.read_text(encoding="utf-8")
    class_pattern = "|".join(PRESENTATION_CONTRACTS)
    references = set(re.findall(rf"`(({class_pattern})\.[a-z][a-z0-9_]*)`", text))
    assert references, "evidence matrix must reference contract fields"

    for reference, _ in references:
        class_name, field_name = reference.split(".")
        contract_type = getattr(contracts, class_name)
        field_names = {item.name for item in fields(contract_type)}
        assert field_name in field_names, f"unknown presentation field: {reference}"


def test_matrix_covers_decision_headline_metrics():
    text = MATRIX.read_text(encoding="utf-8")
    required = {
        "AccessGapResult.peak_demand_per_hour",
        "AccessGapResult.residual_passengers",
        "InterventionOutcome.gap_resolved_passengers",
        "InterventionOutcome.net_vmt_base",
        "InterventionOutcome.net_co2e_kg_base",
        "InterventionOutcome.cost_base",
        "InvestmentRecommendation.cost_per_passenger",
        "InvestmentRecommendation.lead_time_band",
        "InvestmentRecommendation.responsible_actor",
    }
    assert all(reference in text for reference in required)


def test_supplemental_source_register_is_complete_and_statuses_are_honest():
    text = SOURCE_REGISTER.read_text(encoding="utf-8")
    required_families = {
        "FIFA",
        "GTFS",
        "OpenStreetMap",
        "OSMnx",
        "EPA",
        "FTA NTD",
        "FTA Capital Cost Database",
        "FHWA/PBIC",
    }
    assert all(family in text for family in required_families)
    assert "78 US match events, observed" in text
    assert "4 observed and 2 partial cities" in text
    assert "2 failed-feed cities" in text
    assert "Integrated for all 11 venues" in text
    assert "OSMnx 2.1.0" in text
    assert "not a local MOVES inventory" in text
    assert "SHA-256" in text


def test_judging_map_covers_all_weighted_criteria():
    text = JUDGING_MAP.read_text(encoding="utf-8")
    for criterion, weight in {
        "Impact": 25,
        "Data Analytics": 20,
        "Innovation": 15,
        "Feasibility": 15,
        "Legacy": 10,
        "Visualization": 10,
        "Presentation": 5,
    }.items():
        assert f"{criterion} — {weight}" in text


def test_submission_metadata_placeholders_are_explicit_blockers():
    narrative = (ROOT / "SUBMISSION_NARRATIVE.md").read_text(encoding="utf-8")
    assert "blocking before submission" in narrative.lower()
    assert "[TEAM NAME REQUIRED]" in narrative
    assert "[NAME AND EMAIL REQUIRED]" in narrative
    assert "must not invent" in narrative


def test_presentation_surfaces_have_no_prohibited_positive_claims():
    findings = []
    for path in PRESENTATION_FILES:
        findings.extend(
            (path.relative_to(ROOT).as_posix(), label, line)
            for label, line in find_prohibited_positive_claims(path.read_text(encoding="utf-8"))
        )
    assert not findings, findings


@pytest.mark.parametrize(
    "claim",
    [
        "The dashboard measures roadway congestion.",
        "Our platform predicts visitor movement.",
        "This route is ADA-compliant.",
        "The intervention caused a reduction in traffic.",
        "The chart reports observed mode shift.",
    ],
)
def test_prohibited_positive_claims_are_caught(claim):
    assert find_prohibited_positive_claims(claim)


@pytest.mark.parametrize(
    "responsible_statement",
    [
        "The dashboard does not measure roadway congestion.",
        "The route is not an ADA certification.",
        "We do not claim observed mode shift.",
    ],
)
def test_explicit_limitations_are_allowed(responsible_statement):
    assert not find_prohibited_positive_claims(responsible_statement)
