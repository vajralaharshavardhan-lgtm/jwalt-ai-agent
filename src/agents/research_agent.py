"""Research Agent: turns a plain-language target ("Dubai hotel clients") into
Apollo search filters, fetches company candidates, and returns structured,
evidence-backed records.

Hard rule (Phase 4 of the spec): never invent a project, contact, or fact.
Any field Apollo doesn't provide comes back as the literal string "UNKNOWN",
and "evidence of relevance" is only ever a direct quote/match against a real
field (industry, keywords, or description) -- never a generated guess.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.common import UNKNOWN, or_unknown
from src.tools.apollo_client import ApolloClient
from src.tools.apollo_parser import parse_organization


@dataclass
class ResearchCriteria:
    """What the user asked for, normalized into Apollo-searchable filters."""
    locations: list[str] = field(default_factory=lambda: ["Dubai, United Arab Emirates"])
    industry_keywords: list[str] | None = None  # e.g. ["hotel", "hospitality"]
    employee_ranges: list[str] | None = None
    target_count: int = 10
    max_pages: int = 3


@dataclass
class ResearchedCompany:
    name: str
    domain: str
    industry: str
    employee_count: str | int
    city: str
    country: str
    apollo_org_id: str
    description: str
    evidence: list[str]
    source: str = "apollo"


def extract_evidence(parsed_org: dict, fit_out_signal_keywords: list[str]) -> list[str]:
    """Returns the subset of configured signal keywords that literally appear
    in the company's description or Apollo keyword tags. Empty list (not a
    guess) if none match -- the caller renders that as ["UNKNOWN"].
    """
    haystack_parts = []
    if parsed_org.get("description"):
        haystack_parts.append(parsed_org["description"].lower())
    haystack_parts.extend(k.lower() for k in (parsed_org.get("keywords") or []))
    haystack = " | ".join(haystack_parts)

    matched = [kw for kw in fit_out_signal_keywords if kw.lower() in haystack]
    return matched


class ResearchAgent:
    def __init__(self, apollo_client: ApolloClient, scoring_config: dict):
        self._apollo = apollo_client
        self._fit_out_keywords = scoring_config.get("fit_out_signal_keywords", [])

    def research(self, criteria: ResearchCriteria) -> list[ResearchedCompany]:
        results: list[ResearchedCompany] = []
        page = 1
        while len(results) < criteria.target_count and page <= criteria.max_pages:
            raw = self._apollo.search_organizations(
                locations=criteria.locations,
                keyword_tags=criteria.industry_keywords,
                employee_ranges=criteria.employee_ranges,
                page=page,
                per_page=min(25, criteria.target_count * 2),
            )
            orgs = raw.get("organizations", [])
            if not orgs:
                break
            for raw_org in orgs:
                if len(results) >= criteria.target_count:
                    break
                parsed = parse_organization(raw_org)
                evidence = extract_evidence(parsed, self._fit_out_keywords)
                results.append(
                    ResearchedCompany(
                        name=or_unknown(parsed["name"]),
                        domain=or_unknown(parsed["domain"]),
                        industry=or_unknown(parsed["industry"]),
                        employee_count=or_unknown(parsed["employee_count"]),
                        city=or_unknown(parsed["city"]),
                        country=or_unknown(parsed["country"]),
                        apollo_org_id=or_unknown(parsed["apollo_org_id"]),
                        description=or_unknown(parsed["description"]),
                        evidence=evidence if evidence else [UNKNOWN],
                    )
                )
            total_pages = raw.get("pagination", {}).get("total_pages", page)
            if page >= total_pages:
                break
            page += 1
        return results
