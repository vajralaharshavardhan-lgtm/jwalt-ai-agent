"""The orchestrator's tool surface: Anthropic tool-use schemas plus the
Python handlers they dispatch to. Every handler takes (args, ctx) and
returns a JSON-serializable dict, or raises -- the loop (agentic_loop.py)
is responsible for catching exceptions and feeding them back to the model.

This is the ONLY file that maps "what Claude decided to call" to "what
actually runs" -- keeping that mapping in one place makes it possible to
audit exactly what an autonomous action is allowed to do.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from src.agents.common import UNKNOWN
from src.agents.contact_agent import ResearchedContact
from src.agents.qualification_agent import QualificationResult
from src.agents.research_agent import ResearchCriteria, ResearchedCompany
from src.approval.gate import ApprovalRequest
from src.orchestrator import actions as A
from src.orchestrator.context import OrchestratorContext
from src.reporting.report import ReportGenerator

TOOL_SCHEMAS = [
    {
        "name": "search_companies",
        "description": (
            "Search Apollo for candidate companies matching the given criteria. "
            "Costs Apollo credits -- call once per distinct criteria set, not repeatedly for the same one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "locations": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['Dubai, United Arab Emirates']"},
                "industry_keywords": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['hotel', 'hospitality']"},
                "employee_ranges": {"type": "array", "items": {"type": "string"}, "description": "Apollo range strings, e.g. ['51,200','201,500']"},
                "target_count": {"type": "integer", "description": "How many companies to return"},
            },
            "required": ["target_count"],
        },
    },
    {
        "name": "check_duplicate",
        "description": "Check whether a company already exists in the lead database, before doing more work on it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "domain": {"type": "string"},
            },
            "required": ["company_name"],
        },
    },
    {
        "name": "find_contacts",
        "description": "Search Apollo for decision-makers at a company. Costs Apollo credits. Pass back the exact company object returned by search_companies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "object", "description": "The company object as returned by search_companies"},
                "max_results": {"type": "integer"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "qualify_lead",
        "description": "Run the deterministic qualification rubric against a researched company to get a HOT/WARM/COLD/UNQUALIFIED classification and score. Free -- no external calls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "object", "description": "The company object as returned by search_companies"},
                "has_decision_maker": {"type": "boolean", "description": "Whether find_contacts found at least one relevant contact"},
            },
            "required": ["company", "has_decision_maker"],
        },
    },
    {
        "name": "store_lead",
        "description": "Persist a qualified company (and its contact, if any) as a lead. Applies duplicate detection automatically -- safe to call even if check_duplicate was skipped.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "object"},
                "contact": {"type": "object", "description": "Optional. The top contact object from find_contacts."},
                "qualification": {"type": "object", "description": "The object returned by qualify_lead"},
            },
            "required": ["company", "qualification"],
        },
    },
    {
        "name": "draft_outreach",
        "description": "Generate a personalized outreach email draft for a stored lead. Does NOT send anything. Requires the lead to have a contact.",
        "input_schema": {
            "type": "object",
            "properties": {"lead_id": {"type": "integer"}},
            "required": ["lead_id"],
        },
    },
    {
        "name": "request_human_approval",
        "description": "Escalate an outreach draft to a human for approve/reject/edit before it could ever be sent. This is the ONLY way an outreach draft's status changes -- always call this after draft_outreach.",
        "input_schema": {
            "type": "object",
            "properties": {"outreach_event_id": {"type": "integer"}},
            "required": ["outreach_event_id"],
        },
    },
    {
        "name": "generate_report",
        "description": "Produce the run's summary report (researched/qualified/duplicates/contacts/drafts/approvals/errors).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "finish",
        "description": "Call this exactly once, when the objective is complete or you have determined it cannot be completed. Ends the run.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string", "description": "A short human-readable summary of what was accomplished"}},
            "required": ["summary"],
        },
    },
]


def _company_from_dict(d: dict) -> ResearchedCompany:
    return ResearchedCompany(
        name=d.get("name", UNKNOWN),
        domain=d.get("domain", UNKNOWN),
        industry=d.get("industry", UNKNOWN),
        employee_count=d.get("employee_count", UNKNOWN),
        city=d.get("city", UNKNOWN),
        country=d.get("country", UNKNOWN),
        apollo_org_id=d.get("apollo_org_id", UNKNOWN),
        description=d.get("description", UNKNOWN),
        evidence=d.get("evidence") or [UNKNOWN],
    )


def _none_if_unknown(value):
    return None if value in (None, UNKNOWN) else value


def tool_search_companies(args: dict, ctx: OrchestratorContext) -> dict:
    criteria = ResearchCriteria(
        locations=args.get("locations") or ["Dubai, United Arab Emirates"],
        industry_keywords=args.get("industry_keywords"),
        employee_ranges=args.get("employee_ranges"),
        target_count=int(args.get("target_count", 10)),
    )
    companies = ctx.research_agent.research(criteria)
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="research_agent", action=A.RESEARCH_COMPANIES, status="SUCCESS",
        input_summary=json.dumps(asdict(criteria)), output_summary=str(len(companies)),
    )
    return {
        "companies": [asdict(c) for c in companies],
        "count": len(companies),
        "apollo_requests_remaining": ctx.apollo_client.requests_remaining,
    }


def tool_check_duplicate(args: dict, ctx: OrchestratorContext) -> dict:
    existing = ctx.store.dedupe.find_existing_company(
        domain=args.get("domain"), name=args.get("company_name", "")
    )
    if existing:
        ctx.store.run_logs.log(
            run_id=ctx.run_id, agent="orchestrator", action=A.DUPLICATE_DETECTED, status="SUCCESS",
            input_summary=args.get("company_name"), output_summary=f"existing_company_id={existing.id}",
        )
        existing_lead = ctx.store.leads.get_for_company(existing.id)
        return {
            "is_duplicate": True,
            "existing_company_id": existing.id,
            "existing_lead": asdict(existing_lead) if existing_lead else None,
        }
    return {"is_duplicate": False, "existing_company_id": None, "existing_lead": None}


def tool_find_contacts(args: dict, ctx: OrchestratorContext) -> dict:
    company = _company_from_dict(args["company"])
    contacts = ctx.contact_agent.find_decision_makers(company, max_results=int(args.get("max_results", 3)))
    if contacts:
        ctx.store.run_logs.log(
            run_id=ctx.run_id, agent="contact_agent", action=A.CONTACT_FOUND, status="SUCCESS",
            input_summary=company.name, output_summary=str(len(contacts)),
        )
    else:
        ctx.store.run_logs.log(
            run_id=ctx.run_id, agent="contact_agent", action=A.NO_CONTACT_FOUND, status="SUCCESS",
            input_summary=company.name,
        )
    return {"contacts": [asdict(c) for c in contacts]}


def tool_qualify_lead(args: dict, ctx: OrchestratorContext) -> dict:
    company = _company_from_dict(args["company"])
    result: QualificationResult = ctx.qualification_agent.qualify(
        company, has_decision_maker=bool(args.get("has_decision_maker", False))
    )
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="qualification_agent", action=A.LEAD_QUALIFIED, status="SUCCESS",
        input_summary=company.name, output_summary=result.classification,
    )
    return {
        "classification": result.classification,
        "score": result.score,
        "explanation": result.explanation,
        "signals": result.signals,
    }


def tool_store_lead(args: dict, ctx: OrchestratorContext) -> dict:
    company_dict = args["company"]
    contact_dict = args.get("contact")
    qualification = args["qualification"]

    company_record, created = ctx.store.get_or_create_company(
        name=company_dict.get("name", UNKNOWN),
        domain=_none_if_unknown(company_dict.get("domain")),
        industry=_none_if_unknown(company_dict.get("industry")),
        employee_count=str(company_dict.get("employee_count")) if _none_if_unknown(company_dict.get("employee_count")) else None,
        city=_none_if_unknown(company_dict.get("city")),
        country=_none_if_unknown(company_dict.get("country")),
        apollo_org_id=_none_if_unknown(company_dict.get("apollo_org_id")),
        description=_none_if_unknown(company_dict.get("description")),
        source="apollo",
    )

    contact_record = None
    if contact_dict and _none_if_unknown(contact_dict.get("full_name")):
        contact_record = ctx.store.dedupe.find_existing_contact(
            email=_none_if_unknown(contact_dict.get("email")),
            phone=_none_if_unknown(contact_dict.get("phone")),
        )
        if not contact_record:
            contact_record = ctx.store.contacts.create(
                company_id=company_record.id,
                full_name=contact_dict["full_name"],
                title=_none_if_unknown(contact_dict.get("title")),
                email=_none_if_unknown(contact_dict.get("email")),
                email_status=_none_if_unknown(contact_dict.get("email_status")),
                phone=_none_if_unknown(contact_dict.get("phone")),
                linkedin_url=_none_if_unknown(contact_dict.get("linkedin_url")),
                apollo_person_id=_none_if_unknown(contact_dict.get("apollo_person_id")),
                source="apollo",
            )

    lead = ctx.store.leads.create(
        company_id=company_record.id,
        contact_id=contact_record.id if contact_record else None,
        status="QUALIFIED",
        classification=qualification.get("classification"),
        score=qualification.get("score"),
        score_explanation=qualification.get("explanation"),
    )
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="orchestrator", action=A.COMPANY_STORED, status="SUCCESS",
        input_summary=company_record.name,
        output_summary=f"lead_id={lead.id} company_created={created}",
    )
    return {
        "lead_id": lead.id,
        "company_id": company_record.id,
        "contact_id": contact_record.id if contact_record else None,
        "company_was_new": created,
    }


def tool_draft_outreach(args: dict, ctx: OrchestratorContext) -> dict:
    lead_id = int(args["lead_id"])
    lead = ctx.store.leads.get(lead_id)
    if not lead:
        raise ValueError(f"No lead with id {lead_id}")
    if not lead.contact_id:
        raise ValueError(f"Lead {lead_id} has no contact -- cannot draft a personalized outreach email")

    company_record = ctx.store.companies.get(lead.company_id)
    contact_record = ctx.store.contacts.get(lead.contact_id)

    company = ResearchedCompany(
        name=company_record.name, domain=company_record.domain or UNKNOWN,
        industry=company_record.industry or UNKNOWN, employee_count=company_record.employee_count or UNKNOWN,
        city=company_record.city or UNKNOWN, country=company_record.country or UNKNOWN,
        apollo_org_id=company_record.apollo_org_id or UNKNOWN, description=company_record.description or UNKNOWN,
        evidence=[UNKNOWN],
    )
    contact = ResearchedContact(
        full_name=contact_record.full_name, title=contact_record.title or UNKNOWN,
        email=contact_record.email or UNKNOWN, email_status=contact_record.email_status or UNKNOWN,
        phone=contact_record.phone or UNKNOWN, linkedin_url=contact_record.linkedin_url or UNKNOWN,
        apollo_person_id=contact_record.apollo_person_id or UNKNOWN,
    )
    qualification = QualificationResult(
        classification=lead.classification or UNKNOWN, score=lead.score or 0,
        explanation=lead.score_explanation or "", signals={},
    )

    draft = ctx.outreach_agent.draft(lead_id=lead_id, company=company, contact=contact, qualification=qualification)
    event = ctx.store.outreach.create(
        lead_id=lead_id, contact_id=contact_record.id, event_type="DRAFT_CREATED",
        subject=draft.subject, body=draft.body,
        personalization_evidence=json.dumps(draft.personalization_evidence),
        status="PENDING_APPROVAL",
    )
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="outreach_agent", action=A.DRAFT_CREATED, status="SUCCESS",
        input_summary=f"lead_id={lead_id}", output_summary=f"event_id={event.id}",
    )
    return {
        "outreach_event_id": event.id,
        "subject": draft.subject,
        "body": draft.body,
        "personalization_evidence": draft.personalization_evidence,
    }


def tool_request_human_approval(args: dict, ctx: OrchestratorContext) -> dict:
    event_id = int(args["outreach_event_id"])
    event = ctx.store.outreach.get(event_id)
    if not event:
        raise ValueError(f"No outreach event with id {event_id}")
    lead = ctx.store.leads.get(event.lead_id)
    company = ctx.store.companies.get(lead.company_id)
    contact = ctx.store.contacts.get(event.contact_id) if event.contact_id else None

    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="approval_gate", action=A.APPROVAL_REQUESTED, status="SUCCESS",
        input_summary=f"event_id={event_id}",
    )
    result = ctx.approval_gate.request_approval(
        ApprovalRequest(
            action="Send outreach email",
            company_name=company.name,
            contact_name=contact.full_name if contact else UNKNOWN,
            details={"Subject": event.subject, "Body": event.body},
        )
    )
    ctx.store.outreach.update_status(event_id, result.decision.value)
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="approval_gate", action=A.APPROVAL_DECISION, status="SUCCESS",
        input_summary=f"event_id={event_id}", output_summary=result.decision.value,
    )
    return {"decision": result.decision.value, "edited_fields": result.edited_fields}


def tool_generate_report(args: dict, ctx: OrchestratorContext) -> dict:
    report = ReportGenerator(ctx.store).generate(ctx.run_id)
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="reporting_agent", action=A.REPORT_GENERATED, status="SUCCESS",
    )
    return {"report_text": report.as_text()}


def tool_finish(args: dict, ctx: OrchestratorContext) -> dict:
    return {"summary": args.get("summary", "")}


DISPATCH = {
    "search_companies": tool_search_companies,
    "check_duplicate": tool_check_duplicate,
    "find_contacts": tool_find_contacts,
    "qualify_lead": tool_qualify_lead,
    "store_lead": tool_store_lead,
    "draft_outreach": tool_draft_outreach,
    "request_human_approval": tool_request_human_approval,
    "generate_report": tool_generate_report,
    "finish": tool_finish,
}


def dispatch_tool(name: str, args: dict, ctx: OrchestratorContext) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(args, ctx)
