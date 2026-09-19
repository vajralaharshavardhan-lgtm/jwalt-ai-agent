"""Dry-run mode: exercises the full pipeline (search -> dedupe -> qualify ->
store -> contact -> draft -> approval -> report) with two safety guarantees
that hold regardless of what's in .env:

  1. It NEVER writes to the real database file (data/leads.db). It always
     uses a throwaway in-memory SQLite database, so re-running it never
     pollutes your real lead data.
  2. It NEVER sends anything -- there is no send path anywhere in this
     codebase, dry-run or not.

Within those guarantees, dry-run is intentionally *not* fully offline by
default: if APOLLO_API_KEY / ANTHROPIC_API_KEY are configured, it uses the
real Apollo search and real LLM drafting, because that is the only way to
verify those integrations actually work end-to-end without risking real
data. If a key is missing, that step is announced as "WOULD ..." and falls
back to bundled synthetic example data instead of failing outright, so the
command below always works, even straight after cloning with no .env at all:

    python -m src.main --dry-run

Every step is printed with an explicit WOULD-prefixed label for whichever
part of it is simulated, plus the run's normal audit log entries, so a
report generated from a dry run is clearly distinguishable from a real one.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from src.agents.contact_agent import ContactAgent, ResearchedContact
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchAgent, ResearchCriteria
from src.approval.gate import ApprovalGate
from src.config import Settings
from src.memory.store import Store
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.tools import (
    tool_check_duplicate,
    tool_draft_outreach,
    tool_find_contacts,
    tool_generate_report,
    tool_qualify_lead,
    tool_request_human_approval,
    tool_search_companies,
    tool_store_lead,
)
from src.tools.llm_client import LLMClient

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class StubApolloClient:
    """Duck-types the ApolloClient methods the agents call, returning the
    bundled synthetic fixtures with zero network access. Used when no
    APOLLO_API_KEY is configured, or always in dry-run if you prefer
    (see run_dry_run's `force_offline` argument).
    """

    def __init__(self):
        self.requests_made = 0
        self.requests_remaining = "N/A (stub client, no real budget)"

    def search_organizations(self, **kwargs) -> dict:
        self.requests_made += 1
        return _load_fixture("apollo_org_search_response.json")

    def search_people(self, **kwargs) -> dict:
        self.requests_made += 1
        return _load_fixture("apollo_people_search_response.json")

    def match_person(self, **kwargs) -> dict | None:
        self.requests_made += 1
        return _load_fixture("apollo_person_match_response.json")["person"]


class StubLLMClient(LLMClient):
    """Canned response for the bundled fixture scenario -- used when no
    ANTHROPIC_API_KEY is configured, so `--dry-run` never requires network access.
    """

    def complete(self, *, system: str, user: str, max_tokens: int = 1024) -> str:
        return json.dumps(
            {
                "subject": "Interior fit-out support for your new Dubai Marina property",
                "body": (
                    "Hi Sara,\n\nCongratulations on Palm Grove Hospitality Group's expansion with "
                    "the new flagship property in Dubai Marina. J-WALT specializes in interior "
                    "fit-out for hospitality projects across the UAE, and we'd welcome the chance "
                    "to support your build-out timeline.\n\nWould you be open to a short call this "
                    "week to discuss your project needs?\n\nBest regards,\nThe J-WALT Team"
                ),
                "personalization_evidence": [
                    "evidence_of_fit_out_need: new hotel opening",
                    "company_name: Palm Grove Hospitality Group",
                    "city: Dubai",
                ],
            }
        )


def _announce(label: str, detail: str) -> None:
    print(f"[DRY RUN] {label}: {detail}")


def run_dry_run(settings: Settings) -> str:
    run_id = f"dryrun-{uuid.uuid4().hex[:8]}"
    print(f"\n{'#' * 60}\n# DRY RUN -- run_id={run_id}\n# No writes to {settings.resolved_db_path()} will occur.\n# Nothing will be sent -- there is no send path in this codebase.\n{'#' * 60}")

    store = Store(":memory:")

    apollo_is_real = bool(settings.apollo_api_key)
    if apollo_is_real:
        from src.tools.apollo_client import ApolloClient
        apollo_client = ApolloClient(
            api_key=settings.apollo_api_key, base_url=settings.apollo_base_url,
            timeout_seconds=settings.apollo_timeout_seconds,
            max_requests_per_run=settings.apollo_max_requests_per_run,
        )
        _announce("SEARCH", "APOLLO_API_KEY is configured -- using the real Apollo API (read-only calls)")
    else:
        apollo_client = StubApolloClient()
        _announce("SEARCH", "no APOLLO_API_KEY configured -- WOULD SEARCH Apollo; using bundled synthetic example data instead")

    llm_is_real = bool(settings.anthropic_api_key)
    if llm_is_real:
        from src.tools.llm_client import AnthropicLLMClient
        llm_client = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.orchestrator_model)
        _announce("DRAFT", "ANTHROPIC_API_KEY is configured -- outreach drafting will call the real LLM")
    else:
        llm_client = StubLLMClient()
        _announce("DRAFT", "no ANTHROPIC_API_KEY configured -- WOULD DRAFT via LLM; using a canned example draft instead")

    scoring_config = settings.raw_scoring
    research_agent = ResearchAgent(apollo_client, scoring_config)
    qualification_agent = QualificationAgent(scoring_config)
    contact_agent = ContactAgent(apollo_client, scoring_config.get("decision_maker_titles", []))
    outreach_agent = OutreachAgent(llm_client)
    approval_gate = ApprovalGate(non_interactive=True)

    ctx = OrchestratorContext(
        run_id=run_id, store=store, apollo_client=apollo_client, research_agent=research_agent,
        qualification_agent=qualification_agent, contact_agent=contact_agent,
        outreach_agent=outreach_agent, approval_gate=approval_gate,
    )

    # 1. Research
    search_result = tool_search_companies(
        {"locations": ["Dubai, United Arab Emirates"], "target_count": 1}, ctx
    )
    company = search_result["companies"][0]
    _announce("CREATE", f"researched company '{company['name']}' ({company['domain']})")

    # 2. First pass: not a duplicate yet
    dup_check = tool_check_duplicate({"company_name": company["name"], "domain": company["domain"]}, ctx)
    _announce("CHECK", f"duplicate check for '{company['name']}': is_duplicate={dup_check['is_duplicate']}")

    # 3. Contacts
    contacts_result = tool_find_contacts({"company": company}, ctx)
    contact = contacts_result["contacts"][0] if contacts_result["contacts"] else None
    _announce("CREATE", f"found contact: {contact['full_name'] if contact else 'none'}")

    # 4. Qualify
    qualification = tool_qualify_lead({"company": company, "has_decision_maker": bool(contact)}, ctx)
    _announce("CLASSIFY", f"{company['name']} -> {qualification['classification']} (score {qualification['score']})")

    # 5. Store (this is the actual "WOULD CREATE" persistence step -- in-memory only)
    stored = tool_store_lead({"company": company, "contact": contact, "qualification": qualification}, ctx)
    _announce("CREATE", f"lead_id={stored['lead_id']} company_was_new={stored['company_was_new']} (in-memory only, not written to {settings.resolved_db_path()})")

    # 6. Re-run research + store for the SAME company to demonstrate dedupe (WOULD UPDATE, not duplicate-create)
    dup_check_2 = tool_check_duplicate({"company_name": company["name"], "domain": company["domain"]}, ctx)
    _announce("UPDATE", f"second pass for the same company: is_duplicate={dup_check_2['is_duplicate']} (existing_company_id={dup_check_2['existing_company_id']}) -- no new row created")

    # 7. Draft outreach (never sent)
    if contact:
        draft = tool_draft_outreach({"lead_id": stored["lead_id"]}, ctx)
        _announce("DRAFT", f"subject={draft['subject']!r}")

        # 8. Approval gate (auto-reject in dry-run -- no human is present)
        approval = tool_request_human_approval({"outreach_event_id": draft["outreach_event_id"]}, ctx)
        _announce("SEND", f"blocked -- decision={approval['decision']} (dry-run auto-rejects; there is no send integration in this codebase regardless)")
    else:
        _announce("DRAFT", "skipped -- no contact found for this company")

    # 9. Report
    report = tool_generate_report({}, ctx)
    print("\n" + report["report_text"])

    store.close()
    return run_id
