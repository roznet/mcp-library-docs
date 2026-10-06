---
name: sync-all-designs
description: Sync every design doc against code via a resumable Workflow (one subagent per doc), then reconcile INDEX.md and surface obsolescence findings for plans/future/archive/sub-docs. Token-expensive — run occasionally.
argument-hint: "[--apply | --recommend-only] (default: apply content fixes in place, recommend structural changes)"
disable-model-invocation: true
allowed-tools: Bash(find:*), Bash(ls:*), Bash(grep:*), Read, Edit, Write, Grep, Glob, Workflow, Agent
---

# Sync all design docs

Audit and update **every** doc under `designs/`. This is the bulk version of `/sync-designs`:
the heavy per-doc work runs as a **resumable Workflow** (`sync-all-designs.js`, next to this
file) that fans out one subagent per doc. This skill does the parts a workflow can't:
enumerating files up front, then reconciling INDEX.md and structural changes afterwards.

Run it **occasionally**, for example after a big feature lands or when the docs feel stale.
It spawns one agent per doc, so it costs a lot of tokens on a large `designs/` folder. If the
run dies part-way, resume it (Step 3): docs that finished return cached, and only the rest
re-run.

Mode (from `$ARGUMENTS`):
- Default / `--apply`: subagents **edit their own doc in place** to fix content drift, but only
  **recommend** structural changes (delete, move to `archive/`, promote to INDEX, rename).
- `--recommend-only`: subagents change nothing; every finding is reported for review first.

## Step 0 — Locate the design-doc guide

The per-doc agents follow the `sync-designs` skill's principles. Find its `SKILL.md`, checking
in order: the project's `.claude/skills/sync-designs/SKILL.md`, then
`~/.claude/skills/sync-designs/SKILL.md`. Pass the first path that exists as `args.guide`. If
neither exists, omit `guide`; the workflow then falls back to the short rules in its prompt.

## Step 1 — Enumerate and bucket

The workflow has no filesystem access, so build the doc list here:

1. Read `designs/INDEX.md`. Extract every doc it links with `→ Full doc: NAME.md` (and
   `[text](name.md)` links). This is the **INDEX-referenced** set, the one the
   `mcp-library-docs` server can discover.
2. `Glob designs/**/*.md` for the full set, excluding `INDEX.md`.
3. Bucket each doc:
   - **referenced** — linked from INDEX.md.
   - **sub-doc** — not in INDEX but linked from another design doc (grep the other docs for
     its filename). Legitimate: synced like a referenced doc, plus a check that the parent
     still links it.
   - **plans** — under `designs/plans/`.
   - **future** — under `designs/future/`.
   - **archive** — under `designs/archive/`.
   - **references** — under `designs/references/`, if the project uses one: operational
     reference data (thresholds, runbook background, data tables) cited by skills or docs
     rather than by INDEX.md. Their "parent" is whatever cites them, so check that the
     citation still resolves.
   - **orphan** — not in INDEX, not linked anywhere, and not in any of the folders above.
     Orphans should be rare; flag them clearly.
   Subfolders other than these are treated like top-level docs (referenced, sub-doc or orphan).
4. Print the bucket counts so the user sees the scope before the fan-out.

## Step 2 — Run the workflow

Invoke the workflow script bundled with this skill, passing the bucketed list as `args`:

```
Workflow({
  scriptPath: '<this skill's directory>/sync-all-designs.js',
  args: {
    mode: 'apply' | 'recommend-only',
    guide: '<path from Step 0, if any>',
    docs: [ { path: 'designs/foo.md', bucket: 'referenced' }, ... ]
  }
})
```

Pass `args` as a normal JSON object. The workflow spawns one agent per doc. Each agent edits
**only its own file** (no INDEX.md, no cross-doc edits), so parallel writes can't collide. It
returns `{ mode, total, reports, failed }`, where each report is
`{ doc, bucket, verdict, changed, indexAction, structural }`.

**Note the `runId` and the persisted `scriptPath`** from the tool result; you need them to resume.

**No Workflow tool in this session?** Do the same fan-out with the `Agent` tool instead: run
the per-doc prompt from `sync-all-designs.js` (`buildPrompt`) for each doc, a few at a time,
and collect the same report fields from each agent.

## Step 3 — Resume if it died

If the workflow was killed or lost its connection before finishing, relaunch with:

```
Workflow({ scriptPath: '<persisted path>', resumeFromRunId: '<runId>',
           args: { ...same args... } })
```

Completed docs return cached instantly; only failed or unfinished docs re-run. Keep the same
`args` so the cache matches.

## Step 4 — Reconcile

Cross-cutting work the workflow deliberately leaves alone:

1. **INDEX.md:** collect every `indexAction` from the reports. In `apply` mode, edit INDEX.md
   to add missing referenced docs and fix or remove stale entries (entries pointing at docs
   that no longer exist, or whose description or `Key exports:` are now wrong). In
   `recommend-only` mode, list the proposed edits instead. Follow the INDEX.md format in the
   `sync-designs` skill: the `→ Full doc:` arrow notation is required for MCP discovery.
2. **Stale INDEX entries:** cross-check INDEX links against the Step 1 file list and flag any
   `→ Full doc:` pointing at a missing file.
3. Do **not** delete, move or rename anything yourself.

## Step 5 — Report

Summarize:
- the bucket counts, how many docs were in sync vs updated, and any `failed` docs (with the
  resume command to retry them);
- the INDEX.md changes made (or proposed, in `recommend-only` mode);
- a **structural action list**: every recommend-archive, recommend-delete,
  recommend-promote, orphan and wrongly-archived finding, grouped, each with its one-line
  justification, for the user to approve. Don't act on these without a go-ahead.

End with a one-line `result:` headline, for example
`result: synced N design docs, M updated, K structural changes proposed for review`.
