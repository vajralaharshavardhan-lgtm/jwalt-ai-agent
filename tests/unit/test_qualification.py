import pytest

from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchedCompany

SCORING_CONFIG = {
    "target_industries": ["hospitality", "hotel"],
    "target_locations": ["dubai", "united arab emirates"],
    "ideal_employee_ranges": ["51,200", "201,500", "501,1000"],
    "fit_out_signal_keywords": ["new opening", "expansion", "renovation"],
    "weights": {
        "industry_match": 30,
        "location_match": 20,
        "employee_size_fit": 15,
        "fit_out_signal": 20,
        "decision_maker_found": 15,
    },
    "thresholds": {"hot": 75, "warm": 50, "cold": 25},
}


def make_company(**overrides) -> ResearchedCompany:
    defaults = dict(
        name="ABC Hotels", domain="abchotels.com", industry="hospitality",
        employee_count=300, city="Dubai", country="United Arab Emirates",
        apollo_org_id="org_1", description="Hotel group planning a new opening in Dubai Marina.",
        evidence=["new opening"],
    )
    defaults.update(overrides)
    return ResearchedCompany(**defaults)


@pytest.fixture()
def agent():
    return QualificationAgent(SCORING_CONFIG)


class TestQualificationAgent:
    def test_perfect_match_is_hot(self, agent):
        result = agent.qualify(make_company(), has_decision_maker=True)
        assert result.score == 100
        assert result.classification == "HOT"
        assert result.signals["industry_match"] is True
        assert result.signals["decision_maker_found"] is True

    def test_irrelevant_company_is_unqualified(self, agent):
        company = make_company(
            industry="software", city="San Francisco", country="United States",
            employee_count=15000, description="A cloud software company.", evidence=["UNKNOWN"],
        )
        result = agent.qualify(company, has_decision_maker=False)
        assert result.score == 0
        assert result.classification == "UNQUALIFIED"

    def test_missing_decision_maker_lowers_score_but_can_stay_qualified(self, agent):
        with_dm = agent.qualify(make_company(), has_decision_maker=True)
        without_dm = agent.qualify(make_company(), has_decision_maker=False)
        assert without_dm.score == with_dm.score - SCORING_CONFIG["weights"]["decision_maker_found"]

    def test_unknown_employee_count_does_not_crash_and_does_not_match(self, agent):
        company = make_company(employee_count="UNKNOWN")
        result = agent.qualify(company, has_decision_maker=True)
        assert result.signals["employee_size_fit"] is False

    def test_classification_thresholds(self, agent):
        # industry(30) + location(20) = 50 -> WARM boundary
        company = make_company(employee_count="UNKNOWN", evidence=["UNKNOWN"])
        result = agent.qualify(company, has_decision_maker=False)
        assert result.score == 50
        assert result.classification == "WARM"

    def test_explanation_lists_each_signal(self, agent):
        result = agent.qualify(make_company(), has_decision_maker=True)
        for signal_name in result.signals:
            assert signal_name.replace("_", " ") in result.explanation
