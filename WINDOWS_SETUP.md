# Windows Setup Guide (no Python experience needed)

This is the simplest way to run the J-WALT agent on Windows. No PowerShell
commands to type by hand -- you double-click two files.

## What you need first

- **Windows 10 or 11.**
- **The project folder** (`jwalt-ai-agent`) downloaded or cloned onto your
  computer.
- **An Anthropic API key** and an **Apollo.io API key**. Get them from
  https://console.anthropic.com and https://developer.apollo.io -> API Keys.
  Keep these private -- never paste them into a chat, email, or document.

## Step 1: Run the setup

Open the `jwalt-ai-agent` folder in File Explorer and **double-click
`setup.bat`**.

A black window will open and, one step at a time, it will:
1. Check that Python 3.11+ is installed (and tell you exactly how to
   install it, with a link, if it isn't).
2. Check whether Git is installed (optional -- just a heads-up if it's
   missing, not required to run the agent).
3. Create a private Python environment for this project (`.venv`).
4. Install everything the project needs.
5. Create your personal `.env` file and **open it in Notepad automatically**
   the first time.
6. Verify the project works.
7. Run the full automated test suite.

**When Notepad opens** (step 5), fill in these two lines:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
APOLLO_API_KEY=your-real-apollo-key-here
```
Leave every other line as it is. Save (Ctrl+S), close Notepad, then go back
to the black window and press Enter to let setup continue.

At the end you should see `Setup complete!` and a test count like
`80 passed, 2 skipped`. If you see red `ERROR:` text instead, read it --
it tells you plainly what went wrong (most commonly: Python wasn't
installed, or wasn't added to PATH).

**This step only needs to be done once**, unless you get a fresh copy of
the project.

## Step 2: Run the agent

Double-click **`run-agent.bat`**.

This will, one step at a time:
1. Check that `.env` actually has both keys filled in (it never shows you
   the key values -- just confirms something is there).
2. Run a tiny **live** test of your Anthropic key.
3. Run a tiny **live** test of your Apollo key (costs at most 1 credit).
4. If both succeed, run the real agent with the objective **"Find 3
   potential Dubai hotel clients for J-WALT"**.

If either key test fails, it stops there and tells you exactly what's
wrong -- it will not go on to spend more credits or run the full agent on
a broken credential.

### What actually happens when the agent runs

The agent will really: search Apollo for up to 3 Dubai hotel companies,
check your local database so it never creates the same lead twice, look
for a decision-maker contact at each company, score each one against
J-WALT's qualification rules, save the qualified ones to your local
database (`data/leads.db`), and write a personalized draft email for each
lead it found a contact for.

**It will then ask you, for each draft:**
```
[A]pprove / [R]eject / [E]dit?
```
Type `A`, `R`, or `E` and press Enter. **Whatever you choose, no email is
ever sent** -- this project has no code capable of sending an email at
all, by design. Approving just records your decision in the report.

### Distinguishing real results from a test run

- A line starting with `[LIVE]` is a real result from a real API call.
- A line starting with `[DRY RUN]` (see below) is a simulation.
- You'll never see both in the same run -- they're two entirely separate
  code paths.

## Optional: the safe practice run (no API keys needed at all)

Before spending anything, you can see the whole pipeline run on made-up
example data with zero risk:
```
run-agent.bat -DryRun
```
(Open Command Prompt in the folder to pass that option -- a plain
double-click always runs the real 3-hotel-leads test from Step 2.)

## Optional: a different search

Open Command Prompt in the `jwalt-ai-agent` folder (right-click inside the
folder in File Explorer -> "Open in Terminal") and run:
```
run-agent.bat -Objective "Find 5 Dubai retail companies opening new stores" -NonInteractive
```
`-NonInteractive` means it will automatically decline every draft instead
of asking you -- useful for a quick hands-off check. Drop it to review and
respond to each draft yourself.

## If something goes wrong

Every script prints plain-English `ERROR:` lines when something fails,
and stops rather than guessing or faking a result. Copy the red text and
share it -- that's exactly what's needed to fix it.

## What Claude Code could NOT do for you

Claude Code prepared and reviewed every file in this guide, but it was
running in a Linux environment with no access to a Windows machine and no
PowerShell available to test with. It could not, and did not, click
anything on your computer, install Python for you, or run these `.bat`
files itself. See the chat response for the exact list of what still
needs your hands on your keyboard versus what these scripts automate.
