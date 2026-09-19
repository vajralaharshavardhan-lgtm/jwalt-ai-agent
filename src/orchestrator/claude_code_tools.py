"""Claude-Code-mode-only tools.

Used when Claude Code itself is the orchestrator -- no ANTHROPIC_API_KEY,
no OutreachAgent/AnthropicLLMClient, no blocking-terminal ApprovalGate.
Research and contact-finding are performed by the Claude Code session
directly via Apollo MCP tools; these functions only persist already-
gathered, already-normalized data using the SAME database, dedupe,
qualification, and audit-log machinery the API-based orchestrator uses.

check_duplicate, qualify_lead, store_lead, generate_report, and finish
(src/orchestrator/tools.py) are reused UNCHANGED in this mode -- this file
only adds what those don't already cover: deterministic evidence
extraction exposed standalone, recording a manually composed outreach
draft, and recording a human approval decision made directly in the
Claude Code conversation instead of via a blocking terminal prompt.
"""
from __future__ import annotations

import json

from src.agents.common import UNKNOWN
from src.agents.research_agent import extract_evidence
from src.config import get_settings
from src.orchestrator import actions as A
from src.orchestrator.context import OrchestratorContext

_VALID_DECISIONS = {"APPROVED", "REJECTED", "EDITED"}


def cc_extract_evidence(args: dict, ctx: OrchestratorContext) -> dict:
    """Identical logic to the API-mode Research Agent's extract_evidence():
    a literal substring match against config/scoring.yaml's
    fit_out_signal_keywords. Not a separate judgment call -- reuses the
    exact same function so both modes behave identically here.
    """
    fit_out_keywords = get_settings().raw_scoring.get("fit_out_signal_keywords", [])
    parsed = {"description": args.get("description"), "keywords": args.get("keywords") or []}
    matched = extract_evidence(parsed, fit_out_keywords)
    return {"evidence": matched if matched else [UNKNOWN]}


def cc_submit_outreach_draft(args: dict, ctx: OrchestratorContext) -> dict:
    """Records an outreach draft Claude composed itself (following the same
    fact-grounding rules as the API-mode Outreach Agent's system prompt).
    Never sends anything -- there is no send path anywhere in this project.
    """
    lead_id = int(args["lead_id"])
    lead = ctx.store.leads.get(lead_id)
    if not lead:
        raise ValueError(f"No lead with id {lead_id}")
    if not lead.contact_id:
        raise ValueError(f"Lead {lead_id} has no contact -- cannot draft a personalized outreach email")

    subject = args["subject"]
    body = args["body"]
    personalization_evidence = args.get("personalization_evidence", [])

    event = ctx.store.outreach.create(
        lead_id=lead_id,
        contact_id=lead.contact_id,
        event_type="DRAFT_CREATED",
        subject=subject,
        body=body,
        personalization_evidence=json.dumps(personalization_evidence),
        status="PENDING_APPROVAL",
    )
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="claude_code_orchestrator", action=A.DRAFT_CREATED, status="SUCCESS",
        input_summary=f"lead_id={lead_id}", output_summary=f"event_id={event.id}",
    )
    return {
        "outreach_event_id": event.id,
        "subject": subject,
        "body": body,
        "personalization_evidence": personalization_evidence,
    }


def cc_request_approval(args: dict, ctx: OrchestratorContext) -> dict:
    """Audit marker: logs that Claude is about to ask the human, directly in
    this conversation, to approve/reject/edit a draft. No blocking I/O --
    the actual question is asked via the conversation itself.
    """
    event_id = int(args["outreach_event_id"])
    event = ctx.store.outreach.get(event_id)
    if not event:
        raise ValueError(f"No outreach event with id {event_id}")
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="claude_code_orchestrator", action=A.APPROVAL_REQUESTED, status="SUCCESS",
        input_summary=f"event_id={event_id}",
    )
    return {"outreach_event_id": event_id, "subject": event.subject, "body": event.body}


def cc_record_approval_decision(args: dict, ctx: OrchestratorContext) -> dict:
    """Records the human's decision, given directly in the Claude Code
    conversation (not via a terminal prompt), on an outreach draft.
    """
    event_id = int(args["outreach_event_id"])
    decision = args["decision"]
    if decision not in _VALID_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(_VALID_DECISIONS)}, got {decision!r}")

    event = ctx.store.outreach.get(event_id)
    if not event:
        raise ValueError(f"No outreach event with id {event_id}")

    ctx.store.outreach.update_status(event_id, decision)
    ctx.store.run_logs.log(
        run_id=ctx.run_id, agent="claude_code_orchestrator", action=A.APPROVAL_DECISION, status="SUCCESS",
        input_summary=f"event_id={event_id}", output_summary=decision,
    )
    return {"outreach_event_id": event_id, "decision": decision}


DISPATCH = {
    "cc_extract_evidence": cc_extract_evidence,
    "cc_submit_outreach_draft": cc_submit_outreach_draft,
    "cc_request_approval": cc_request_approval,
    "cc_record_approval_decision": cc_record_approval_decision,
}
