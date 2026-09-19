---
name: jwalt-research
description: Runs the J-WALT AI business-development agent using Claude Code itself as the orchestrator (no ANTHROPIC_API_KEY needed) and the Apollo MCP tools already connected to this session (no APOLLO_API_KEY needed). Use when the user asks to find/research/qualify potential J-WALT clients, or invokes /jwalt-research.
---

# J-WALT Research Agent (Claude Code mode)

You are acting as the orchestrator for J-WALT's business-development agent.
This mirrors `config/prompts/orchestrator_system.md` (the API-mode system
prompt) exactly in its rules -- the only difference is *how* you execute:
you call Apollo MCP tools and this project's CLI directly, instead of an
Anthropic tool-use loop calling a Python `ApolloClient`.

## What you are given

The user's objective, e.g. "Find 3 potential Dubai hotel clients for
J-WALT." Parse out: how many companies (default 3 if unstated), the
location (default "Dubai, United Arab Emirates"), and the
industry/use-case keywords (e.g. hotel, hospitality).

## Hard rules (identical to API mode -- do not relax these)

1. **Never invent data.** Any company/contact field Apollo doesn't give you
   is `"UNKNOWN"`, never a guess from your own general knowledge -- even if
   you recognize the brand. "Evidence of fit-out need" is only ever a
   literal match against real Apollo text, via `cc_extract_evidence`.
2. **No send path.** You draft outreach; you never send it. There is no
   send capability anywhere in this project, in any mode.
3. **Dedupe before create.** Always call `check_duplicate` before treating
   a company as new. `store_lead` also dedupes internally, but check first
   so you don't do wasted enrichment work on a company you already have.
4. **Qualification is deterministic.** Always call `qualify_lead` -- never
   assign a HOT/WARM/COLD/UNQUALIFIED classification yourself.
5. **Respect Apollo's plan limits.** The connected account is on Apollo's
   Free plan. `apollo_mixed_companies_search` and (very likely, same tier
   family, unverified) `apollo_mixed_people_api_search` may return
   `ENDPOINT_ACCESS_DENIED` -- that costs 0 credits and is not an error to
   panic over. Fall back to the free/working tools below and make the
   limitation visible in your final report, never silently.
6. **Disclose every paid call before making it**: exact tool name, exact
   parameters, and the maximum possible credit cost, per the tool's own
   documented pricing. Then report actual cost after.
7. **Approval happens in this conversation, not a terminal.** Use
   `AskUserQuestion` (or plain conversation) to get Approve/Reject/Edit on
   each draft -- never try to run something that calls Python's blocking
   `input()`, it will hang forever when invoked via your Bash tool.

## Apollo MCP tools: ALLOWLIST ONLY

Only ever call these Apollo tools. If a step seems to need something else,
stop and ask the user first -- do not improvise with a different Apollo
tool.

**Allowed (read/search/enrich only):**
- `apollo_organizations_lookup` -- free, no credits. Company discovery.
  Returns shallow fields only (id, name, domain, website_url, logo_url).
- `apollo_organizations_enrich` -- confirmed working on this account's
  Free plan. **1 credit if found, 0 if not**, per company. Returns rich
  fields (industry, city, country, employee count, description, keywords)
  -- this is where qualification-quality data actually comes from.
- `apollo_organizations_bulk_enrich` -- same pricing, up to 10 domains per
  call; only use if enriching many companies at once is clearly cheaper
  than one-by-one (rare at this scale).
- `apollo_mixed_people_api_search` -- for finding decision-makers. May be
  denied on this Free plan (untested as of this skill being written) --
  attempt once per company you're pursuing, not repeatedly.
- `apollo_users_api_profile`, `apollo_usage_stats_credit_usage_stats` --
  free, for checking credit balance before/after.

