"""Qualification Agent: deterministic, config-driven lead scoring.

Deliberately NOT an LLM call. Qualification decisions need to be reliable,
testable, and explainable to a human approver -- a fixed rubric (read from
config/scoring.yaml, see src/config.py) gives repeatable scores for the same
inputs, which an LLM judgment would not.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agents.common import UNKNOWN
from src.agents.research_agent import ResearchedCompany


@dataclass
class QualificationResult:
    classification: str  # HOT | WARM | COLD | UNQUALIFIED
    score: int
    explanation: str
    signals: dict[str, bool]


def _parse_employee_ranges(ranges: list[str]) -> list[tuple[int, int]]:
    parsed = []
    for r in ranges:
        lo, hi = r.split(",")
        parsed.append((int(lo), int(hi)))
    return parsed


class QualificationAgent:
    def __init__(self, scoring_config: dict):
        self._target_industries = [i.lower() for i in scoring_config.get("target_industries", [])]
        self._target_locations = [l.lower() for l in scoring_config.get("target_locations", [])]
        self._ideal_ranges = _parse_employee_ranges(scoring_config.get("ideal_employee_ranges", []))
        self._weights = scoring_config.get("weights", {})
        self._thresholds = scoring_config.get("thresholds", {"hot": 75, "warm": 50, "cold": 25})

    def _industry_matches(self, company: ResearchedCompany) -> bool:
        haystack = f"{company.industry} {company.description}".lower()
        return any(target in haystack for target in self._target_industries)

    def _location_matches(self, company: ResearchedCompany) -> bool:
        haystack = f"{company.city} {company.country}".lower()
        return any(target in haystack for target in self._target_locations)

    def _employee_size_fits(self, company: ResearchedCompany) -> bool:
        if company.employee_count == UNKNOWN:
            return False
        try:
            count = int(company.employee_count)
        except (ValueError, TypeError):
            return False
        return any(lo <= count <= hi for lo, hi in self._ideal_ranges)

    def _has_fit_out_signal(self, company: ResearchedCompany) -> bool:
        return bool(company.evidence) and company.evidence != [UNKNOWN]

    def qualify(self, company: ResearchedCompany, *, has_decision_maker: bool) -> QualificationResult:
        signals = {
            "industry_match": self._industry_matches(company),
            "location_match": self._location_matches(company),
            "employee_size_fit": self._employee_size_fits(company),
            "fit_out_signal": self._has_fit_out_signal(company),
            "decision_maker_found": has_decision_maker,
        }

        score = sum(self._weights.get(name, 0) for name, matched in signals.items() if matched)

        if score >= self._thresholds.get("hot", 75):
            classification = "HOT"
        elif score >= self._thresholds.get("warm", 50):
            classification = "WARM"
        elif score >= self._thresholds.get("cold", 25):
            classification = "COLD"
        else:
            classification = "UNQUALIFIED"

        lines = [f"Score {score}/100 -> {classification}."]
        for name, matched in signals.items():
            weight = self._weights.get(name, 0)
            mark = "+" if matched else " "
            lines.append(f"  [{mark}] {name.replace('_', ' ')} ({weight} pts){' matched' if matched else ' not matched'}")
        explanation = "\n".join(lines)

        return QualificationResult(
            classification=classification,
            score=score,
            explanation=explanation,
            signals=signals,
        )
