# J-WALT AI Business-Development Agent

An autonomous agent that researches potential clients in Dubai for J-WALT
(an interior fit-out company), qualifies them, finds decision-makers,
drafts personalized outreach emails, and requires human approval before
anything could ever be sent. This is the MVP slice of a larger planned
system -- see "What is still missing" below for what is deliberately not
built yet.

## What makes this "agentic" rather than a fixed script

The real orchestrator (`python -m src.main --objective "..."`) is an
Anthropic tool-use loop: Claude is given the objective and a set of tools
(search companies, check duplicates, find contacts, qualify a lead, store
a lead, draft outreach, request human approval, generate a report, finish)
and decides for itself which tool to call, in what order, when to retry a
failed step, when to broaden its search instead of repeating it, and when
to stop. The Python code only executes whatever Claude decides and feeds
the result back -- see `src/orchestrator/agentic_loop.py` and
`config/prompts/orchestrator_system.md` for the exact rules it operates
under (never invent data, dedupe before storing, always request approval
before a draft could be sent, respect the Apollo credit budget).

`--dry-run` is a separate, deterministic path used for safe testing/demo
purposes -- it does not use the LLM-driven loop. See "Dry-run mode" below.

## Architecture

```
src/
  main.py                     CLI entrypoint
  config.py                   loads .env + config/*.yaml into one Settings object
  orchestrator/
    agentic_loop.py           the real, LLM-driven orchestrator (tool-use loop)
    dry_run.py                deterministic, always-safe demo path
    tools.py                  tool schemas + handlers Claude can call
    context.py                bundles agents/store/clients for tool handlers
    actions.py                canonical run_logs action names
  agents/
    research_agent.py         Apollo search -> structured, evidence-backed companies
    qualification_agent.py    deterministic, config-driven HOT/WARM/COLD/UNQUALIFIED scoring
    contact_agent.py          decision-maker search + selective enrichment
    outreach_agent.py         LLM-drafted, fact-grounded outreach emails (never sends)
    common.py                 shared UNKNOWN/or_unknown helpers
  tools/
    apollo_client.py          Apollo REST client (credit-budgeted)
    apollo_parser.py          raw Apollo JSON -> plain dicts
    llm_client.py             Anthropic wrapper for plain-text/JSON completions
  memory/
    db.py, models.py, repositories.py, store.py, dedupe.py
                               SQLite schema, CRUD, and duplicate detection
  approval/
    gate.py                   CLI human approval gate
  reporting/
    report.py                 tallies a run's outcome from the audit log
config/
  settings.yaml                runtime config (non-secret)
  scoring.yaml                 the qualification rubric -- edit this, not code
  prompts/orchestrator_system.md   the orchestrator's system prompt
tests/
  unit/                        no network, no credits, run on every commit
  integration/                 real Apollo calls, gated, off by default
  fixtures/                    synthetic example Apollo payloads
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# then edit .env -- see "Environment variables" below
```

## Environment variables

