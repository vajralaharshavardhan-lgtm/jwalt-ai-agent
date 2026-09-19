"""Real Apollo API calls. Skipped by default -- these consume real credits
and require real network access to api.apollo.io.

Run explicitly with:
    RUN_APOLLO_INTEGRATION_TESTS=1 pytest tests/integration/test_apollo_integration.py -m apollo_integration

Note from development of this project: the sandboxed environment these
files were originally built in has its network egress policy configured to
block outbound HTTPS to api.apollo.io outright (confirmed via a 403 policy
denial on the CONNECT, not a timeout). That means these tests could not be
executed during development, regardless of whether an API key was
available. They are included so they CAN be run for real in an environment
with normal internet access and a real APOLLO_API_KEY -- do not treat their
mere presence as evidence the integration has been verified end-to-end.
"""
import os

import pytest

from src.config import get_settings
from src.tools.apollo_client import ApolloClient

RUN_INTEGRATION = os.getenv("RUN_APOLLO_INTEGRATION_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_APOLLO_INTEGRATION_TESTS=1 to run real, credit-consuming Apollo API tests.",
)


@pytest.fixture()
def client() -> ApolloClient:
    settings = get_settings()
    if not settings.apollo_api_key:
        pytest.skip("APOLLO_API_KEY not set")
    return ApolloClient(
        api_key=settings.apollo_api_key,
        base_url=settings.apollo_base_url,
        timeout_seconds=settings.apollo_timeout_seconds,
        max_requests_per_run=5,
    )


@pytest.mark.apollo_integration
def test_search_organizations_returns_real_shape(client):
    result = client.search_organizations(
        locations=["Dubai, United Arab Emirates"], employee_ranges=["51,200"], per_page=1
    )
    assert "organizations" in result


@pytest.mark.apollo_integration
def test_enrich_organization_for_known_domain(client):
    org = client.enrich_organization("apollo.io")
    assert org is None or org.get("name")
