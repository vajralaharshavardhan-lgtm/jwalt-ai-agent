"""CLI entrypoint.

    python -m src.main --dry-run
    python -m src.main --objective "Find 10 potential Dubai hotel clients for J-WALT"

See README.md for full usage, required environment variables, and what
dry-run does and doesn't touch.
"""
from __future__ import annotations

import argparse
import sys
import uuid

from src.agents.contact_agent import ContactAgent
from src.agents.outreach_agent import OutreachAgent
from src.agents.qualification_agent import QualificationAgent
from src.agents.research_agent import ResearchAgent
from src.approval.gate import ApprovalGate
from src.config import get_settings
from src.memory.store import Store
from src.orchestrator.agentic_loop import AgenticOrchestrator
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.dry_run import run_dry_run
from src.tools.apollo_client import ApolloClient
from src.tools.llm_client import AnthropicLLMClient


def _run_real(objective: str, *, non_interactive: bool) -> int:
    settings = get_settings()

    missing = []
    if not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")
    if not settings.apollo_api_key:
        missing.append("APOLLO_API_KEY")
    if missing:
        print(
            f"ERROR: missing required environment variable(s): {', '.join(missing)}.\n"
            "Add them to .env (see .env.example), or run with --dry-run instead, "
            "which works without any credentials.",
            file=sys.stderr,
        )
        return 1

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    store = Store(str(settings.resolved_db_path()))
    apollo_client = ApolloClient(
        api_key=settings.apollo_api_key,
        base_url=settings.apollo_base_url,
        timeout_seconds=settings.apollo_timeout_seconds,
        max_requests_per_run=settings.apollo_max_requests_per_run,
    )
    llm_client = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.orchestrator_model)
    scoring_config = settings.raw_scoring

    ctx = OrchestratorContext(
        run_id=run_id,
        store=store,
        apollo_client=apollo_client,
        research_agent=ResearchAgent(apollo_client, scoring_config),
        qualification_agent=QualificationAgent(scoring_config),
        contact_agent=ContactAgent(apollo_client, scoring_config.get("decision_maker_titles", [])),
        outreach_agent=OutreachAgent(llm_client),
        approval_gate=ApprovalGate(non_interactive=non_interactive),
    )

    orchestrator = AgenticOrchestrator(
        anthropic_api_key=settings.anthropic_api_key,
        model=settings.orchestrator_model,
        ctx=ctx,
        max_iterations=settings.orchestrator_max_iterations,
        max_retries_per_step=settings.orchestrator_max_retries_per_step,
    )

    print(f"Run {run_id} starting. Objective: {objective}\n")
    summary = orchestrator.run(objective)
    print(f"\n{'=' * 60}\nRun {run_id} finished.\n{'=' * 60}\n{summary}")
    store.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="J-WALT autonomous business-development agent")
    parser.add_argument("--dry-run", action="store_true", help="Run the full pipeline safely: no writes to the real DB, nothing sent, works without credentials.")
    parser.add_argument("--objective", type=str, help="Plain-language objective for the real, LLM-driven orchestrator, e.g. 'Find 10 potential Dubai hotel clients for J-WALT'")
    parser.add_argument("--non-interactive", action="store_true", help="Auto-reject approval requests instead of prompting (real mode only; dry-run is always non-interactive).")
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run(get_settings())
        return 0

    if args.objective:
        return _run_real(args.objective, non_interactive=args.non_interactive)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
