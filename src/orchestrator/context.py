"""Everything a tool handler needs to do its job, bundled so tools.py
functions take exactly two arguments: (args: dict, ctx: OrchestratorContext).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agents.contact_agent import ContactAgent
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchAgent
from src.approval.gate import ApprovalGate
from src.memory.store import Store
from src.tools.apollo_client import ApolloClient


@dataclass
class OrchestratorContext:
    run_id: str
    store: Store
    apollo_client: ApolloClient
    research_agent: ResearchAgent
    qualification_agent: QualificationAgent
    contact_agent: ContactAgent
    outreach_agent: OutreachAgent
    approval_gate: ApprovalGate
