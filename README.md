# mcp-library-docs

This repo has two things:

1. **An MCP server.** It lets Claude Code discover and load short design docs (`designs/INDEX.md` + topic docs). It reads them from the project you're in and from any other libraries and projects you register.
2. **A workflow built on top of it.** This is how I use Claude Code day to day: design docs as Claude's memory of the architecture, skills for the steps I repeat, an automated review bot, and parallel sessions I can drive from my phone. This README describes the workflow as I actually run it. The setup files it describes are public in [flyfun-weather](https://github.com/roznet/flyfun-weather/tree/main/.claude), so you can copy from a working setup instead of a toy example.

> **If you are Claude** and someone pointed you at this repo to help them adopt the workflow, start at [Adopting this workflow (guide for Claude)](#adopting-this-workflow-guide-for-claude). It is written for you.

For a longer, essay-style write-up of the ideas, see [AI Dev Workflow Tips](ai-dev-workflow.md).

## A real project built this way: flyfun-weather

[**flyfun-weather**](https://github.com/roznet/flyfun-weather) is an aviation weather briefing tool (Python backend, web app and iOS app) where almost all of the code was written by Claude Code using this approach. It is public, so you can see the whole setup working rather than a sample:

- [`designs/`](https://github.com/roznet/flyfun-weather/tree/main/designs): more than 50 design docs with an `INDEX.md`, plus the `future/`, `plans/`, `archive/` and `references/` lifecycle folders.
- [`.claude/`](https://github.com/roznet/flyfun-weather/tree/main/.claude): the project `CLAUDE.md`, the skills (`implement-issue`, `land-pr`, `worktree-init`, `deploy`, …), and the review commands.
- [`.github/workflows/claude-code-review.yml`](https://github.com/roznet/flyfun-weather/blob/main/.github/workflows/claude-code-review.yml): the review bot.
- [**`HOW_TO.md`**](https://github.com/roznet/flyfun-weather/blob/main/HOW_TO.md): a detailed explanation of the workflow used to build the tool. It covers how design docs, issues, `/implement-issue`, the Owner's brief, review and landing, worktrees, memory and skills fit together, and ends with an [adoption checklist](https://github.com/roznet/flyfun-weather/blob/main/HOW_TO.md#adopting-this-in-your-own-project). This README covers the generic pieces. `HOW_TO.md` shows them in a real project, with its project-specific details left in.

---

## The idea in one paragraph

Claude is a strong coder, but every session starts with no memory. If it has to rediscover your architecture by grepping, it wastes context and often gets the intent wrong. So each repo keeps a `designs/` folder of short notes for a future Claude: intent, architecture, key choices and *why*, patterns, and gotchas. `INDEX.md` is the map. This MCP server serves those notes on demand, across all your repos. A one-line rule in `CLAUDE.md` makes Claude read them before it touches code. The `/sync-designs` skill keeps them true as the code changes. Once that foundation is in place, Claude can take a GitHub issue and produce a PR that fits the project, even unattended. Most of the rest of the workflow is skills that turn the prompts I kept repeating into one command.

## The workflow as it actually runs

These are real patterns from a month of sessions on one project (about 125 sessions, about 35 PRs, many sessions running in parallel):

```
 brainstorm ──► design doc ──► GitHub issue ──► /implement-issue ──► review bot ──► /land-pr ──► /deploy
 (local chat)   designs/future/  (gh issue       (often cloud/phone,   (GitHub Action  (merge, fix    (separate,
                committed to     create, refs    unattended; ends      on every push)  leftovers      confirmed
                main             the doc)        with owner's brief)                   on main)       step)
```

1. **Brainstorm locally.** For example: *"i want to do a brainstorm about X — you should also come up with your own ideas"*. Then decide in short numbered answers, like *"1. context-sensitive 2. yes 3. delay to v2"*.
2. **Save the thinking.** *"Save the brainstorm into a designs/future document, commit it to main, then create the issue referring to it."* Later decisions go into issue comments, and the project `CLAUDE.md` tells Claude to read `gh issue view <n> --comments`, not just the body.
3. **Implement with [`/implement-issue <n>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/implement-issue/SKILL.md).** This usually runs in Claude Code on the web, started from my phone. The skill reads the thread and the design docs, works on a branch or worktree, runs the tests this machine can run, updates the design docs it touched, and opens a PR. It ends with an **Owner's brief**: what changes for the user, the decisions it made for me, how it could go wrong, what was and wasn't verified, and the questions worth asking. I don't review every line, so this brief is how I own what ships.
4. **Automatic review.** A [GitHub Action](https://github.com/roznet/flyfun-weather/blob/main/.github/workflows/claude-code-review.yml) runs [`/code-review`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/code-review.md) on every push and posts one comment with Critical, Important and Minor sections. The format is fixed so other skills can read it. [`/process-review`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/process-review.md) triages it. Each push costs a full review round, so only real blockers get pushed.
5. **Land with [`/land-pr <n>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/land-pr/SKILL.md).** It checks CI and every review round, runs locally what the cloud couldn't (for example iOS builds and UI tests), does a rebase-merge, and then **fixes remaining findings directly on main** instead of starting another PR round. It finishes with a short landing summary and a list of what deploy will need.
6. **Deploy as its own step.** `/deploy` runs pre-flight checks, then stops for an explicit "yes" in a separate turn. That gate was added after a deploy was reported as done but never actually happened.

Supporting habits:

- **One task per session.** I use `/clear` far more than `/compact`. Fresh context plus design docs is cheaper and more accurate than one long conversation.
- **Worktree per issue, run in parallel.** [`/worktree-init <branch>`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/worktree-init/SKILL.md) creates a sibling checkout (`../issue-451`) with its own venv and `.env`. A per-worktree dev server runs on its own port, so several sessions never collide.
- **Remote Control from the phone.** Local sessions are bridged to claude.ai so I can approve, steer or say *"go ahead"* from anywhere. About a fifth of my prompts are one-word approvals.
- **Auto mode plus approval hooks.** Safe commands are auto-approved by a `PreToolUse` hook, so parallel sessions rarely block on permission prompts.
- **Skills come from repeated prompts.** When I notice I keep typing the same instructions (*"it feels like I always do the similar prompt"*), I ask Claude to turn them into a skill, try it on two or three real PRs, and refine it. `land-pr` was created this way.
- **Periodic "review my usage" sessions.** I ask Claude to read my recent session transcripts and suggest process changes. Several of the skills above came out of those sessions.
- **Few subagents.** I use them for parallel reviews of big PRs and for audits, not by default. Design docs already provide the context that subagents would otherwise be spawned to gather.

---

## Adopting this workflow (guide for Claude)

*This section is written for Claude Code, running in the user's environment, to help the user adopt this workflow. Go in stages. Each stage is useful on its own, so stop wherever the user wants. Before each stage, look at what already exists (`~/.claude/`, the repo's `.claude/`, `CLAUDE.md`, `designs/`, `.github/workflows/`) and change only what is missing. Ask before writing files outside the current repo.*

### Stage 1: Install the MCP server (user-wide)

```bash
pip install mcp-library-docs          # or: pipx install mcp-library-docs
claude mcp add --scope user library-docs -- python -m mcp_library_docs
```

`--scope user` makes the server available in every project. Use the Python interpreter where the package was installed; with pipx or a venv, put its absolute path in place of `python`. Check the install by restarting Claude Code and running `/mcp`: `library-docs` should be listed with tools `list_libraries`, `get_design_doc` and `get_index_status`.

### Stage 2: Install the design-doc skills (user-wide)

This repo ships two generic skills that write `designs/` in exactly the format this server reads:

- [`sync-designs`](.claude/skills/sync-designs/SKILL.md): create a design doc from code, or sync one doc (or all docs) with the code. This is the everyday one.
- [`sync-all-designs`](.claude/skills/sync-all-designs/SKILL.md): an occasional full consistency check. It fans out one subagent per doc through a resumable Workflow script bundled with the skill, then reconciles `INDEX.md` and proposes structural clean-ups (archive stale plans, promote built `future/` docs, flag orphans). It uses a lot of tokens, so it only runs when typed.

Install them at user level so they work in every project:

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/sync-designs .claude/skills/sync-all-designs ~/.claude/skills/   # from a clone of this repo
```

Copy rather than symlink if the user will customise them. The repo versions are kept generic on purpose, and a personal copy can then add machine- or project-specific details. Use a symlink instead to pick up updates on `git pull`.

### Stage 3: Tell Claude to use the docs (global `CLAUDE.md`)

Add this to `~/.claude/CLAUDE.md`, or to a project's `CLAUDE.md`. Without it, Claude often skips the docs and greps instead.

```markdown
## Always start here

Design docs give you architecture, key exports, and non-obvious decisions faster than grepping.
For any task that touches code (features, bug fixes, "how does X work", refactors), BEFORE reading or grepping:

1. Call the `mcp__library-docs__list_libraries` MCP tool (or read `designs/INDEX.md` if the server is
   unavailable). It is an MCP tool, not a skill — do not invoke it via `Skill`.
2. If a relevant module appears, call `mcp__library-docs__get_design_doc`.
3. Only then explore with Grep/Read.

For `[library]` entries: import and reuse. For `[project]` entries: follow the patterns.
Skip this only for trivial edits.
```

### Stage 4: Bootstrap design docs for a repo

In the target repo, run `/sync-designs <code path>` once for each major component, for example `/sync-designs src/api/`. This creates `designs/<component>.md` and an `INDEX.md` entry for each. Then:

- Review the docs with the user. The *Key Choices* and *Gotchas* sections are the most valuable parts, and the code alone can't supply them, so ask the user what Claude got wrong or missed.
- Keep each doc under about 300 lines. Split big components into several docs.
- Optional subfolders that work well: `designs/future/` (brainstorms and plans not yet built), `designs/plans/`, `designs/archive/` (superseded designs, kept for history), and `designs/references/` (runbook data that skills cite). Only docs linked from `INDEX.md` with `→ Full doc: name.md` are served by the MCP server.
- To check the index, run `get_index_status` or `/sync-designs` with no arguments.

If the user has shared libraries or related repos, register them in `~/.config/mcp-library-docs/config.yaml` (see [Configuration](#configuration)). Use `type: library` for code to import, and `projects:` with `related:` for repos that share an API contract.

### Stage 5: Keep docs in sync as part of the work

Docs only help while they're true. The rule that works: **the PR that changes behaviour updates the design doc for the code it touched**, in the same PR, scoped to that code. Running `/sync-designs <doc>` before opening a PR does it. A full audit (`/sync-designs` with no arguments, or `/sync-all-designs` on a large `designs/` folder) is for occasional use.

### Stage 6: The issue → PR → land loop (adapt, don't copy)

These skills are project-specific. Read [flyfun-weather's `HOW_TO.md`](https://github.com/roznet/flyfun-weather/blob/main/HOW_TO.md#how-we-work) first for how they fit together, then copy the *shape* and rewrite the details (test commands, toolchains, deploy targets) for the user's project. The reference versions are in [flyfun-weather/.claude](https://github.com/roznet/flyfun-weather/tree/main/.claude):

| Piece | Reference | What to keep when adapting |
|---|---|---|
| Implement an issue | [`skills/implement-issue`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/implement-issue/SKILL.md) | Read the whole issue thread and the design docs first. Detect cloud vs local and attended vs unattended. Classify the risk. Update the docs it touched. End with an **Owner's brief** stating what was verified and what was only claimed. |
| Review bot | [`.github/workflows/claude-code-review.yml`](https://github.com/roznet/flyfun-weather/blob/main/.github/workflows/claude-code-review.yml) + [`commands/code-review.md`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/code-review.md) | One complete pass with every finding. A fixed, machine-readable comment format. Always post before finishing. Set it up with `/install-github-app`. |
| Triage the review | [`commands/process-review.md`](https://github.com/roznet/flyfun-weather/blob/main/.claude/commands/process-review.md) | Strict definition of a blocker. Push only for blockers, and batch everything else into that push. Never auto-merge. Cap at 2 review rounds. |
| Land a PR | [`skills/land-pr`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/land-pr/SKILL.md) | The user has already decided to merge. Pause only for things that can't be fixed after merging. Finish the remaining findings on main. Never deploy. |
| Parallel worktrees | [`skills/worktree-init`](https://github.com/roznet/flyfun-weather/blob/main/.claude/skills/worktree-init/SKILL.md) | A sibling worktree per issue with its own environment, and a separate dev-server port for each. |
| Project rules | [`.claude/CLAUDE.md`](https://github.com/roznet/flyfun-weather/blob/main/.claude/CLAUDE.md) | "Always start here", the "read this doc before writing X" pointers, and "read issue comments, not just the body". |

Good order to adopt them: CLAUDE.md rules → review bot → `implement-issue` → `land-pr`. Mark skills that act on the outside world (merge, deploy, release) with `disable-model-invocation: true` so they run only when the user types them.

### Stage 7: Build the user's own skills

Don't install every skill above up front. Tell the user: *when you notice you've typed the same multi-step instructions three times, ask Claude to turn that conversation into a skill, then try it on a few real cases and refine it.* The skills that last are the ones that grew out of real repetition.

---

## Reference: the MCP server

### How it works

When Claude calls `list_libraries`, the server:

1. **Auto-discovers the current project.** It walks up from Claude's working directory to the nearest `designs/INDEX.md`. No config is needed for this.
2. **Loads registered libraries and projects** from `config.yaml`.
3. **Returns a combined index**, with each entry tagged `[current project]`, `[library]` (import and reuse) or `[project]` (follow its patterns, don't import from it).

Claude then calls `get_design_doc(library, topic)` to load only the docs the task needs.

### Minimal `designs/INDEX.md`

```markdown
# my-project

> Brief description of what this project provides

## Modules

### api
REST API client and authentication.
Key exports: `ApiClient`, `authenticate`
→ Full doc: api.md
```

Each entry needs a `→ Full doc: name.md` line (Markdown links `[text](name.md)` also work). Keep descriptions to 1–2 sentences, list the main exports, and put the most-used modules first.

### Topic doc template

```markdown
# Feature Name
> One-line summary

## Intent          — why it exists; what must NOT change
## Architecture    — key components, where things live
## Usage Examples  — 2–3 idiomatic snippets, not the full API
## Key Choices     — decisions and WHY, so they aren't redone or contradicted
## Patterns        — conventions for extending it
## Gotchas         — non-obvious traps
## References      — related docs, key code paths
```

Write the "why" and leave out the "what". Claude can read the code for implementation details, but it can't infer intent or rejected alternatives.

### MCP tools

| Tool | Parameters | Purpose |
|---|---|---|
| `list_libraries` | `cwd` | All INDEX.md contents (current project + configured), type-tagged |
| `get_design_doc` | `library`, `topic` | Full content of one doc (`topic` = filename without `.md`) |
| `get_index_status` | `cwd` | Docs missing from INDEX.md and stale INDEX entries |

There is also an MCP prompt, `update_index`, with formatting guidance for INDEX.md entries.

### Configuration

Configuration is optional. Without it, the server only discovers the current project.

**Location:** `~/.config/mcp-library-docs/config.yaml` on Linux and macOS (macOS also falls back to `~/Library/Application Support/mcp-library-docs/`). On Windows it is `%APPDATA%\mcp-library-docs\`. To use another location, set `MCP_LIBRARY_DOCS_CONFIG_DIR` or pass `--config PATH`.

```yaml
defaults:                     # all optional
  designs_dir: designs
  index_file: INDEX.md
  cache: dynamic              # "static" = read once, "dynamic" = re-read each call

libraries:                    # shared code Claude should import from
  lib-utils:
    path: ~/projects/lib-utils
    type: library             # "library" (import) or "project" (patterns only)

  legacy-lib:
    path: ~/projects/legacy-lib
    designs_dir: docs/design  # per-library overrides
    index_file: README.md
    cache: static

projects:                     # apps to learn patterns from; `related` links API partners
  my-app:
    path: ~/projects/my-app
    related: [my-app-server]
  my-app-server:
    path: ~/projects/my-app-server
    related: [my-app]
```

| Option | Default | Description |
|---|---|---|
| `path` | required | Repo root (`~` expanded) |
| `type` | `library` | `library` or `project` |
| `designs_dir` | `designs` | Folder holding the docs |
| `index_file` | `INDEX.md` | Index file name |
| `cache` | `dynamic` | `static` or `dynamic` |
| `related` | — | Other entries Claude should also consult (shown as `Related:` in the index) |

### Other clients

The server works with any MCP client. For Cursor (`.cursor/mcp.json`), or for a manual project `.mcp.json`:

```json
{
  "mcpServers": {
    "library-docs": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_library_docs"]
    }
  }
}
```

### CLI

```bash
python -m mcp_library_docs [--debug] [--config PATH]
```

For the server's own design, see [designs/mcp-library-docs-design.md](designs/mcp-library-docs-design.md).
