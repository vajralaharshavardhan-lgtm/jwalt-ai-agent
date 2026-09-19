import json
from pathlib import Path

from src.agents.research_agent import ResearchAgent, ResearchCriteria, extract_evidence
from src.tools.apollo_parser import parse_organization

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

SCORING_CONFIG = {"fit_out_signal_keywords": ["new opening", "expansion", "renovation", "new hotel"]}


class FakeApolloClient:
    """Duck-types the ApolloClient surface ResearchAgent needs, no network."""

    def __init__(self, response: dict):
        self._response = response
        self.calls = []

    def search_organizations(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestExtractEvidence:
    def test_matches_keyword_present_in_keyword_tags(self):
        raw = load_fixture("apollo_org_search_response.json")["organizations"][0]
        parsed = parse_organization(raw)
        evidence = extract_evidence(parsed, SCORING_CONFIG["fit_out_signal_keywords"])
        # "new hotel opening" is a real Apollo keyword tag on the fixture -> "new hotel" matches.
        assert evidence == ["new hotel"]
        # "expansion" must NOT match: the description says "expanding", not "expansion" --
        # extract_evidence is a literal substring match, never a semantic guess.
        assert "expansion" not in evidence

    def test_no_match_returns_empty_list(self):
        parsed = {"description": "A boring logistics company.", "keywords": ["logistics"]}
        assert extract_evidence(parsed, SCORING_CONFIG["fit_out_signal_keywords"]) == []


class TestResearchAgent:
    def test_returns_structured_company_with_evidence(self):
        fixture = load_fixture("apollo_org_search_response.json")
        client = FakeApolloClient(fixture)
        agent = ResearchAgent(client, SCORING_CONFIG)

        results = agent.research(ResearchCriteria(target_count=1))

        assert len(results) == 1
        company = results[0]
        assert company.name == "Palm Grove Hospitality Group"
        assert company.domain == "palmgrovehospitality.ae"
        assert company.evidence != ["UNKNOWN"]  # description mentions "new hotel"/"expanding"

    def test_missing_fields_become_unknown_not_invented(self):
        sparse_response = {
            "organizations": [{"name": "Mystery Corp"}],  # everything else absent
            "pagination": {"page": 1, "total_pages": 1},
        }
        client = FakeApolloClient(sparse_response)
        agent = ResearchAgent(client, SCORING_CONFIG)

        results = agent.research(ResearchCriteria(target_count=1))

        company = results[0]
        assert company.name == "Mystery Corp"
        assert company.domain == "UNKNOWN"
        assert company.industry == "UNKNOWN"
        assert company.city == "UNKNOWN"
        assert company.evidence == ["UNKNOWN"]

    def test_stops_at_target_count(self):
        fixture = {
            "organizations": [{"name": f"Company {i}"} for i in range(5)],
            "pagination": {"page": 1, "total_pages": 1},
        }
        client = FakeApolloClient(fixture)
        agent = ResearchAgent(client, SCORING_CONFIG)

        results = agent.research(ResearchCriteria(target_count=2))
        assert len(results) == 2

    def test_no_results_returns_empty_list(self):
        client = FakeApolloClient({"organizations": [], "pagination": {"page": 1, "total_pages": 1}})
        agent = ResearchAgent(client, SCORING_CONFIG)
        assert agent.research(ResearchCriteria(target_count=5)) == []