All in `.env` (never commit this file -- it's gitignored).

| Variable | Required for | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Real orchestrator runs (`--objective`), outreach drafting | Without it, `--dry-run` still works via a canned draft. |
| `ORCHESTRATOR_MODEL` | Optional | Defaults to `claude-sonnet-5`. |
| `APOLLO_API_KEY` | Real orchestrator runs | Get it from https://developer.apollo.io -> API Keys. This is a **separate** credential from any Apollo MCP connector you may have in Claude Code/Desktop -- MCP tool access does not extend to this standalone application. Without it, `--dry-run` falls back to bundled synthetic example data. |
| `JWALT_DB_PATH` | Optional | Defaults to `data/leads.db`. |
| `JWALT_LOG_LEVEL`, `JWALT_LOG_PATH` | Optional | Currently only `run_logs` (in the DB) is implemented; see "What is still missing". |

Non-secret configuration lives in `config/settings.yaml` (Apollo request
budget, orchestrator iteration limits, approval channel) and
`config/scoring.yaml` (the qualification rubric -- industries, locations,
employee-size sweet spot, fit-out signal keywords, decision-maker titles,
scoring weights, HOT/WARM/COLD thresholds). Edit these, not the Python
code, to retune behavior.

## Running the agent

**Dry-run (recommended first run -- works with zero configuration):**
```bash
python -m src.main --dry-run
```

**Real, LLM-driven run (requires `ANTHROPIC_API_KEY` and `APOLLO_API_KEY`):**
```bash
python -m src.main --objective "Find 10 potential Dubai hotel clients for J-WALT"
```
This will prompt you at the terminal (`[A]pprove / [R]eject / [E]dit?`)
whenever the orchestrator has drafted an outreach email and wants to send
it -- nothing is ever sent (there is no send integration at all yet), but
the approval decision is recorded either way.

Pass `--non-interactive` to auto-reject approval requests instead of
prompting (useful for a first hands-off test run; every draft will show up
as "awaiting approval: 0, rejected: N" in the report rather than blocking).

## Dry-run mode: exactly what it does and doesn't do

`--dry-run` gives two guarantees regardless of what's in `.env`:

1. **It never writes to your real database.** It always uses a throwaway
   in-memory SQLite database, so running it repeatedly never pollutes
   `data/leads.db` with test leads.
2. **It never sends anything.** There is no send path anywhere in this
   codebase, dry-run or not.

Within those guarantees, dry-run opportunistically uses real integrations
if they're configured, because that's the only way to verify Apollo/LLM
wiring without risking real data: if `APOLLO_API_KEY` is set it does a real
(read-only) Apollo search; if not, it prints `WOULD SEARCH ...` and falls
back to a bundled synthetic example company. Same pattern for
`ANTHROPIC_API_KEY` and outreach drafting. Every step that would be
irreversible or costly in a real run (search, create, update, draft, send)
is printed with an explicit label so a dry-run's console output and report
are clearly distinguishable from a real run's.

## Apollo setup

1. Create/locate an Apollo.io account with API access, and get an API key
   from https://developer.apollo.io -> API Keys. Put it in `.env` as
   `APOLLO_API_KEY`.
2. **This is separate from any Apollo MCP connector.** If you've connected
   Apollo to Claude Code/Desktop via MCP, that connector is only usable by
   an interactive Claude Code session -- it does not give this standalone
   Python application any access. The application always calls Apollo's
   REST API directly with `APOLLO_API_KEY`.

**What was actually verified during development** (via the MCP connector,
as a way to inspect real Apollo behavior before writing the REST client --
not as a substitute for testing the REST client itself):
- The connected Apollo account is real (a live team account, confirmed via
  its profile/credit-balance endpoint).
- Apollo's free organization-lookup tool returns real UAE company data when
  filtered by location (e.g. Jumeirah, Mashreq, DAMAC Properties, Dubai
  Airports came back for `organization_locations: ["United Arab Emirates"]`)
  -- confirming Apollo has solid Dubai/UAE data coverage worth building on,
  though fuzzy name-only matches for some UAE conglomerates returned nothing
  until location/domain filters were added.
- No credits were spent verifying this (only the free lookup and
  profile endpoints were called).

**What was NOT verified, and why:** `apollo_client.py`'s actual REST calls
(`mixed_companies/search`, `organizations/enrich`, `mixed_people/search`,
`people/match`) could not be exercised end-to-end during development. The
sandboxed environment this was built in has a network egress policy that
explicitly blocks outbound HTTPS to `api.apollo.io` (confirmed as a 403
policy denial on the CONNECT, not a timeout or misconfiguration). The
client's request/response handling was instead verified with unit tests
against representative fixture payloads
(`tests/fixtures/apollo_*.json`, clearly marked as synthetic, not captured
live traffic). **Run the integration tests below from a normal network
environment with a real `APOLLO_API_KEY` before trusting this in
production.**

There is also no confirmed *free* company-discovery REST endpoint in
Apollo's public API -- the MCP connector's free "organization lookup" tool
appears to be a capability specific to Apollo's own MCP server, not a
documented public REST endpoint. Company discovery in this codebase
therefore goes through the paid Organization Search endpoint, budgeted by
`apollo.max_requests_per_run` in `config/settings.yaml`.

## Tests

```bash
python -m pytest                                    # unit tests only, no network, no credits
RUN_APOLLO_INTEGRATION_TESTS=1 python -m pytest tests/integration -m apollo_integration
                                                      # real Apollo calls -- costs credits, needs network + APOLLO_API_KEY
```

Unit test coverage includes: duplicate detection (domain, normalized name,
email, phone), lead scoring (all signal combinations and threshold
boundaries), database CRUD, input validation (`UNKNOWN` handling), the
approval gate (interactive and non-interactive), the research/outreach
agents (fixture-driven, no network), reporting tallies, and Apollo client
request construction/auth/budget enforcement (mocked HTTP, no network).

Fixture-based scenario tests (`tests/unit/test_pipeline_fixtures.py`) cover
the five required cases end-to-end through the orchestrator's tool layer:
a valid lead, a duplicate lead, an irrelevant company, a lead with no
contact found, and a company with almost entirely missing data.

## What is still missing

Deliberately out of scope for this MVP (see the architecture conversation
that preceded this build for the full roadmap):
- **Actually sending email** (Gmail API or similar) -- outreach stops at a
  logged, approved-or-rejected draft.
- **CRM / Google Sheets sync** -- leads currently live only in SQLite.
- **Slack/email approval channels** -- only the CLI gate is implemented.
- **Scheduled/recurring runs** -- the agent runs once per invocation; no
  cron/scheduler wiring yet.
- **Multiple concurrent runs** -- SQLite here is single-writer; fine for
  one run at a time, not for concurrency.
- **Browser automation** -- not needed yet since Apollo covers the MVP's
  data needs; would be added if a target data source has no API.
- **Live-verified Apollo REST integration** -- see "Apollo setup" above.

## Example commands

```bash
# Safe, zero-config walkthrough of the whole pipeline
python -m src.main --dry-run

# Real run (needs .env configured)
python -m src.main --objective "Find 10 potential Dubai hotel clients for J-WALT"
python -m src.main --objective "Find Dubai retail companies opening new flagship stores" --non-interactive

# Tests
python -m pytest
python -m pytest tests/unit/test_qualification.py -v
RUN_APOLLO_INTEGRATION_TESTS=1 python -m pytest tests/integration -m apollo_integration
```
