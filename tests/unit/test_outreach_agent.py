import json

import pytest

from src.agents.contact_agent import ResearchedContact
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationResult
from src.agents.research_agent import ResearchedCompany


class FakeLLMClient:
    def __init__(self, response: str):
        self._response = response
        self.last_call = None

    def complete(self, *, system, user, max_tokens=1024):
        self.last_call = {"system": system, "user": user}
        return self._response


def make_company():
    return ResearchedCompany(
        name="ABC Hotels", domain="abchotels.com", industry="hospitality", employee_count=300,
        city="Dubai", country="United Arab Emirates", apollo_org_id="org_1",
        description="Hotel group.", evidence=["new opening"],
    )


def make_contact():
    return ResearchedContact(
        full_name="John Smith", title="Facilities Manager", email="john@abchotels.com",
        email_status="verified", phone="+971501234567", linkedin_url="https://linkedin.com/in/johnsmith",
        apollo_person_id="p1",
    )


def make_qualification():
    return QualificationResult(classification="HOT", score=90, explanation="...", signals={})


class TestOutreachAgent:
    def test_valid_json_response_is_parsed(self):
        llm = FakeLLMClient(json.dumps({
            "subject": "Hello",
            "body": "Hi John, ...",
            "personalization_evidence": ["company_name: ABC Hotels"],
        }))
        agent = OutreachAgent(llm)
        draft = agent.draft(lead_id=1, company=make_company(), contact=make_contact(), qualification=make_qualification())
        assert draft.subject == "Hello"
        assert draft.lead_id == 1
        assert "ABC Hotels" in draft.personalization_evidence[0]

    def test_only_facts_from_input_are_sent_to_the_model(self):
        llm = FakeLLMClient(json.dumps({"subject": "x", "body": "y", "personalization_evidence": []}))
        agent = OutreachAgent(llm)
        agent.draft(lead_id=1, company=make_company(), contact=make_contact(), qualification=make_qualification())
        assert "ABC Hotels" in llm.last_call["user"]
        assert "John Smith" in llm.last_call["user"]
        assert "never invent" in llm.last_call["system"].lower() or "only" in llm.last_call["system"].lower()

    def test_markdown_fenced_json_is_handled(self):
        llm = FakeLLMClient('```json\n{"subject": "Hi", "body": "...", "personalization_evidence": []}\n```')
        agent = OutreachAgent(llm)
        draft = agent.draft(lead_id=1, company=make_company(), contact=make_contact(), qualification=make_qualification())
        assert draft.subject == "Hi"

    def test_invalid_json_raises_clear_error(self):
        llm = FakeLLMClient("not json at all")
        agent = OutreachAgent(llm)
        with pytest.raises(ValueError, match="valid JSON"):
            agent.draft(lead_id=1, company=make_company(), contact=make_contact(), qualification=make_qualification())

    def test_unknown_facts_never_appear_in_prompt_as_real_values(self):
        llm = FakeLLMClient(json.dumps({"subject": "x", "body": "y", "personalization_evidence": []}))
        agent = OutreachAgent(llm)
        unknown_company = ResearchedCompany(
            name="Mystery Corp", domain="UNKNOWN", industry="UNKNOWN", employee_count="UNKNOWN",
            city="UNKNOWN", country="UNKNOWN", apollo_org_id="UNKNOWN", description="UNKNOWN",
            evidence=["UNKNOWN"],
        )
        agent.draft(lead_id=1, company=unknown_company, contact=make_contact(), qualification=make_qualification())
        # UNKNOWN fields are still shown to the model, but explicitly labeled UNKNOWN so it knows not to use them.
        assert "UNKNOWN" in llm.last_call["user"]
