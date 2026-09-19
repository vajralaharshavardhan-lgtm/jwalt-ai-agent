"""Command-line interface for Claude-Code-mode orchestration.

Lets a Claude Code session act as the agent's orchestrator -- no
ANTHROPIC_API_KEY needed -- by calling the project's existing dedupe/
qualification/storage/reporting logic through simple, scriptable commands
instead of the Anthropic tool-use loop in src/orchestrator/agentic_loop.py.

Research and contact discovery are NOT performed here: in Claude Code
mode, Claude calls Apollo MCP tools directly (available only to the Claude
Code session itself, not to this Python process) and passes the results
into these commands as plain JSON. See .claude/skills/jwalt-research/SKILL.md
for the full procedure an orchestrating Claude Code session follows.

Usage:
    python -m src.cli_tools list-tools
    python -m src.cli_tools new-run
    python -m src.cli_tools call <tool_name> '<json args>'

Available tool names (unchanged from src/orchestrator/tools.py, reused
as-is): check_duplicate, qualify_lead, store_lead, generate_report, finish.

New Claude-Code-mode tools (src/orchestrator/claude_code_tools.py):
cc_extract_evidence, cc_submit_outreach_draft, cc_request_approval,
cc_record_approval_decision.

NOT available here (API-mode only -- need a real ApolloClient /
AnthropicLLMClient / ApprovalGate): search_companies, find_contacts,
draft_outreach, request_human_approval. In Claude Code mode: call Apollo
MCP tools yourself for research/contacts, and use cc_submit_outreach_draft
/ cc_request_approval / cc_record_approval_decision for outreach.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from src.agents.qualification_agent import QualificationAgent
from src.config import get_settings
from src.memory.store import Store
from src.orchestrator.claude_code_tools import DISPATCH as CC_DISPATCH
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.tools import DISPATCH as API_DISPATCH
from src.orchestrator.tools import TOOL_SCHEMAS

API_MODE_ONLY = {"search_companies", "find_contacts", "draft_outreach", "request_human_approval"}

CC_TOOL_SCHEMAS = [
    {
        "name": "cc_extract_evidence",
        "description": (
            "Deterministic keyword match against fit_out_signal_keywords (config/scoring.yaml) -- "
            "identical logic to API mode's Research Agent. Pass the company's real description/keywords from Apollo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "cc_submit_outreach_draft",
        "description": (
            "Record an outreach draft you composed yourself, following the same fact-grounding "
            "rules as API mode's Outreach Agent. Does not send anything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "personalization_evidence": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["lead_id", "subject", "body"],
        },
    },
    {
        "name": "cc_request_approval",
        "description": "Log that you are about to ask the human, directly in this conversation, to approve/reject/edit a draft.",
        "input_schema": {
            "type": "object",
            "properties": {"outreach_event_id": {"type": "integer"}},
            "required": ["outreach_event_id"],
        },
    },
    {
        "name": "cc_record_approval_decision",
        "description": "Record the human's decision, given directly in the Claude Code conversation, on an outreach draft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "outreach_event_id": {"type": "integer"},
                "decision": {"type": "string", "enum": ["APPROVED", "REJECTED", "EDITED"]},
            },
            "required": ["outreach_event_id", "decision"],
        },
    },
]

RUN_ID_MARKER = Path(__file__).resolve().parent.parent / "data" / ".current_run_id"


def _get_or_create_run_id(*, new_run: bool) -> str:
    if not new_run and RUN_ID_MARKER.exists():
        existing = RUN_ID_MARKER.read_text().strip()
        if existing:
            return existing
    run_id = f"ccrun-{uuid.uuid4().hex[:8]}"
    RUN_ID_MARKER.parent.mkdir(parents=True, exist_ok=True)
    RUN_ID_MARKER.write_text(run_id)
    return run_id


def _build_context(run_id: str) -> OrchestratorContext:
    settings = get_settings()
    store = Store(str(settings.resolved_db_path()))
    return OrchestratorContext(
        run_id=run_id,
        store=store,
        apollo_client=None,
        research_agent=None,
        qualification_agent=QualificationAgent(settings.raw_scoring),
        contact_agent=None,
        outreach_agent=None,
        approval_gate=None,
    )


def dispatch(name: str, args: dict, ctx: OrchestratorContext) -> dict:
    if name in API_MODE_ONLY:
        raise ValueError(
            f"'{name}' is API-mode only (it needs a real Apollo/Anthropic client, neither of which "
            "exists in Claude Code mode). In Claude Code mode: call Apollo MCP tools yourself for "
            "research/contacts, and use cc_submit_outreach_draft / cc_request_approval / "
            "cc_record_approval_decision for outreach."
        )
    if name in CC_DISPATCH:
        return CC_DISPATCH[name](args, ctx)
    if name in API_DISPATCH:
        return API_DISPATCH[name](args, ctx)
    raise ValueError(f"Unknown tool: {name}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]

    if command == "list-tools":
        schemas = [s for s in TOOL_SCHEMAS if s["name"] not in API_MODE_ONLY] + CC_TOOL_SCHEMAS
        print(json.dumps(schemas, indent=2))
        return 0

    if command == "new-run":
        run_id = _get_or_create_run_id(new_run=True)
        print(run_id)
        return 0

    if command == "call":
        if len(sys.argv) < 4:
            print("Usage: python -m src.cli_tools call <tool_name> '<json args>'", file=sys.stderr)
            return 1
        tool_name = sys.argv[2]
        try:
            args = json.loads(sys.argv[3])
        except json.JSONDecodeError as exc:
            print(json.dumps({"error": f"invalid JSON args: {exc}"}), file=sys.stderr)
            return 1

        run_id = _get_or_create_run_id(new_run=False)
        ctx = _build_context(run_id)
        try:
            result = dispatch(tool_name, args, ctx)
            print(json.dumps({"run_id": run_id, "result": result}, indent=2, default=str))
            return 0
        except Exception as exc:  # noqa: BLE001 -- surface the real error; never fabricate a result
            ctx.store.run_logs.log(
                run_id=run_id, agent="claude_code_orchestrator", action=tool_name,
                status="ERROR", input_summary=json.dumps(args)[:500], error_message=str(exc),
            )
            print(json.dumps({"run_id": run_id, "error": str(exc)}, indent=2), file=sys.stderr)
            return 1
        finally:
            ctx.store.close()

    print(f"Unknown command: {command!r}", file=sys.stderr)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
