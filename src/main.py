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
from src.orchestrator.agentic_loop import AgenticOrchestrator, FatalToolError, MaxIterationsExceeded
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.dry_run import run_dry_run
from src.tools.apollo_client import ApolloClient, ApolloError
from src.tools.llm_client import AnthropicLLMClient


def _apollo_smoke_test() -> int:
    """The smallest possible live Apollo call: enrich one well-known domain.
    Costs at most 1 credit (0 if Apollo has no match). Never touches the
    orchestrator, the database, or any other agent -- just proves the
    credential and endpoint actually work.
    """
    settings = get_settings()
    if not settings.apollo_api_key:
        print("ERROR: APOLLO_API_KEY is not set. Add it to .env (see .env.example).", file=sys.stderr)
        return 1

    client = ApolloClient(
        api_key=settings.apollo_api_key, base_url=settings.apollo_base_url,
        timeout_seconds=settings.apollo_timeout_seconds, max_requests_per_run=1,
    )
    print("[LIVE] Apollo smoke test: GET /organizations/enrich?domain=apollo.io (<=1 credit)")
    try:
        org = client.enrich_organization("apollo.io")
    except ApolloError as exc:
        print(f"ERROR: Apollo smoke test failed -- {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # network-level failures (DNS, connection refused, proxy denial, etc.)
        print(f"ERROR: Apollo smoke test failed -- could not reach Apollo: {exc}", file=sys.stderr)
        return 1

    if org:
        print(f"[LIVE] SUCCESS -- Apollo returned real data: name={org.get('name')!r}, industry={org.get('industry')!r}")
    else:
        print("[LIVE] Apollo responded successfully but found no match for apollo.io (0 credits charged).")
    print(f"[LIVE] Apollo requests made: {client.requests_made}")
    return 0


def _anthropic_smoke_test() -> int:
    """The smallest possible live Anthropic call: a one-word completion.
    Never touches the orchestrator, tools, or the database.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example).", file=sys.stderr)
        return 1

    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.orchestrator_model)
    print(f"[LIVE] Anthropic smoke test: one trivial completion, model={settings.orchestrator_model}")
    try:
        text = llm.complete(system="Reply with exactly one word and nothing else.", user="Say: OK", max_tokens=10)
    except Exception as exc:
        print(f"ERROR: Anthropic smoke test failed -- {exc}", file=sys.stderr)
        return 1
    print(f"[LIVE] SUCCESS -- model responded: {text!r}")
    return 0


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

    print(f"[LIVE] Run {run_id} starting. Objective: {objective}")
    print(f"[LIVE] Apollo budget for this run: {settings.apollo_max_requests_per_run} requests\n")
    try:
        summary = orchestrator.run(objective)
    except FatalToolError as exc:
        print(f"\nERROR: run stopped -- {exc}", file=sys.stderr)
        store.close()
        return 1
    except MaxIterationsExceeded as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        store.close()
        return 1

    print(f"\n{'=' * 60}\n[LIVE] Run {run_id} finished.\n{'=' * 60}\n{summary}")
    store.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="J-WALT autonomous business-development agent")
    parser.add_argument("--dry-run", action="store_true", help="Run the full pipeline safely: no writes to the real DB, nothing sent, works without credentials.")
    parser.add_argument("--objective", type=str, help="Plain-language objective for the real, LLM-driven orchestrator, e.g. 'Find 10 potential Dubai hotel clients for J-WALT'")
    parser.add_argument("--non-interactive", action="store_true", help="Auto-reject approval requests instead of prompting (real mode only; dry-run is always non-interactive).")
    parser.add_argument("--apollo-smoke-test", action="store_true", help="Smallest possible live Apollo call (<=1 credit) to verify APOLLO_API_KEY works. No orchestrator, no DB writes.")
    parser.add_argument("--anthropic-smoke-test", action="store_true", help="Smallest possible live Anthropic call (one word) to verify ANTHROPIC_API_KEY works. No orchestrator, no DB writes.")
    args = parser.parse_args()

    if args.apollo_smoke_test:
        return _apollo_smoke_test()

    if args.anthropic_smoke_test:
        return _anthropic_smoke_test()

    if args.dry_run:
        run_dry_run(get_settings())
        return 0

    if args.objective:
        return _run_real(args.objective, non_interactive=args.non_interactive)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
