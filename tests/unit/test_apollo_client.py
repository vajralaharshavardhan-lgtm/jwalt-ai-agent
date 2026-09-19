"""Unit tests for request construction, auth, and budget enforcement --
no real HTTP calls (the session's post/get is monkeypatched). Real-API
behavior is covered separately in tests/integration/test_apollo_integration.py,
which only runs when explicitly enabled.
"""
import pytest

from src.tools.apollo_client import ApolloAuthError, ApolloBudgetExceededError, ApolloClient


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


class TestApolloClientAuth:
    def test_missing_api_key_raises_before_any_request(self):
        client = ApolloClient(api_key=None)
        with pytest.raises(ApolloAuthError):
            client.search_organizations()

    def test_401_response_raises_auth_error(self, monkeypatch):
        client = ApolloClient(api_key="fake-key")
        monkeypatch.setattr(client._session, "post", lambda *a, **k: FakeResponse(status_code=401))
        with pytest.raises(ApolloAuthError):
            client.search_organizations()


class TestApolloClientBudget:
    def test_stops_after_max_requests(self, monkeypatch):
        client = ApolloClient(api_key="fake-key", max_requests_per_run=2)
        monkeypatch.setattr(client._session, "post", lambda *a, **k: FakeResponse(json_data={"organizations": []}))

        client.search_organizations()
        client.search_organizations()
        assert client.requests_made == 2
        assert client.requests_remaining == 0

        with pytest.raises(ApolloBudgetExceededError):
            client.search_organizations()

    def test_bulk_enrich_rejects_more_than_ten_domains(self):
        client = ApolloClient(api_key="fake-key")
        with pytest.raises(ValueError):
            client.bulk_enrich_organizations([f"d{i}.com" for i in range(11)])


class TestApolloClientRequestConstruction:
    def test_search_organizations_sends_expected_body(self, monkeypatch):
        client = ApolloClient(api_key="fake-key")
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse(json_data={"organizations": []})

        monkeypatch.setattr(client._session, "post", fake_post)
        client.search_organizations(locations=["Dubai, United Arab Emirates"], per_page=5)

        assert captured["url"].endswith("/mixed_companies/search")
        assert captured["headers"]["x-api-key"] == "fake-key"
        assert captured["json"]["organization_locations"] == ["Dubai, United Arab Emirates"]
        assert captured["json"]["per_page"] == 5
