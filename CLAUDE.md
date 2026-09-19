# CLAUDE.md

Guidance for Claude Code (or any AI assistant) working in this repository.

## What this is

An autonomous business-development agent for J-WALT, a Dubai-based interior
fit-out company. It researches potential clients via Apollo.io, qualifies
them against a configurable rubric, finds decision-makers, drafts outreach
emails, and requires human approval before anything could ever be sent.
There is currently no send path at all -- see README.md "What is still
missing".

## Architecture at a glance

- `src/orchestrator/agentic_loop.py` -- the real orchestrator: an Anthropic
  tool-use loop. Claude decides which tool to call next, retries, replans,
  and stops; it does not follow a fixed script.
- `src/orchestrator/tools.py` -- the ONLY mapping from "what Claude decided"
  to "what actually runs". If you add a capability the orchestrator should
  be able to use, it goes here, with a schema in `TOOL_SCHEMAS`.
- `src/orchestrator/dry_run.py` -- a separate, deterministic, always-safe
  path (`--dry-run`). Not LLM-driven, so it works with zero credentials.
- `src/agents/*` -- deterministic specialist logic (research parsing,
  qualification scoring, contact search, outreach drafting). Only
  `outreach_agent.py` calls an LLM; qualification is intentionally a fixed,
  config-driven rubric, not a model judgment, so scores are reproducible.
- `src/memory/*` -- SQLite persistence, no ORM. `store.py` is the single
  entry point (one connection, all repositories, dedupe).
- `src/tools/apollo_client.py` -- the only place that calls Apollo's REST
  API. `src/tools/apollo_parser.py` maps raw responses to plain dicts,
  kept separate so parsing is unit-testable without network access.

## Hard rules (do not relax these without the user's explicit sign-off)

1. **Never invent data.** Any field the tools don't provide must surface as
   the literal string `"UNKNOWN"`, never a guess. See `src/agents/common.py`.
2. **No send path.** `OutreachAgent` only drafts. Do not wire up an SMTP/Gmail
   send call without first building the human approval flow around it and
   getting explicit confirmation this is wanted.
3. **Dedupe before create.** Any code path that creates a company must go
   through `Store.get_or_create_company` (or an equivalent dedupe check),
   never `CompanyRepository.create` directly, outside of tests/fixtures.
4. **Qualification stays deterministic.** Don't replace `QualificationAgent`
   with an LLM call -- it needs to be reproducible and explainable to a
   human approver.
5. **Respect the Apollo budget.** `ApolloClient` enforces
   `apollo.max_requests_per_run` from `config/settings.yaml`. Don't bypass it.
6. **`--dry-run` must stay safe with zero configuration.** It must never
   write to the real DB file and must never require any API key to run.
7. **Never fabricate data on a live-call failure.** In a real (`--objective`)
   run, an `ApolloAuthError` or `ApolloBudgetExceededError` must abort the
   whole run immediately (`FatalToolError` in `agentic_loop.py`) rather than
   let the model retry a call that cannot succeed, and must never be
   papered over with synthetic data -- that fallback exists only in
   `dry_run.py`, always explicitly labeled `WOULD ...`.

## Known, confirmed limitation from development

This project was originally built inside a sandbox whose network egress
policy explicitly blocks `api.apollo.io` (confirmed via a 403 policy denial,
not a timeout). `apollo_client.py`'s REST calls were therefore verified for
correct request/response shape against fixtures, but could not be
live-tested end-to-end during development. Don't treat their presence in
the codebase as proof they've been exercised against the real API -- run
`tests/integration/test_apollo_integration.py` with
`RUN_APOLLO_INTEGRATION_TESTS=1` from an environment with real internet
access first.

## Running things

```
pip install -e ".[dev]"
python -m pytest              # fast, no network, no credit usage
python -m src.main --dry-run  # full pipeline, zero cost, zero risk
```

See README.md for full setup and environment variables.
