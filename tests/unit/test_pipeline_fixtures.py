"""Fixture-based tests exercising the orchestrator's tool layer end-to-end
against an in-memory Store, covering the five scenarios required by the
spec: valid lead, duplicate lead, irrelevant company, missing contact,
incomplete data. No network access anywhere in this file.
"""
import pytest

from src.agents.contact_agent import ContactAgent
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchAgent
from src.approval.gate import ApprovalGate
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.tools import (
    tool_check_duplicate,
    tool_draft_outreach,
    tool_qualify_lead,
    tool_store_lead,
)

SCORING_CONFIG = {
    "target_industries": ["hospitality", "hotel"],
    "target_locations": ["dubai", "united arab emirates"],
    "ideal_employee_ranges": ["51,200", "201,500", "501,1000"],
    "fit_out_signal_keywords": ["new opening", "expansion", "renovation"],
    "decision_maker_titles": ["facilities manager"],
    "weights": {
        "industry_match": 30, "location_match": 20, "employee_size_fit": 15,
        "fit_out_signal": 20, "decision_maker_found": 15,
    },
    "thresholds": {"hot": 75, "warm": 50, "cold": 25},
}

VALID_COMPANY = {
    "name": "Palm Grove Hospitality Group", "domain": "palmgrovehospitality.ae",
    "industry": "hospitality", "employee_count": 620, "city": "Dubai",
    "country": "United Arab Emirates", "apollo_org_id": "org_1",
    "description": "Hotel group with a new opening in Dubai Marina.",
    "evidence": ["new opening"],
}

VALID_CONTACT = {
    "full_name": "Sara Al Mansoori", "title": "Facilities Manager",
    "email": "sara@palmgrovehospitality.ae", "email_status": "verified",
    "phone": "+971501234567", "linkedin_url": "https://linkedin.com/in/sara",
    "apollo_person_id": "p1",
}

IRRELEVANT_COMPANY = {
    "name": "Global Software Inc", "domain": "globalsoftware.com",
    "industry": "software", "employee_count": 50000, "city": "San Francisco",
    "country": "United States", "apollo_org_id": "org_2",
    "description": "A cloud software company.", "evidence": ["UNKNOWN"],
}

INCOMPLETE_COMPANY = {"name": "Mystery Trading Co"}  # everything else genuinely unknown


@pytest.fixture()
def ctx(store):
    return OrchestratorContext(
        run_id="test-run", store=store, apollo_client=None,
        research_agent=ResearchAgent(None, SCORING_CONFIG),
        qualification_agent=QualificationAgent(SCORING_CONFIG),
        contact_agent=ContactAgent(None, SCORING_CONFIG["decision_maker_titles"]),
        outreach_agent=OutreachAgent(None),
        approval_gate=ApprovalGate(non_interactive=True),
    )


class TestValidLead:
    def test_full_pipeline_produces_hot_lead(self, ctx):
        qualification = tool_qualify_lead({"company": VALID_COMPANY, "has_decision_maker": True}, ctx)
        assert qualification["classification"] == "HOT"

        stored = tool_store_lead(
            {"company": VALID_COMPANY, "contact": VALID_CONTACT, "qualification": qualification}, ctx
        )
        assert stored["company_was_new"] is True
        lead = ctx.store.leads.get(stored["lead_id"])
        assert lead.classification == "HOT"
        assert lead.contact_id is not None


class TestDuplicateLead:
    def test_second_store_reuses_company_and_does_not_duplicate(self, ctx):
        qualification = tool_qualify_lead({"company": VALID_COMPANY, "has_decision_maker": True}, ctx)
        first = tool_store_lead(
            {"company": VALID_COMPANY, "contact": VALID_CONTACT, "qualification": qualification}, ctx
        )
        dup_check = tool_check_duplicate(
            {"company_name": VALID_COMPANY["name"], "domain": VALID_COMPANY["domain"]}, ctx
        )
        assert dup_check["is_duplicate"] is True
        assert dup_check["existing_company_id"] == first["company_id"]

        second = tool_store_lead(
            {"company": VALID_COMPANY, "contact": VALID_CONTACT, "qualification": qualification}, ctx
        )
        assert second["company_id"] == first["company_id"]
        assert second["company_was_new"] is False
        assert len(ctx.store.companies.search()) == 1


class TestIrrelevantCompany:
    def test_scores_low_and_unqualified(self, ctx):
        qualification = tool_qualify_lead({"company": IRRELEVANT_COMPANY, "has_decision_maker": False}, ctx)
        assert qualification["classification"] == "UNQUALIFIED"
        assert qualification["score"] == 0


class TestMissingContact:
    def test_lead_without_contact_has_null_contact_id(self, ctx):
        qualification = tool_qualify_lead({"company": VALID_COMPANY, "has_decision_maker": False}, ctx)
        stored = tool_store_lead({"company": VALID_COMPANY, "qualification": qualification}, ctx)
        lead = ctx.store.leads.get(stored["lead_id"])
        assert lead.contact_id is None

    def test_drafting_outreach_without_contact_raises(self, ctx):
        qualification = tool_qualify_lead({"company": VALID_COMPANY, "has_decision_maker": False}, ctx)
        stored = tool_store_lead({"company": VALID_COMPANY, "qualification": qualification}, ctx)
        with pytest.raises(ValueError, match="no contact"):
            tool_draft_outreach({"lead_id": stored["lead_id"]}, ctx)


class TestIncompleteData:
    def test_missing_fields_become_unknown_and_do_not_crash(self, ctx):
        qualification = tool_qualify_lead({"company": INCOMPLETE_COMPANY, "has_decision_maker": False}, ctx)
        assert qualification["classification"] == "UNQUALIFIED"

        stored = tool_store_lead({"company": INCOMPLETE_COMPANY, "qualification": qualification}, ctx)
        company_record = ctx.store.companies.get(stored["company_id"])
        assert company_record.name == "Mystery Trading Co"
        assert company_record.domain is None
        assert company_record.industry is None