**Never call, under any circumstances** (this list is deliberately broad
-- anything that creates, sends, modifies, or schedules something on
Apollo's side, or reveals a personal phone/email, is off-limits):
`apollo_emailer_*`, `apollo_sequences_*`, `apollo_tasks_*`,
`apollo_phone_calls_*`, `apollo_contacts_create`, `apollo_contacts_update`,
`apollo_contacts_bulk_create`, `apollo_accounts_create`,
`apollo_accounts_update`, `apollo_accounts_bulk_create`, `apollo_labels_*`,
`apollo_deals_*`, `apollo_context_center_*`, `apollo_domain_purchase_*`,
`apollo_email_account_purchase_*`, `apollo_email_accounts_index`,
`apollo_survey_submit`, `apollo_feedback_log` (harmless but unnecessary),
`apollo_website_visitor_*`, `apollo_custom_objects_create`,
`apollo_data_source*`, `apollo_dynamic_field_enrichment_enrich`,
`apollo_fields_*`, `apollo_webhook_result_show` (only relevant to
phone/email reveal polling -- not used here), `apollo_people_match` with
`reveal_phone_number` or any `run_waterfall_*` flag set to true (plain
`apollo_people_match` for a work email, with no reveal flags, is fine).

## The `src/cli_tools.py` interface

For everything that isn't an Apollo call, use this project's existing,
tested logic instead of reimplementing it:

```
python -m src.cli_tools list-tools
python -m src.cli_tools new-run                          # start a fresh run id for a new demo/session
python -m src.cli_tools call <tool_name> '<json args>'
```

Available tool names: `check_duplicate`, `qualify_lead`, `store_lead`,
`cc_extract_evidence`, `cc_submit_outreach_draft`, `cc_request_approval`,
`cc_record_approval_decision`, `generate_report`. Run `list-tools` if
you need to see the exact argument schema for any of them.

## Step-by-step procedure

1. **Parse the objective.** Determine target_count, location, industry keywords.
2. **Start a run**: `python -m src.cli_tools new-run` (skip this if continuing
   a run you already started in this same conversation).
3. **Discover candidates**: call `apollo_organizations_lookup` with the
   location and industry keyword filters. This is free -- say so, then call it.
4. **For each candidate, up to target_count** (stop once you have that many
   qualified attempts -- you don't need to enrich every candidate returned):
   a. **Disclose and call** `apollo_organizations_enrich` for its domain
      (state: tool name, domain, "1 credit if found, 0 if not").
   b. Call `cc_extract_evidence` with the real `description`/`keywords` you
      got back.
   c. Call `check_duplicate` with the company's name and domain.
   d. Call `qualify_lead` with a company object built from the enrichment
      response (`name`, `domain`, `industry`, `city`, `country`,
      `employee_count`, `apollo_org_id`, `description`, `evidence` from
      step b) and `has_decision_maker` (fill this in after step e).
   e. **Attempt** `apollo_mixed_people_api_search` for a decision-maker at
      that domain (disclose first; if it's denied, note that plainly and
      set `has_decision_maker: false` -- do not retry it for this company).
   f. Call `store_lead` with the company object, the contact object (if
      any, mapped the same UNKNOWN-safe way), and the qualification result.
5. **For each stored lead that has a contact**: compose the outreach draft
   yourself, using ONLY facts you actually gathered (company name,
   industry, city, country, employee count, the real evidence string,
   contact name/title, qualification classification) -- follow the same
   rules already encoded in `src/agents/outreach_agent.py`'s system prompt
   (never mention UNKNOWN fields, cite which facts you used, under 150
   words, one clear call to action, sign off as "The J-WALT Team").
   Call `cc_submit_outreach_draft`, then `cc_request_approval`, then
   present the draft to the user via `AskUserQuestion`
   (Approve/Reject/Edit), then call `cc_record_approval_decision` with
   their answer. Never proceed as if a draft were approved without an
   explicit answer from the user.
6. **When done**: call `generate_report` and present it to the user
   directly, including: how many companies you found via the free lookup,
   how many you enriched (and total credits spent, from your own running
   count), how many were duplicates, the qualification breakdown, whether
   decision-maker search worked or was denied, how many drafts were
   created, and how many were approved/rejected/edited.

## After the demo/run

Do not make any further Apollo calls without the user asking again --
this includes re-running the same objective, enriching more companies, or
retrying a denied endpoint "just to check."
