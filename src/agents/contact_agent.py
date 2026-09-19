"""Contact Agent: finds and (selectively) enriches decision-makers at a
researched company.

Credit-conscious by design: `find_decision_makers` only searches (titles,
names -- emails usually come back masked/unavailable at this stage).
`enrich_top_contact` is a separate, explicit step that spends a credit to
reveal verified contact details for exactly one person, so the orchestrator
decides when that cost is worth paying rather than it happening implicitly.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agents.common import UNKNOWN, or_unknown
from src.agents.research_agent import ResearchedCompany
from src.tools.apollo_client import ApolloClient
from src.tools.apollo_parser import parse_person


@dataclass
class ResearchedContact:
    full_name: str
    title: str
    email: str
    email_status: str
    phone: str
    linkedin_url: str
    apollo_person_id: str
    source: str = "apollo"


class ContactAgent:
    def __init__(self, apollo_client: ApolloClient, decision_maker_titles: list[str]):
        self._apollo = apollo_client
        self._titles = decision_maker_titles

    def find_decision_makers(
        self, company: ResearchedCompany, *, max_results: int = 3
    ) -> list[ResearchedContact]:
        if company.domain == UNKNOWN:
            return []
        raw = self._apollo.search_people(
            organization_domains=[company.domain],
            titles=self._titles,
            per_page=max_results,
        )
        contacts = []
        for raw_person in raw.get("people", [])[:max_results]:
            parsed = parse_person(raw_person)
            contacts.append(
                ResearchedContact(
                    full_name=or_unknown(parsed["full_name"]),
                    title=or_unknown(parsed["title"]),
                    email=or_unknown(parsed["email"]),
                    email_status=or_unknown(parsed["email_status"]),
                    phone=or_unknown(parsed["phone"]),
                    linkedin_url=or_unknown(parsed["linkedin_url"]),
                    apollo_person_id=or_unknown(parsed["apollo_person_id"]),
                )
            )
        return contacts

    def enrich_top_contact(
        self, company: ResearchedCompany, contact: ResearchedContact
    ) -> ResearchedContact:
        """Spends one Apollo credit to attempt to reveal a verified work email
        for a single already-identified contact. Returns the contact
        unchanged if Apollo has no match or the domain is unknown.
        """
        if company.domain == UNKNOWN or contact.apollo_person_id == UNKNOWN:
            return contact
        raw_person = self._apollo.match_person(
            name=None if contact.full_name == UNKNOWN else contact.full_name,
            organization_name=None if company.name == UNKNOWN else company.name,
            domain=company.domain,
        )
        if not raw_person:
            return contact
        parsed = parse_person(raw_person)
        return ResearchedContact(
            full_name=or_unknown(parsed["full_name"] or contact.full_name),
            title=or_unknown(parsed["title"] or contact.title),
            email=or_unknown(parsed["email"]),
            email_status=or_unknown(parsed["email_status"]),
            phone=or_unknown(parsed["phone"]),
            linkedin_url=or_unknown(parsed["linkedin_url"] or contact.linkedin_url),
            apollo_person_id=or_unknown(parsed["apollo_person_id"] or contact.apollo_person_id),
        )
