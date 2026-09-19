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

## Windows quickstart (no Python experience assumed)

**Easiest path: see [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md).** Double-click
`setup.bat` once, then `run-agent.bat` -- no commands to type. Both scripts
check Python/Git, create the virtual environment, install dependencies,
create `.env` for you, run the test suite, verify your API keys with live
smoke tests, and only then run the agent. `.env` is never overwritten and
never committed (see `.gitignore`); the scripts never contain or print any
API key.

The rest of this section is the manual, type-it-yourself PowerShell
equivalent of the same steps, for anyone who prefers that or wants to see
exactly what the scripts do.

**1. Install Python** (skip if `python --version` in PowerShell already
prints 3.11 or higher): download from https://www.python.org/downloads/,
run the installer, and **check the "Add python.exe to PATH" box** on the
first screen before clicking Install.

**2. Open PowerShell in the project folder.** In File Explorer, open the
`jwalt-ai-agent` folder, then either right-click inside it and choose "Open
in Terminal", or type `powershell` into the address bar and press Enter.

**3. Create and activate a virtual environment** (a private, isolated copy
of Python just for this project, so it can't conflict with anything else
on your machine):
```powershell
python -m venv .venv
.venv\Scripts\activate
```
Your prompt should now start with `(.venv)`. Do this every time you open a
new PowerShell window to work on this project -- it doesn't carry over.

**4. Install the project's dependencies:**
```powershell
pip install -e ".[dev]"
```

**5. Create your personal `.env` file** (this holds your API keys and is
never uploaded anywhere -- see "Environment variables" below):
```powershell
copy .env.example .env
notepad .env
```
Notepad will open. Fill in the two blank lines so they look like:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
APOLLO_API_KEY=your-real-apollo-key-here
```
Leave every other line exactly as it is. Save (Ctrl+S) and close Notepad.
**Never paste these keys anywhere else** -- not into chat, not into a
document, not into a screenshot.

**6. Verify both keys work, before spending anything on a real search:**
```powershell
python -m src.main --anthropic-smoke-test
python -m src.main --apollo-smoke-test
```
Each should print a line containing `SUCCESS`. If one fails, read the
`ERROR:` line it prints -- it tells you plainly what's wrong (e.g. a typo
in the key) and never shows the key itself.

**7. Run the full pipeline safely first**, with no real API calls and no
risk, to see how it behaves:
```powershell
python -m src.main --dry-run
```
Every line in this output is prefixed `[DRY RUN]` -- that's your signal
this is a simulation, not real data. Nothing you see here was sent
anywhere, and nothing was saved to your real database.

**8. Run your first real, live test** (see "Your first live test" below
for exactly what this does and what to expect):
```powershell
python -m src.main --objective "Find 3 potential Dubai hotel clients for J-WALT" --non-interactive
```
Every line here is prefixed `[LIVE]` instead -- that's real data from the
real Apollo API and real Claude reasoning. `--non-interactive` means it
will automatically decline to send anything rather than stopping to ask
you at the terminal; drop that flag once you're ready to sit at the
keyboard and personally approve, reject, or edit each draft.

**9. Look at what got saved**, without needing any database software:
```powershell
python -c "from src.memory.store import Store; s = Store('data/leads.db'); [print(l) for l in s.leads.search()]"
```

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

**Smoke tests (recommended before your first real run) -- verify each credential works in isolation, at minimal cost, with no orchestrator and no DB writes:**
```bash
python -m src.main --apollo-smoke-test      # one GET /organizations/enrich call, <=1 credit
python -m src.main --anthropic-smoke-test   # one ~10-token completion
```
Both report clear SUCCESS/ERROR and never print the key itself. Run these
first -- they isolate "is my credential valid and can I reach the API"
from "does the full orchestrator work," which is a much smaller thing to
debug if something's wrong.

**Real, LLM-driven run (requires `ANTHROPIC_API_KEY` and `APOLLO_API_KEY`):**
```bash
python -m src.main --objective "Find 2 potential Dubai hotel clients for J-WALT"
```
This will prompt you at the terminal (`[A]pprove / [R]eject / [E]dit?`)
whenever the orchestrator has drafted an outreach email and wants to send
it -- nothing is ever sent (there is no send integration at all yet), but
the approval decision is recorded either way. Start with a small
`target_count` (2-3) in your objective wording -- Apollo calls cost real
credits, and this also bounds how many tool-use iterations the orchestrator
needs.

Pass `--non-interactive` to auto-reject approval requests instead of
prompting (useful for a first hands-off test run; every draft will show up
as "awaiting approval: 0, rejected: N" in the report rather than blocking).

If Apollo fails for a reason that can't be fixed by retrying -- a rejected
API key, or the run's Apollo credit budget (`apollo.max_requests_per_run`
in `config/settings.yaml`) being exhausted -- the run stops immediately
with the real error message and a non-zero exit code. It never falls back
to synthetic/fabricated data during a real (`--objective`) run; that
fallback only ever happens in `--dry-run`, and even there it's always
labeled `[DRY RUN] ... WOULD SEARCH ...` so it's never mistaken for a live
result.

## Your first live test

```bash
python -m src.main --objective "Find 3 potential Dubai hotel clients for J-WALT" --non-interactive
```

What this actually does, step by step, all real:
1. Claude reads the objective and calls `search_companies` with a Dubai
   location filter and `target_count: 3` -- a real, credit-consuming Apollo
   API call.
2. For each company Apollo returns, it checks the local SQLite database for
   an existing match (domain, then normalized name) before doing anything
   else -- so re-running this same objective later won't create duplicates.
3. It calls `find_contacts` to look for a decision-maker at each company
   (another real Apollo call).
4. It runs the qualification rubric (`config/scoring.yaml`) -- no API call,
   deterministic -- and classifies each company HOT/WARM/COLD/UNQUALIFIED.
5. Qualified companies (and their contact, if found) are saved to
   `data/leads.db`.
6. For each stored lead with a contact, it calls `draft_outreach` -- a real
   Claude call that writes a personalized email grounded only in the facts
   it actually gathered -- and immediately calls `request_human_approval`.
   With `--non-interactive`, that auto-rejects (nothing is ever sent
   regardless -- there is no send code in this project at all). Drop the
   flag to sit at the `[A]pprove / [R]eject / [E]dit?` prompt yourself.
7. It calls `generate_report` and then `finish`.

**No bulk actions happen anywhere in this path**: `target_count: 3` bounds
the search, there is no "send all" or "approve all" tool, and each
outreach draft is approved/rejected one at a time.

**LIVE vs DRY RUN, at a glance:** a `--dry-run` run prefixes every action
line `[DRY RUN]` (and, for any step where no API key was configured, says
`WOULD SEARCH` / `WOULD DRAFT` / `WOULD SEND` instead of doing it), and its
run id always starts with `dryrun-` (visible in the report header too). A
real run prefixes its start/budget/finish lines `[LIVE]`, gets a run id
starting with `run-`, and everything in between is the model's own tool
calls and their real results. The two paths share no code (`dry_run.py` vs
`agentic_loop.py`), so there's no way for one to be mistaken for the other.

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
