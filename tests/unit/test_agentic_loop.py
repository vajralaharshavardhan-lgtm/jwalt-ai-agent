"""Tests for the real, LLM-driven orchestrator loop -- with the Anthropic
SDK's network call replaced by a scripted fake response object, so these
run with zero network access and zero cost. Apollo failures are triggered
for real (an ApolloClient constructed with api_key=None raises
ApolloAuthError before any network call), which is exactly the case the
fail-fast behavior exists for.
"""
from dataclasses import dataclass, field

import pytest

from src.agents.contact_agent import ContactAgent
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchAgent
from src.approval.gate import ApprovalGate
from src.orchestrator.agentic_loop import AgenticOrchestrator, FatalToolError, MaxIterationsExceeded
from src.orchestrator.context import OrchestratorContext
from src.tools.apollo_client import ApolloClient

SCORING_CONFIG = {
    "target_industries": ["hospitality"], "target_locations": ["dubai"],
    "ideal_employee_ranges": ["51,200"], "fit_out_signal_keywords": ["new opening"],
    "decision_maker_titles": ["facilities manager"],
    "weights": {"industry_match": 30, "location_match": 20, "employee_size_fit": 15, "fit_out_signal": 20, "decision_maker_found": 15},
    "thresholds": {"hot": 75, "warm": 50, "cold": 25},
}


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    name: str
    input: dict
    id: str = "toolu_1"
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list = field(default_factory=list)


class ScriptedAnthropicMessages:
    """Stands in for `anthropic.Anthropic(...).messages` -- returns each
    scripted response in order on successive `.create()` calls.
    """

    def __init__(self, responses: list[FakeResponse]):
        self._responses = list(responses)
        self.call_count = 0

    def create(self, **kwargs):
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


def make_ctx(store, *, apollo_api_key: str | None = "fake-key-does-not-matter"):
    apollo_client = ApolloClient(api_key=apollo_api_key, max_requests_per_run=5)
    return OrchestratorContext(
        run_id="test-run", store=store, apollo_client=apollo_client,
        research_agent=ResearchAgent(apollo_client, SCORING_CONFIG),
        qualification_agent=QualificationAgent(SCORING_CONFIG),
        contact_agent=ContactAgent(apollo_client, SCORING_CONFIG["decision_maker_titles"]),
        outreach_agent=OutreachAgent(None),
        approval_gate=ApprovalGate(non_interactive=True),
    )


def make_orchestrator(ctx, responses: list[FakeResponse], **kwargs) -> AgenticOrchestrator:
    orchestrator = AgenticOrchestrator(
        anthropic_api_key="fake-key-does-not-matter", model="claude-sonnet-5", ctx=ctx, **kwargs
    )
    orchestrator._client.messages = ScriptedAnthropicMessages(responses)
    return orchestrator


class TestFinishesNormally:
    def test_calls_finish_tool_and_returns_summary(self, store):
        ctx = make_ctx(store)
        responses = [
            FakeResponse(content=[FakeToolUseBlock(name="finish", input={"summary": "Done, found 0 leads."})]),
        ]
        orchestrator = make_orchestrator(ctx, responses)
        result = orchestrator.run("Find leads")
        assert result == "Done, found 0 leads."

    def test_plain_text_response_without_tool_use_is_treated_as_done(self, store):
        ctx = make_ctx(store)
        responses = [FakeResponse(content=[FakeTextBlock(text="I have nothing to do.")])]
        orchestrator = make_orchestrator(ctx, responses)
        result = orchestrator.run("Find leads")
        assert result == "I have nothing to do."


class TestFatalApolloErrorsAbortImmediately:
    def test_missing_apollo_key_raises_fatal_tool_error(self, store):
        ctx = make_ctx(store, apollo_api_key=None)  # ApolloAuthError guaranteed, no network needed
        responses = [
            FakeResponse(content=[FakeToolUseBlock(name="search_companies", input={"target_count": 1})]),
        ]
        orchestrator = make_orchestrator(ctx, responses)
        with pytest.raises(FatalToolError, match="search_companies"):
            orchestrator.run("Find leads")

    def test_fatal_error_is_logged_before_raising(self, store):
        ctx = make_ctx(store, apollo_api_key=None)
        responses = [FakeResponse(content=[FakeToolUseBlock(name="search_companies", input={"target_count": 1})])]
        orchestrator = make_orchestrator(ctx, responses)
        with pytest.raises(FatalToolError):
            orchestrator.run("Find leads")
        logs = store.run_logs.list_for_run("test-run")
        assert any(entry.status == "ERROR" and "FATAL" in (entry.error_message or "") for entry in logs)

    def test_exhausted_apollo_budget_raises_fatal_tool_error(self, store):
        ctx = make_ctx(store)
        ctx.apollo_client._max_requests = 0  # simulate an already-exhausted budget
        responses = [FakeResponse(content=[FakeToolUseBlock(name="search_companies", input={"target_count": 1})])]
        orchestrator = make_orchestrator(ctx, responses)
        with pytest.raises(FatalToolError, match="budget"):
            orchestrator.run("Find leads")


class TestNonFatalErrorsAreFedBackToClaude:
    def test_ordinary_tool_error_does_not_abort_the_run(self, store):
        ctx = make_ctx(store)
        responses = [
            # qualify_lead with a bad payload raises a plain KeyError -> non-fatal
            FakeResponse(content=[FakeToolUseBlock(name="qualify_lead", input={})]),
            FakeResponse(content=[FakeToolUseBlock(name="finish", input={"summary": "Recovered and stopped."})]),
        ]
        orchestrator = make_orchestrator(ctx, responses)
        result = orchestrator.run("Find leads")
        assert result == "Recovered and stopped."
        logs = store.run_logs.list_for_run("test-run")
        assert any(entry.status == "ERROR" for entry in logs)

    def test_never_falls_back_to_fabricated_apollo_data(self, store):
        """An Apollo failure must never silently produce fake company data --
        it must surface as an error, fatal or not, and nothing in the DB.
        """
        ctx = make_ctx(store, apollo_api_key=None)
        responses = [FakeResponse(content=[FakeToolUseBlock(name="search_companies", input={"target_count": 1})])]
        orchestrator = make_orchestrator(ctx, responses)
        with pytest.raises(FatalToolError):
            orchestrator.run("Find leads")
        assert store.companies.search() == []


class TestMaxIterations:
    def test_raises_if_finish_never_called(self, store):
        ctx = make_ctx(store)
        # Every call re-issues the same non-fatal, non-finish tool call forever.
        responses = [
            FakeResponse(content=[FakeToolUseBlock(name="generate_report", input={})]) for _ in range(3)
        ]
        orchestrator = make_orchestrator(ctx, responses, max_iterations=3)
        with pytest.raises(MaxIterationsExceeded):
            orchestrator.run("Find leads")
