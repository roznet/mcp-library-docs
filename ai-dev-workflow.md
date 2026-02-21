# AI-Assisted Development with Claude: Tips from My Workflow

> This document describes how my AI-assisted development workflow has evolved over time — what's worked for me, what I've learned, and how I use Claude Code, MCP servers, and design docs to stay productive. It's not "the one true way" — it's advice and patterns I've found useful, and I hope some of it helps you too.

## Preamble: Markdown as Infrastructure

### The Setup

I keep markdown documents consolidated into a `designs/` directory within my repositories. This is the convention the `mcp-library-docs` MCP server expects, and it's worked well for me.

```
your-repo/
├── designs/
│   ├── INDEX.md                    # Overview + links to all design docs
│   ├── pricing-engine.md           # Feature/component design documents
│   ├── market-data-loader.md
│   └── subsystems/
│       ├── risk-aggregation.md
│       └── portfolio-analytics.md
├── .claude/
│   ├── settings.json               # MCP server configuration
│   └── skills/
│       ├── sync-designs/SKILL.md   # Custom skills (slash commands)
│       ├── validate-arch/SKILL.md
│       └── pre-review/SKILL.md
├── src/
└── CLAUDE.md                       # Project-level instructions for Claude
```

### Why I Think It Works

Claude Code has full filesystem access and can read, write, and search across your codebase. But in my experience, undirected codebase exploration tends to burn context tokens on discovery rather than reasoning. A curated `designs/` directory gives Claude the distilled knowledge it needs to be effective immediately — architecture, intent, file maps, conventions, and gotchas — without re-discovering it from source every session.

These documents are **context for Claude but remain human-readable**. I think of them as notes I leave for my future self before a context reset.

### The MCP Layer

The [mcp-library-docs](https://github.com/roznet/mcp-library-docs) MCP server adds automatic discovery on top of the markdown files. Once configured, Claude can:

- Call `list_libraries` to see all available design docs across your current project and any registered external libraries
- Call `get_design_doc(library, topic)` to load a specific doc on demand
- Distinguish between `[current project]`, `[library]` (importable code), and `[project]` (patterns/reference only)

Setup in `.claude/settings.json` or `.mcp.json`:
```json
{
  "mcpServers": {
    "library-docs": {
      "command": "python",
      "args": ["-m", "mcp_library_docs"]
    }
  }
}
```

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
/validate-arch src/pricing/
/pre-review
```

A skill file (e.g. `.claude/skills/sync-designs/SKILL.md`) looks like this:

```markdown
---
name: sync-designs
description: Review and update design documents to stay in sync with code.
allowed-tools: Read, Grep, Glob, Edit, Write, Task
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

The frontmatter (`---` block) tells Claude which tools the skill is allowed to use: `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Task` (for spawning sub-agents). The `name` field determines the slash command.

### Skills I've Found Useful

**`/sync-designs [target]`** — The skill I use most. Keeps design docs aligned with code. Three modes:
- No args: audits all docs in `designs/` against current code
- Design doc path: syncs a specific doc
- Code path: creates a new design doc from existing code

This is how I bootstrap design docs for an existing codebase — point it at a directory and let it explore and document.

**`/validate-arch [path]`** — Reviews code changes against documented architecture decisions. Reads the relevant design doc(s) and flags code that violates stated patterns, contradicts key choices, or introduces inconsistencies. I find it useful before submitting changes.

**`/pre-review`** — Project-specific checklist before code review. Checks naming conventions, test coverage patterns, error handling conventions, and anything else you've standardized. Reads the project's `CLAUDE.md` and relevant design docs to know what "correct" looks like.

**`/debug-guide [description]`** — Structured debugging workflow: read relevant context docs → reproduce the issue → form hypotheses → instrument → fix → verify → update design doc if the fix reveals a new gotcha.

**`/create-feature-design [name]`** — Bootstraps a new feature design doc from the template and guides you through an interactive design session.

### The Task Tool: Parallel Sub-Agents

Claude Code's `Task` tool lets a skill spawn sub-agents for complex work. The `sync-designs` skill uses this when exploring a large codebase:

- Main agent orchestrates the overall sync
- Sub-agents explore individual modules in parallel
- Results are collected and synthesized into coherent design docs

This is particularly useful for the initial bootstrap of design docs across a large project.

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
- The `Task` tool can parallelize independent steps of the plan
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

### The `/validate-arch` Skill

For routine validation, the `/validate-arch` skill automates the check: it reads the relevant design docs, compares them against the current code, and flags violations. This is faster than manual cross-validation for known patterns, though it doesn't replace the value of a genuinely fresh perspective for design-level review.

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

### Stale Doc Prevention

Stale docs are worse than no docs. Here's what I do to fight staleness:

- Run `/sync-designs` periodically (daily or after significant commits)
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

---

## 9. The Phone Workflow: Issue-to-PR from Anywhere

This is the payoff for all the setup above, and honestly the moment where it clicked for me that the investment in design docs and skills was worth it.

Once your `designs/` directory, `CLAUDE.md`, skills, and MCP server are all in place, Claude has enough context to work autonomously on well-scoped tasks. Which means you don't need to be at your desk to get things done.

### How It Works

1. **Create a GitHub issue from your phone.** I use the GitHub mobile app. The issue description is essentially a prompt — I write it the same way I'd describe a task to Claude: clear intent, constraints, and what "done" looks like.

2. **Open Claude on your phone.** I pull up the Claude app, start a Claude Code session and give it a short prompt:
   *"Work on and implement issue #42. Make sure you read the design docs first."*

3. **Go do something else.** Walk the dog, commute, make dinner — whatever. Claude reads the design docs via MCP, understands the codebase context, implements the feature, writes tests, and opens a PR.

4. **Come back to a PR ready for review.** By the time I'm back at my desk, there's usually a pull request waiting with proper tests, consistent patterns, and code that follows the conventions documented in `CLAUDE.md` and the design docs.

And I can have multiple issues in progress this way — I just start a session for each issue and let them run in parallel.

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
| Sub-agents | `Task` tool | Parallel exploration and implementation |
| Code sync | `/sync-designs` skill | Keep docs aligned with code |
| Architecture checks | `/validate-arch` skill | Catch pattern violations |
