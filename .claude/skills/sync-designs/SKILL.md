---
name: sync-designs
description: Review and update design documents to stay in sync with code. Invoke to audit, update, or create design docs.
allowed-tools: Read, Grep, Glob, Edit, Write, Agent
---

# Design Document Sync

Maintain design documentation that stays aligned with code.

## Purpose

These design docs are **context for Claude** but remain human readable - they exist so you can quickly load them before working on a feature. They should contain what YOU need to:
- Understand the architecture and how components fit together
- Know the intent behind decisions (the "why")
- Follow established patterns and conventions
- Respect previous design choices
- Be effective immediately without re-discovering context

Write these docs as if you're leaving notes for your future self before context resets.

## When Invoked

Determine the mode based on arguments:

### Mode A: Sync Existing Docs (no args or design doc path)
1. **Locate design docs**: Look for `designs/` folder or `designs/INDEX.md`
2. **Cross-check with code**: For each design doc, verify against actual implementation
3. **Check INDEX.md**: Ensure all design docs have entries with `→ Full doc: name.md` links, and remove stale entries for deleted docs
4. **Update or report**: Fix outdated sections or report discrepancies

### Mode B: Create New Design Doc (code path provided)
1. **Explore the code**: Read and understand the feature/component at the given path
2. **Identify boundaries**: Determine what belongs in this design vs related docs
3. **Create design doc**: Generate `designs/<feature_name>.md` following the principles below
4. **Update INDEX.md**: Add entry to `designs/INDEX.md` following the INDEX.md Format section below (create INDEX.md from template if needed)

## Design Doc Principles

### Keep Docs Small
- Each doc should be < 300 lines (minimize context usage)
- Split large docs into sub-components that cross-reference each other
- Prefer multiple focused files over one monolithic doc

### Content Focus
Each design doc should contain what Claude needs to be effective:
- **Intent**: Why this feature/component exists (so you don't accidentally break the purpose)
- **Architecture**: High-level structure and key components (so you know where to look/edit)
- **Choices**: Important decisions and their rationale (so you don't redo or contradict them)
- **Patterns**: Conventions to follow (so new code stays consistent)
- **Usage Examples**: Concise, representative code showing how to use the API (so you see intent, patterns, and conventions quickly)
- **Gotchas**: Non-obvious constraints or edge cases (so you don't fall into known traps)
- **References**: Links to related design docs or key code paths (so you can dive deeper)

### Usage Examples Guidelines
Include 2-3 concise examples that show:
- **Intent**: How the API is *meant* to be used
- **Patterns**: The idiomatic way to chain/combine things
- **Conventions**: What "good code" looks like in this codebase

Do NOT include:
- Every method variant (just representative ones)
- Full API signatures with all parameters (read the code for that)
- Exhaustive examples (pick the most illustrative)

Good example (shows pattern):
```python
# Parse → Categorize → Filter → Use
briefing = ForeFlightSource().parse("briefing.pdf")
critical = briefing.notams_query.for_airport("LFPG").runway_related()
```

Bad example (too exhaustive):
```python
# 50 lines showing every filter method...
```

### Avoid
- Implementation details that duplicate code (you can read the code directly)
- Line-by-line explanations (wastes context tokens)
- Full class implementations (that's what the code is for)
- Content that changes frequently with minor code updates (hard to keep in sync)
- Generic documentation for humans (this is Claude-to-Claude knowledge transfer)

### Structure Convention
```
designs/
├── INDEX.md              # Overview + links to all design docs
├── feature_name.md       # Individual feature designs
└── subsystems/           # Optional: group related designs
    ├── auth.md
    └── data_layer.md
```

### INDEX.md Format

The INDEX.md file is parsed by the `mcp-library-docs` MCP server to discover design docs. It uses arrow notation (`→`) to link to doc files — this is **required** for discovery.

**Template:**
```markdown
# {Project Name}

> One-line description of what this project does

Install: `pip install {package}` or `import from {path}`

## Modules

### {module_name}
Brief description of what this module does (1-2 sentences).
Key exports: `export1`, `export2`, `export3`
→ Full doc: {module_name}.md

### {another_module}
Brief description.
Key exports: `func1`, `ClassA`
→ Full doc: {another_module}.md
```

**Rules:**
- Each entry must include `→ Full doc: {name}.md` — this is how the MCP server discovers topics
- Markdown links `[text](name.md)` also work for discovery but arrow notation is preferred
- Keep descriptions to 1-2 sentences focused on use case, not implementation
- List key exports (main functions/classes users will import)
- Order entries by importance — most commonly used modules first
- Topic names must start with a word character and can contain word chars and hyphens (e.g., `data-layer.md`, `auth.md`)

### Cross-References
Use relative links between docs:
```markdown
See [Authentication Design](./subsystems/auth.md) for auth flow details.
```

## Create Workflow

When creating a new design doc from code:
1. Explore the code thoroughly (use Task/Explore agent if complex)
2. Identify the core purpose and boundaries of the feature
3. Document the "why" not just the "what"
4. Extract key architectural decisions visible in the code
5. Note any patterns, conventions, or dependencies
6. Keep it concise - capture essence, not exhaustive detail
7. Add to `designs/INDEX.md` following the INDEX.md Format convention (with `→ Full doc: name.md`)

Template for new docs:
```markdown
# Feature Name

> One-line summary of what this feature does

## Intent
Why this exists, what problem it solves. What should NOT change.

## Architecture
Key components and how they interact. Where to find things.

## Usage Examples
2-3 concise examples showing the intended way to use this feature.

## Key Choices
Decisions made and WHY - so future Claude doesn't revisit or contradict them.

## Patterns
Conventions to follow when extending this feature.

## Gotchas
Non-obvious things that will bite you if you don't know them.

## References
- Related docs: [link](./other.md)
- Key code paths: `src/path/to/main/file.swift`
```

## Sync Workflow

When checking sync status:
1. Read the design doc
2. Identify key components/files it describes
3. Use Grep/Glob to find those in code
4. Compare documented behavior vs actual implementation
5. Update doc if discrepancies found, or note if code should change

## Arguments

- **No args**: Audit all docs in `designs/`
- **Design doc path**: Focus on specific doc (e.g., `/sync-designs auth.md`)
- **Code path**: Create new design from code (e.g., `/sync-designs src/features/auth/`)
- **Feature name**: Create/sync by feature name (e.g., `/sync-designs authentication`)

The skill infers the mode:
- If arg matches an existing design doc → sync that doc
- If arg matches a code path → create design doc from that code
- If arg is a feature name → check if design exists, sync or offer to create
