# AI-Assisted Development with Claude: Tips from My Workflow

> This document describes how my AI-assisted development workflow has evolved over time — what's worked for me, what I've learned, and how I use Claude Code, MCP servers, and design docs to stay productive. It's not "the one true way" — it's advice and patterns I've found useful, and I hope some of it helps you too.
>
> The [README](README.md) has the condensed version and a step-by-step adoption guide. The real skills described here are public in [flyfun-weather/.claude](https://github.com/roznet/flyfun-weather/tree/main/.claude).

## Preamble: Markdown as Infrastructure

### The Setup

I keep markdown documents consolidated into a `designs/` directory within my repositories. This is the convention the `mcp-library-docs` MCP server expects, and it's worked well for me.

```
your-repo/
├── designs/
│   ├── INDEX.md                    # Overview + links to all design docs
│   ├── pricing-engine.md           # Feature/component design documents
│   ├── market-data-loader.md
│   ├── future/                     # Brainstorms and designs not yet built
│   ├── plans/                      # Implementation plans for in-flight work
│   ├── archive/                    # Superseded designs, kept for history
│   └── references/                 # Runbook data that skills cite
├── .claude/
│   ├── CLAUDE.md                   # Project-level instructions for Claude
│   ├── settings.json               # Project permissions
│   ├── commands/                   # Older-style slash commands (code-review, process-review)
│   └── skills/
│       ├── implement-issue/SKILL.md   # Project skills (slash commands)
│       ├── land-pr/SKILL.md
│       ├── worktree-init/SKILL.md
│       └── deploy/SKILL.md
├── .github/workflows/
│   └── claude-code-review.yml      # Review bot on every PR push
└── src/
```

`/sync-designs` and `/sync-all-designs` aren't in that tree because they're installed once at user level (`~/.claude/skills/`) and used in every repo. Generic versions ship in this repo.

### Why I Think It Works

Claude Code has full filesystem access and can read, write, and search across your codebase. But in my experience, undirected codebase exploration tends to burn context tokens on discovery rather than reasoning. A curated `designs/` directory gives Claude the distilled knowledge it needs to be effective immediately — architecture, intent, file maps, conventions, and gotchas — without re-discovering it from source every session.

These documents are **context for Claude but remain human-readable**. I think of them as notes I leave for my future self before a context reset.

### The MCP Layer

The [mcp-library-docs](https://github.com/roznet/mcp-library-docs) MCP server adds automatic discovery on top of the markdown files. Once configured, Claude can:

- Call `list_libraries` to see all available design docs across your current project and any registered external libraries
- Call `get_design_doc(library, topic)` to load a specific doc on demand
- Distinguish between `[current project]`, `[library]` (importable code), and `[project]` (patterns/reference only)

Setup, once for all projects:
```bash
pip install mcp-library-docs
claude mcp add --scope user library-docs -- python -m mcp_library_docs
```

Add a short "Always start here" rule to `CLAUDE.md` telling Claude to call `list_libraries` before grepping (the README has the exact block). Without it, Claude often skips the docs.

External libraries can be registered in a `config.yaml` so Claude knows about shared utilities, internal frameworks, and reference projects — and knows whether to import from them or just learn patterns.

---

## 1. Design-First Feature Development

### The Workflow

Before writing any code for a new feature, I like to use Claude as a design partner:

1. **Start with intent.** Tell Claude you want a design document, not code:
   *"We're going to design the new risk aggregation feature. Don't write code yet — let's produce a design document in `designs/risk-aggregation.md` and iterate until we're happy with the approach."*

2. **Have Claude ask questions.** Claude can explore the codebase to understand what exists, but you should also prompt it to surface what it doesn't know:
   *"What do you need to know about our requirements and existing infrastructure to design this well? Read `designs/INDEX.md` to see what's already documented, then ask me questions about anything that's unclear."*

3. **Iterate on the document.** Claude edits the design doc directly. Each round of feedback produces a cleaner document, not a longer chat history. Use the `Edit` tool — the document is the artifact, not the conversation.

4. **Cross-validate.** Open a fresh Claude session (or use ChatGPT/Gemini) and paste the design doc:
   *"Review this design for gaps, risks, incorrect assumptions, and missing edge cases. Be critical."*
   A fresh session has no commitment to the choices made during the design conversation.

5. **Save before implementing.** The design doc in `designs/` becomes the contract for implementation.

### With MCP: Context-Aware Design

When `mcp-library-docs` is configured, the design phase gets richer:

- Claude can call `list_libraries` to see what shared utilities and patterns already exist across your projects
- Before designing a new component, Claude can check whether a similar pattern exists in a registered library: *"Check if any of our libraries already handle yield curve interpolation before we design our own."*
- Design docs can reference library components with confidence that Claude will be able to find them later during implementation

### Why I Think This Works Better Than Jumping to Code

Claude is a strong coder and it's tempting to just let it build. But in my experience, design-first produces better outcomes because:

- It forces articulation of intent before commitment to implementation
- It creates a reviewable artifact that outlives the session
- It catches architectural mistakes when they're cheap to fix (minutes of reading vs. hours of debugging)
- The design doc becomes reusable context for future sessions working on the same feature

---

## 2. Component Context Documents

### Structure and Content

Here's the template I've settled on for design docs — it's optimized for what Claude needs to load context quickly:

```markdown
# Market Data Loader

> Fetches, normalizes, and caches market data from multiple providers.

## Intent
Provides a single interface for all market data access. All downstream consumers
(pricing engine, risk, analytics) should go through this module rather than
calling providers directly. This ensures consistent data normalization and
caching across the system.

## Architecture
Key components and how they interact. Where to find things.

## File Map
- `src/market_data/provider.py` — Provider abstraction and factory
- `src/market_data/bloomberg.py` — Bloomberg terminal adapter
- `src/market_data/refinitiv.py` — Refinitiv/LSEG adapter
- `src/market_data/cache.py` — Redis-backed time-series cache with TTL by data type
- `src/market_data/normalizer.py` — Cross-provider field mapping and unit conversion
- `tests/market_data/` — Integration tests (require mock provider fixtures)

## Usage Examples
# Standard data retrieval — cache handles dedup automatically
loader = MarketDataLoader(provider="bloomberg")
spot_prices = loader.get_spot("AAPL", start="2024-01-01", end="2024-06-30")
curve = loader.get_yield_curve("USD", tenor_points=["1M", "3M", "1Y", "5Y", "10Y"])

# Multi-provider fallback
loader = MarketDataLoader(providers=["bloomberg", "refinitiv"], fallback=True)
px = loader.get_spot("VOD.L")  # Tries Bloomberg first, falls back to Refinitiv

## Key Choices
- Provider fallback is opt-in, not default — silent fallback masks data quality issues
- Cache TTL varies by data type: spot=5min, curves=1hr, reference=24hr
- Normalization happens at ingestion, not at query time

## Patterns
- All new providers must implement `BaseProvider` protocol in `provider.py`
- Field mapping goes in `normalizer.py`, never in provider adapters
- Tests use `FakeProvider` fixture, not mocks of specific providers

## Gotchas
- Bloomberg adapter requires an active terminal session; CI uses Refinitiv only
- Yield curve tenors must be passed as strings ("1Y"), not timedeltas
- Cache key includes provider name — same instrument from different providers
  is cached separately (this is intentional, provider data can differ)

## References
- Related: [Pricing Engine](./pricing-engine.md), [Risk Aggregation](./subsystems/risk-aggregation.md)
- Key code paths: `src/market_data/`
```

### What I've Found Works

**Keep docs under 300 lines.** I try to minimize context usage. Splitting large features into sub-components that cross-reference each other has worked better for me than one monolithic doc.

**Document the "why", not the "what".** Claude can read the code for implementation details. What it can't infer is intent, the reasoning behind choices, and constraints that aren't visible in the code.

**Include usage examples that show patterns, not exhaustive APIs.** I aim for 2-3 examples showing the *intended* way to use the component. Claude can read the code for the full API.

**Avoid content that duplicates code.** Full class implementations and line-by-line explanations tend to go stale fast. If it changes with every minor code update, it probably doesn't belong in the design doc.

### INDEX.md: The Discovery Layer

The `INDEX.md` at the root of `designs/` is parsed by the `mcp-library-docs` MCP server to discover available docs. It uses arrow notation (`→`) which is required for automatic discovery:

```markdown
# Risk Analytics Platform

> Portfolio analytics, pricing, and risk management

## Modules

### market-data-loader
Fetches, normalizes, and caches market data from multiple providers.
Key exports: `MarketDataLoader`, `BaseProvider`, `get_spot`, `get_yield_curve`
→ Full doc: market-data-loader.md

### portfolio-analytics
Portfolio-level calculations: returns, attribution, factor exposures.
Key exports: `PortfolioAnalyzer`, `compute_returns`, `factor_decomposition`
→ Full doc: subsystems/portfolio-analytics.md

### pricing-engine
Derivatives pricing: Black-Scholes, Monte Carlo, binomial models.
Key exports: `price_option`, `PricingModel`, `GreeksResult`
→ Full doc: pricing-engine.md
```

Guidelines for INDEX.md:
- Each entry needs `→ Full doc: {name}.md` — this is how the MCP server discovers topics
- I try to keep descriptions to 1-2 sentences focused on use case
- Listing key exports (main functions/classes consumers will import) helps Claude know what's available
- I order by importance — most commonly used modules first

### With MCP: On-Demand Context Loading

When `mcp-library-docs` is active, Claude doesn't need to be told which docs to read. The workflow becomes:

1. Claude calls `list_libraries` to see the INDEX of available design docs
2. Based on the task, Claude calls `get_design_doc` for the relevant components
3. Claude loads only what it needs — no wasted context on unrelated modules

This is the automated version of manually saying "read `designs/market-data-loader.md` first."

---

## 3. Skills (Slash Commands)

### How Skills Work in Claude Code

In Claude Code, skills are markdown files stored in `.claude/skills/{name}/SKILL.md`. Each skill gets its own subdirectory, and the file must be named `SKILL.md`. They have YAML frontmatter declaring allowed tools and are invoked as slash commands:

```
/sync-designs market-data-loader
/implement-issue 42
/land-pr 57
```

A skill file (e.g. `.claude/skills/sync-designs/SKILL.md`) looks like this:

```markdown
---
name: sync-designs
description: Review and update design documents to stay in sync with code.
allowed-tools: Read, Grep, Glob, Edit, Write, Agent
---

# Design Document Sync

## Purpose
These design docs are context for Claude but remain human readable...

## When Invoked
Determine the mode based on arguments:

### Mode A: Sync Existing Docs (no args or design doc path)
1. Locate design docs: Look for `designs/` folder or `designs/INDEX.md`
2. Cross-check with code: For each design doc, verify against actual implementation
3. Check INDEX.md: Ensure all design docs have entries with `→ Full doc:` links
4. Update or report: Fix outdated sections or report discrepancies

### Mode B: Create New Design Doc (code path provided)
1. Explore the code: Read and understand the feature/component
2. Identify boundaries: Determine what belongs in this design vs related docs
3. Create design doc: Generate `designs/<feature_name>.md`
4. Update INDEX.md: Add entry with `→ Full doc: name.md`
```

The frontmatter (`---` block) holds the skill's `name` (the slash command), a `description` (which Claude also uses to decide when the skill applies), and optionally `allowed-tools`. Two other frontmatter settings matter in practice:

- **`disable-model-invocation: true`** means the skill only runs when *I* type it. I set it on everything that acts on the outside world: merging, deploying, releasing.
- **Where the skill lives** decides where it works. `.claude/skills/` in a repo is project-only; `~/.claude/skills/` works everywhere. `sync-designs` is generic, so it lives at user level; `land-pr` knows the project's CI and toolchain, so it lives in the repo.

### Skills I Actually Use

These are the ones that earned their place, with links to the real files:

**[`/sync-designs [target]`](.claude/skills/sync-designs/SKILL.md)** — Keeps design docs aligned with code. No args audits everything in `designs/`; a doc path syncs one doc; a code path creates a new doc from existing code. This is how I bootstrap docs for an existing codebase, and how a PR updates the docs for the code it touched.

**[`/implement-issue <n>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/implement-issue/SKILL.md)** — Takes a GitHub issue end to end: reads the whole comment thread and the design docs, works out whether it's running in the cloud or locally and whether I'm watching, branches, implements, runs what it can verify, updates the touched design docs, and opens a PR. It ends with an **Owner's brief**: what changes for the user, the decisions it made for me, how it could go wrong, what was verified versus only claimed, and specific questions I should ask. I don't read every diff line, so the brief is how I stay in control of what ships.

**[`/process-review [pr]`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/process-review.md)** — Waits for the review bot's comment (Section 6), triages each finding as blocker, cosmetic or unsure, and only pushes when there's a real blocker. Every push triggers another full review, so when it does push it batches in everything worth fixing.

**[`/land-pr <n>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/land-pr/SKILL.md)** — For when I've decided a PR is going in. Checks CI and every review round, runs locally what the cloud couldn't (iOS build and UI tests), rebase-merges, then fixes the remaining findings with a direct commit on main instead of another PR round. It updates design docs and memory notes, and ends with a short landing summary including what the deploy will need. It never deploys.

**[`/worktree-init <branch>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/worktree-init/SKILL.md)** and **`/devserver`** — A sibling git worktree per issue, each with its own venv and dev-server port, so several sessions can work in parallel without stepping on each other.

**`/deploy`** — Pre-flight checks, then a hard stop that needs my explicit "yes" in a separate turn. I added that gate after a deploy was reported as done when it had never actually run.

**How these skills got written.** Almost none were designed up front. When I noticed I'd typed the same multi-step instructions several times, I asked Claude to turn that conversation into a skill, ran it on two or three real PRs, and fixed what went wrong. I also periodically ask Claude to read my recent session transcripts and suggest changes to my process; several skills and rules came out of that.

### Subagents (the Agent Tool)

Claude Code's `Agent` tool lets a session or skill spawn subagents with their own context. I use them less than you might expect: for parallel reviews of a big PR (one per language or area), for audits, and for an independent second opinion on a PR's brief. With good design docs, a single session usually has the context it needs, and that's cheaper than fanning out.

For one heavy job I use a **Workflow** script instead: [`/sync-all-designs`](.claude/skills/sync-all-designs/SKILL.md) runs one subagent per design doc in a resumable workflow, then reconciles `INDEX.md`. It's expensive, so I run it occasionally rather than routinely.

### CLAUDE.md: Project-Level Instructions

The `CLAUDE.md` file at your project root gives Claude persistent instructions that apply to every session. I use it for:

- Project conventions and coding standards
- Which design docs to read before specific types of tasks
- Common patterns and anti-patterns
- Test and build commands
- Any standing instructions that should always apply

```markdown
# CLAUDE.md

## Project Overview
Risk analytics platform. Python 3.11+. See designs/INDEX.md for architecture.

## Before Starting Any Task
1. Read designs/INDEX.md to understand available context
2. Load the design doc for the component you're working on
3. Propose a plan before writing code

## Conventions
- All data access goes through MarketDataLoader, never direct provider calls
- DataFrames use MultiIndex with (date, instrument) — don't flatten
- Tests use FakeProvider fixtures, not mocks of specific providers
- Type hints required on all public functions

## Build & Test
- `pytest tests/` — run all tests
- `pytest tests/market_data/ -x` — run specific module, stop on first failure
- `mypy src/` — type checking
```

---

## 4. Prompt Tips

### Why I Still Think About Prompts

Even with Claude's larger context window and stronger reasoning, I've found that structured prompts produce noticeably better results. The difference is less about preventing the model from going off-track and more about communicating *exactly* what you want efficiently.

### Structured Prompts

For non-trivial tasks, I've had better results when I structure the request:

```
Task: Fix incorrect volatility surface interpolation in pricing engine.

Context: Read designs/pricing-engine.md first.

Problem: The vol surface interpolation returns NaN for tenors between 6M and 1Y
when the strike is more than 20% OTM. Users report incorrect Greeks for
long-dated options.

Constraints:
- Don't change the VolSurface interface — downstream consumers depend on it
- Fix must handle edge cases at surface boundaries
- Add a test that verifies interpolation for the failing tenor/strike combination
- Use scipy's existing interpolation, don't add new dependencies

Start by reading the relevant files and proposing a fix before making changes.
```

### When Conversational Prompts Work Fine

With Claude, you don't need to be as rigidly structured for simpler tasks. *"Fix the TypeError in `src/market_data/cache.py` line 42 — it's passing a string where it expects a datetime"* is perfectly clear for a targeted fix. I save the structured format for tasks where scope, constraints, or intent might be ambiguous.

### One Task, One Session

In my experience, context pollution degrades quality even in large context windows. If I've been debugging the pricing engine and now want to work on the data pipeline, I start a fresh session. Claude Code makes this easy — just open a new session and point it to the relevant design doc.

---

## 5. Plan-Driven Implementation

### The Workflow

1. **Load context.** Claude reads the relevant design docs (via MCP or direct file read).
2. **Request a plan.** *"Based on the design doc and the codebase, write an implementation plan. List the files you'll modify, what changes you'll make to each, and in what order. Don't write code yet."*
3. **Review and iterate.** Read the plan. Does it miss files? Does it respect the key choices in the design doc? Are there unnecessary changes?
4. **Save the plan.** For non-trivial work, have Claude add an `## Implementation Plan` section to the feature's design doc. This creates a reviewable record and lets you resume from a new session.
5. **Execute incrementally.** Claude implements the plan step by step. Because you have a written plan, you can catch deviations: *"That's not in the plan. Why are you changing this file?"*

### Claude-Specific Advantages

- Claude can read the full plan and the full design doc simultaneously without context pressure
- Subagents (the `Agent` tool) can parallelize independent steps of the plan
- Claude can run tests after each step to verify before moving to the next
- If the plan needs adjustment mid-implementation, Claude updates the saved plan document rather than just changing direction in the conversation

### Saving Plans for Complex Work

For anything that takes more than one session or involves coordination with other developers, save the plan:

```markdown
## Implementation Plan

### Step 1: Add basis point conversion utilities
- Create `src/utils/basis_points.py`
- Add `bps_to_decimal()`, `decimal_to_bps()`, `spread_in_bps()`
- Add unit tests in `tests/utils/test_basis_points.py`

### Step 2: Integrate into pricing engine
- Modify `src/pricing/rates.py` — use new bps utilities instead of inline conversion
- Update `src/pricing/spreads.py` — replace hardcoded /10000 with `bps_to_decimal()`

### Step 3: Update downstream consumers
- `src/risk/credit_risk.py` — switch to new utility
- `src/reports/pnl_attribution.py` — switch to new utility

### Step 4: Update design doc
- Add basis_points to designs/INDEX.md
- Update designs/pricing-engine.md with new dependency
```

---

## 6. Cross-Validation and AI-as-Reviewer

### Why I Think Even Claude Benefits from Fresh Eyes

Claude is strong, but a single session still develops commitment to its own direction. The full conversation history conditions every subsequent response. A fresh session evaluates the work without that accumulated bias — at least that's been my experience.

### Validation Workflows

**Design review — fresh Claude session:**
Paste the design doc into a new Claude conversation:
*"Review this design for gaps, risks, incorrect assumptions, and missing edge cases. Be critical — I'd rather hear problems now than discover them in implementation."*

**Code review — fresh Claude session or different model:**
Copy the diff and the design doc into a new session:
```
I'm attaching:
1. The design doc (designs/risk-aggregation.md)
2. The implementation diff

Review for:
- Deviations from the design intent
- Edge cases not handled
- Performance concerns with large portfolios
- Inconsistencies with the patterns described in the design doc
```

**Architecture validation — periodic:**
Feed your full `designs/INDEX.md` and a few key design docs to a fresh session:
*"Review these architecture documents for internal consistency. Are there contradictions? Missing interfaces? Unclear boundaries?"*

**Cross-model validation:**
Using a different model (Gemini, GPT-4) for review adds diversity — different models have different blind spots and training biases. This is especially valuable for design review where reasoning patterns matter more than code syntax.

### The Review Bot

For routine review, I don't open a fresh session by hand. A [GitHub Action](https://github.com/roznet/flyfun-weather/blob/main/.github/workflows/claude-code-review.yml) (set up with `/install-github-app`) runs my [`/code-review`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/code-review.md) command on every push to a PR. Because it runs in CI, it's a genuinely fresh session with no stake in the implementation. A few things made it work well:

- **One complete pass.** The prompt insists on reporting every finding at once, grouped as Critical, Important and Minor, instead of drip-feeding issues over several rounds.
- **Post before finishing.** In CI there's no follow-up turn, so a review that isn't posted didn't happen. The command says so explicitly.
- **A fixed output format.** `/process-review` and `/land-pr` find the review by matching its first line, so the comment shape is a contract written into both the reviewer and the reader. Make the reader tolerant anyway: the format drifted once and the watcher silently found nothing.

For high-risk PRs I add [`/brief-check`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/brief-check/SKILL.md): a separate agent re-derives the Owner's brief from the diff and the issue, and posts what the implementing agent missed, understated or overstated.

---

## 7. MCP Server Integration

### mcp-library-docs: Cross-Project Context

The `mcp-library-docs` server is what I built to connect design docs across multiple projects. It provides three tools:

**`list_libraries(cwd)`** — Returns all INDEX.md contents from the current project and any registered external libraries. Each is tagged with its type:
- `[current project]` — The repo you're working in
- `[library]` — Shared code Claude can import from
- `[project]` — Reference patterns, don't import

**`get_design_doc(library, topic)`** — Loads a specific design doc. Claude uses this to load context on demand rather than reading everything upfront.

**`get_index_status(cwd)`** — Shows which docs need adding to INDEX.md and which entries are stale. Useful before running `/sync-designs`.

### Configuration for Shared Libraries

Register external libraries in `~/.config/mcp-library-docs/config.yaml`:

```yaml
libraries:
  # Shared analytics utilities — Claude should import from this
  analytics-utils:
    path: ~/projects/analytics-utils
    type: library

  # Risk framework for reference — learn patterns, don't import
  risk-framework:
    path: ~/projects/risk-framework
    type: project

  # Legacy data layer with custom doc location
  legacy-data:
    path: ~/projects/legacy-data
    designs_dir: docs/design
    index_file: README.md
    cache: static
```

### Other MCP Servers

The MCP protocol is open — other servers can provide Claude with additional context. Some examples:

- Database schema servers — give Claude access to table definitions and relationships
- API documentation servers — let Claude look up internal API specs
- Task tracker integrations — load Jira ticket context into Claude sessions

Each server extends what Claude can discover without manually copying context into prompts.

---

## 8. Workflow Integration

### Git Workflow

I keep design docs with the code and follow the same branching and review process:

- **Feature branches include their design docs.** When I create a branch for a feature, the design doc lives in that branch and evolves with the code. Reviewers see both intent and implementation.
- **PRs that change architecture update design docs.** I try to make this a review checklist item. If you change how market data caching works, `designs/market-data-loader.md` should ideally be updated in the same PR.
- **Run `/sync-designs` before PRs.** The skill catches docs that have drifted from the code.
- **Design docs as PR descriptions.** Linking to or summarizing the relevant design doc gives reviewers context they'd otherwise have to infer from the diff.
- **Merge, then fix on main.** Once I've decided a PR is good enough, leftover minor findings get fixed in a direct follow-up commit on main (`/land-pr` does this). Another PR round would cost another full review for little gain.
- **Brainstorms are committed too.** Design discussions end with *"save the brainstorm into a designs/future document, commit it to main, then create the issue referring to it"*. Decisions made later go in issue comments, and `CLAUDE.md` tells Claude to read the whole comment thread, not just the issue body.

### Stale Doc Prevention

Stale docs are worse than no docs. Here's what I do to fight staleness:

- Make the implementing skill update the docs for the code it touched, in the same PR (`/implement-issue` does this, and `/land-pr` checks it)
- Run `/sync-designs` periodically, or the full `/sync-all-designs` workflow after a big feature lands
- Use `get_index_status` to check for missing or orphaned entries
- Add a CI step that flags PRs modifying files referenced in a design doc's File Map when the design doc itself hasn't been modified
- The `/sync-designs` skill has been my main tool for this — it reads the code and updates docs, catching drift that I'd miss manually

---

## Quick Reference: My Session Startup

Here's what a typical session looks like for me on a non-trivial task:

1. Claude calls `list_libraries` (via MCP) to see available context
2. Claude loads the relevant design doc(s) with `get_design_doc`
3. State the task — structured format for complex tasks, conversational for simple ones
4. Claude proposes a plan → review and iterate
5. Execute incrementally, test after each step
6. Cross-validate with a fresh session when done
7. Run `/sync-designs` if architecture changed
8. `/clear` and start fresh for the next task. I use `/clear` far more than `/compact`

---

## 9. The Phone Workflow: Issue-to-PR from Anywhere

This is the payoff for all the setup above, and honestly the moment where it clicked for me that the investment in design docs and skills was worth it.

Once your `designs/` directory, `CLAUDE.md`, skills, and MCP server are all in place, Claude has enough context to work autonomously on well-scoped tasks. Which means you don't need to be at your desk to get things done.

### How It Works

1. **Create a GitHub issue from your phone.** I use the GitHub mobile app. The issue description is essentially a prompt — I write it the same way I'd describe a task to Claude: clear intent, constraints, and what "done" looks like.

2. **Open Claude on your phone.** I pull up the Claude app, start a Claude Code session on the web and run `/implement-issue 42`. Before that skill existed, the prompt was simply *"Work on and implement issue #42. Make sure you read the design docs first."*

3. **Go do something else.** Walk the dog, commute, make dinner — whatever. Claude reads the design docs (via MCP locally; in a cloud session, where my local MCP server isn't available, the `CLAUDE.md` fallback points it at `designs/INDEX.md` directly), understands the codebase context, implements the feature, writes tests, and opens a PR.

4. **Come back to a PR and an Owner's brief.** The brief is written to fit on a phone screen, so I can read it, ask follow-up questions, and decide before I'm back at a computer.

5. **Land it on the Mac.** The cloud has no Xcode, so `/land-pr` runs locally, builds and tests what the cloud couldn't, and merges.

Alongside cloud sessions, local sessions on my Mac are bridged to the Claude app with Remote Control, so I can steer and approve them from my phone too. A permission hook auto-approves safe commands, so parallel sessions rarely sit waiting on a prompt.

By the time I'm back at my desk, there's usually a PR waiting with proper tests, consistent patterns, and code that follows the conventions documented in `CLAUDE.md` and the design docs. And I can have multiple issues in progress this way — I just start a session for each issue and let them run in parallel.

### Why This Works

This isn't magic — it only works *because* of everything described in the earlier sections:

- **Design docs** give Claude the architectural context it needs without you explaining it each time
- **`CLAUDE.md`** gives it the project conventions and standing instructions
- **The MCP server** lets it discover and load the right context on its own
- **A well-written issue** acts as a structured prompt with clear scope

Without that foundation, you'd get code that compiles but doesn't fit the project. With it, Claude has enough context to produce code that looks like you wrote it.

### Tips for Writing Good Issues-as-Prompts

I've found that the issues that work best as Claude prompts are the ones that would also make good tickets for a junior developer who knows the codebase:

- **State the goal, not just the task.** *"Users need to filter by date range"* is better than *"Add a date picker."*
- **Mention constraints.** *"Don't change the API contract"* or *"This needs to work with the existing cache layer."*
- **Reference the relevant design doc if it's not obvious.** *"See designs/market-data-loader.md for context."*
- **Keep scope small.** One feature, one bug fix, one refactor. If it would take you more than a session to review the PR, it's probably too big.

### What It's Not

This doesn't replace thinking about design or reviewing code. I still review every PR before merging, and for anything architecturally significant, I still do design-first (Section 1). But for well-scoped tasks in a well-documented codebase, it's been a genuine productivity multiplier — I can queue up work during downtime and review results when I'm back at my desk.

---

## Summary: The Toolchain at a Glance

| Capability | Tool | Purpose |
|-----------|------|---------|
| Context docs | `designs/` directory | Persistent, curated knowledge for Claude |
| Auto-discovery | `mcp-library-docs` MCP server | Claude finds and loads docs on demand |
| Cross-project context | `config.yaml` library registration | Claude knows about shared libraries |
| Reusable workflows | `.claude/skills/` skills | Skills invoked as slash commands |
| Project instructions | `CLAUDE.md` | Always-on context for every session |
| Sub-agents | `Agent` tool | Parallel reviews and audits, used sparingly |
| Code sync | `/sync-designs` skill | Keep docs aligned with code |
| Issue → PR | `/implement-issue` skill | Unattended implementation ending in an Owner's brief |
| Review | GitHub Action + `/code-review`, `/process-review` | Fresh-eyes review on every push, triaged by severity |
| Landing | `/land-pr` skill | Merge, then fix leftovers on main |
| Parallel work | `/worktree-init`, Remote Control | Several sessions at once, steerable from the phone |
