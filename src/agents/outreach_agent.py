"""Outreach Agent: drafts personalized outreach emails. It NEVER sends
anything -- there is no send path in this codebase at all (see README
"What is still missing").

Every factual/personalization claim in the email must trace back to a field
already present on the researched company/contact/qualification objects
passed in. The prompt lists only those facts, forbids adding anything else,
and requires the model to cite which facts it used.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from src.agents.contact_agent import ResearchedContact
from src.agents.qualification_agent import QualificationResult
from src.agents.research_agent import ResearchedCompany
from src.tools.llm_client import LLMClient

SYSTEM_PROMPT = """You are a business-development copywriter for J-WALT, a Dubai-based interior fit-out company.
You write short, professional first-touch outreach emails to potential clients.

STRICT RULES:
- Use ONLY the facts given to you in the AVAILABLE FACTS block. Never invent, assume, or embellish any company detail, project, statistic, or personal detail not explicitly listed there.
- Any fact whose value is UNKNOWN must never be mentioned or implied in the email.
- Every specific claim about the recipient's company must be traceable to one of the AVAILABLE FACTS. List exactly which facts you used in personalization_evidence.
- Keep the email body under 150 words. End with one clear call to action: a short introductory call.
- Sign off as "The J-WALT Team".
- Output ONLY valid JSON, no markdown code fences, no commentary, matching exactly this shape:
{"subject": "...", "body": "...", "personalization_evidence": ["fact used 1", "fact used 2"]}
"""


@dataclass
class OutreachDraft:
    lead_id: int
    subject: str
    body: str
    personalization_evidence: list[str]


class OutreachAgent:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    @staticmethod
    def _build_facts_block(
        company: ResearchedCompany, contact: ResearchedContact, qualification: QualificationResult
    ) -> str:
        facts = {
            "company_name": company.name,
            "industry": company.industry,
            "city": company.city,
            "country": company.country,
            "employee_count": company.employee_count,
            "evidence_of_fit_out_need": company.evidence,
            "contact_name": contact.full_name,
            "contact_title": contact.title,
            "lead_classification": qualification.classification,
        }
        return "\n".join(f"- {k}: {v}" for k, v in facts.items())

    def draft(
        self,
        *,
        lead_id: int,
        company: ResearchedCompany,
        contact: ResearchedContact,
        qualification: QualificationResult,
    ) -> OutreachDraft:
        facts_block = self._build_facts_block(company, contact, qualification)
        user_prompt = f"AVAILABLE FACTS:\n{facts_block}\n\nWrite the outreach email JSON now."
        raw_response = self._llm.complete(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=600)
        data = self._parse_json_response(raw_response)
        return OutreachDraft(
            lead_id=lead_id,
            subject=data.get("subject", "UNKNOWN"),
            body=data.get("body", "UNKNOWN"),
            personalization_evidence=data.get("personalization_evidence", []),
        )

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Outreach LLM did not return valid JSON: {raw[:200]!r}") from e
