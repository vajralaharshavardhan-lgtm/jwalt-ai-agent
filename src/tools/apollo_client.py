"""Thin REST client over Apollo.io's public API.

Endpoints mirror the Apollo MCP tool surface that was inspected and verified
live against the connected Apollo account during development (see README
"Apollo setup" for what was actually verified and how). They follow Apollo's
long-stable v1 API shape:

    POST {base_url}/mixed_companies/search   -- paid, full company search
    GET  {base_url}/organizations/enrich      -- paid, single company enrich
    POST {base_url}/organizations/bulk_enrich -- paid, up to 10 companies
    POST {base_url}/mixed_people/search       -- paid, people prospecting
    POST {base_url}/people/match              -- paid, single person enrich

IMPORTANT — honestly flagging a real limitation found during development:
this project was built inside a sandboxed environment whose network egress
policy explicitly blocks outbound HTTPS to api.apollo.io (confirmed via a
403 policy denial on the CONNECT, not a timeout or DNS failure). That means
these calls could NOT be live-tested from inside that sandbox, regardless of
API key. Nothing here was invented to paper over that: the code below has
only been verified for correct request construction and response parsing
against representative captured payloads (tests/fixtures/apollo_*.json). It
must be exercised against the real API from an environment with normal
internet access, with a real APOLLO_API_KEY, before being trusted in
production. See tests/integration/test_apollo_integration.py.

There is no confirmed FREE discovery endpoint in Apollo's public REST API
(the MCP tool's free "organization lookup" appears to be a capability of
Apollo's own MCP server, not a documented public REST endpoint) — so company
discovery here goes through the paid Organization Search endpoint. Credit
usage is bounded by `max_requests_per_run` and every call is counted.
"""
from __future__ import annotations

import requests


class ApolloError(Exception):
    """Base class for Apollo client errors."""


class ApolloAuthError(ApolloError):
    """Raised when APOLLO_API_KEY is missing or rejected."""


class ApolloBudgetExceededError(ApolloError):
    """Raised when a run would exceed the configured Apollo request budget."""


class ApolloClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.apollo.io/v1",
        timeout_seconds: int = 30,
        max_requests_per_run: int = 25,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_requests = max_requests_per_run
        self._requests_made = 0
        self._session = requests.Session()

    @property
    def requests_made(self) -> int:
        return self._requests_made

    @property
    def requests_remaining(self) -> int:
        return max(0, self._max_requests - self._requests_made)

    def _check_budget(self) -> None:
        if self._requests_made >= self._max_requests:
            raise ApolloBudgetExceededError(
                f"Apollo request budget exhausted for this run "
                f"({self._requests_made}/{self._max_requests}). "
                "Raise apollo.max_requests_per_run in config/settings.yaml if this run genuinely needs more."
            )

    def _headers(self) -> dict:
        if not self._api_key:
            raise ApolloAuthError(
                "APOLLO_API_KEY is not set. Add it to .env (see .env.example). "
                "Refusing to call Apollo without real credentials."
            )
        return {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

    def _post(self, path: str, json_body: dict) -> dict:
        self._check_budget()
        resp = self._session.post(
            f"{self._base_url}{path}",
            headers=self._headers(),
            json=json_body,
            timeout=self._timeout,
        )
        self._requests_made += 1
        if resp.status_code == 401:
            raise ApolloAuthError(f"Apollo rejected the API key (401) calling {path}")
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict) -> dict:
        self._check_budget()
        resp = self._session.get(
            f"{self._base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=self._timeout,
        )
        self._requests_made += 1
        if resp.status_code == 401:
            raise ApolloAuthError(f"Apollo rejected the API key (401) calling {path}")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Company discovery / enrichment
    # ------------------------------------------------------------------

    def search_organizations(
        self,
        *,
        locations: list[str] | None = None,
        keyword_tags: list[str] | None = None,
        employee_ranges: list[str] | None = None,
        name: str | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict:
        """Paid: 1 credit per request that returns >=1 result."""
        body: dict = {"page": page, "per_page": per_page}
        if locations:
            body["organization_locations"] = locations
        if keyword_tags:
            body["q_organization_keyword_tags"] = keyword_tags
        if employee_ranges:
            body["organization_num_employees_ranges"] = employee_ranges
        if name:
            body["q_organization_name"] = name
        return self._post("/mixed_companies/search", body)

    def enrich_organization(self, domain: str) -> dict | None:
        """Paid: 1 credit if found, 0 if not. Returns None on no match."""
        data = self._get("/organizations/enrich", {"domain": domain})
        return data.get("organization")

    def bulk_enrich_organizations(self, domains: list[str]) -> dict:
        """Paid: 1 credit per matched company. Max 10 domains per call."""
        if len(domains) > 10:
            raise ValueError("Apollo bulk_enrich_organizations accepts at most 10 domains per call")
        return self._post("/organizations/bulk_enrich", {"domains": domains})

    # ------------------------------------------------------------------
    # People discovery / enrichment
    # ------------------------------------------------------------------

    def search_people(
        self,
        *,
        organization_ids: list[str] | None = None,
        organization_domains: list[str] | None = None,
        titles: list[str] | None = None,
        seniorities: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict:
        """Paid. Does not return emails/phones — call match_person to enrich."""
        body: dict = {"page": page, "per_page": per_page}
        if organization_ids:
            body["organization_ids"] = organization_ids
        if organization_domains:
            body["q_organization_domains_list"] = organization_domains
        if titles:
            body["person_titles"] = titles
        if seniorities:
            body["person_seniorities"] = seniorities
        return self._post("/mixed_people/search", body)

    def match_person(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        name: str | None = None,
        organization_name: str | None = None,
        domain: str | None = None,
        email: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict | None:
        """Paid single-person enrichment. Does NOT request phone reveal or
        waterfall enrichment (those are async, higher-cost, and out of scope
        for the MVP) — only standard match fields, including verified work
        email when Apollo has one.
        """
        body = {
            k: v
            for k, v in {
                "first_name": first_name,
                "last_name": last_name,
                "name": name,
                "organization_name": organization_name,
                "domain": domain,
                "email": email,
                "linkedin_url": linkedin_url,
            }.items()
            if v
        }
        data = self._post("/people/match", body)
        return data.get("person")
