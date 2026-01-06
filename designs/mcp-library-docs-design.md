# MCP Server: Library Design Docs

## Purpose

An MCP server that gives Claude access to design documentation across multiple code libraries/repositories. This enables Claude sessions working in one repo to discover and understand utilities, patterns, and conventions from other repos in the ecosystem - preventing reimplementation of existing functionality.

## Problem being solved

When working across multiple libraries and projects:
- Claude doesn't know what utilities exist in other repos
- Developer has to manually remind Claude about existing code
- Logic gets reimplemented instead of reused
- Context about architectural decisions lives in developer's head

## Design philosophy

- **Human-maintained docs, AI-consumed** - Design docs are written/updated by Claude but reviewed by human
- **Lightweight discovery, detailed on demand** - INDEX files are always small; full docs loaded selectively
- **Explicit over magic** - No embedding/RAG; simple file structure the developer controls
- **Zero config to start** - Works immediately by walking up from cwd; config only needed for external libraries

## Architecture

### Discovery model

```
┌─────────────────────────────────────────────────────────────┐
│                    list_libraries(cwd)                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│     Current Project      │    │    External Libraries    │
│  (auto-discovered)       │    │    (from config)         │
├──────────────────────────┤    ├──────────────────────────┤
│ • Walk up from cwd       │    │ • Registered in config   │
│ • Stop at $HOME or /     │    │ • Type: library/project  │
│ • Take nearest designs/  │    │ • Caching: configurable  │
│ • Always read fresh      │    │ • Default: cached        │
│ • Not in config          │    │                          │
└──────────────────────────┘    └──────────────────────────┘
```

### Directory structure

```
# Current project (auto-discovered from cwd)
{project_path}/
  designs/              # Or configured name
    INDEX.md            # Or configured name
    {topic}.md

# Config location (optional, platform-specific)
# Linux/macOS: ~/.config/mcp-library-docs/config.yaml
# macOS fallback: ~/Library/Application Support/mcp-library-docs/config.yaml
# Windows: %APPDATA%\mcp-library-docs\config.yaml
# Override: MCP_LIBRARY_DOCS_CONFIG_DIR env var

# External libraries (from config)
{library_path}/
  designs/
    INDEX.md
    {topic}.md
```

### CWD discovery algorithm

```python
def find_current_project(cwd: Path, designs_dir: str = "designs") -> Path | None:
    """Walk up from cwd to find nearest designs/ directory."""
    current = cwd
    home = Path.home()

    while current != current.parent:  # Stop at filesystem root
        designs_path = current / designs_dir
        if designs_path.is_dir():
            return current
        if current == home:  # Stop at $HOME
            break
        current = current.parent

    return None
```

### Library types

| Type | Tag in response | Claude's interpretation |
|------|-----------------|------------------------|
| Current project | `[current project]` | "I'm working here - prioritize this, check for changes" |
| `library` | `[library]` | "I can/should import and reuse this code" |
| `project` | `[project]` | "Learn patterns and conventions, but don't import" |

## MCP Tools

### 1. `list_libraries`

Returns all INDEX.md contents from current project and registered libraries.

**Parameters:**
- `cwd` (string, required): Current working directory of the Claude session

**Returns:** Concatenated INDEX.md contents with library names and type tags as headers

**When Claude should call this:** At the start of a task, before implementing new functionality

**Behavior:**
1. Walk up from `cwd` to find current project's designs/ directory
2. Read current project INDEX.md fresh (always dynamic)
3. Read external libraries from config (cached or dynamic per config)
4. Return concatenated results with type tags

**Example response:**
```markdown
# my-app [current project]
> Main application for user management

## Modules
### api
REST endpoints and authentication.
Key exports: `create_app`, `AuthMiddleware`
→ Full doc: api.md

### models
Database models and schemas.
Key exports: `User`, `Session`
→ Full doc: models.md

---

# lib-utils [library]
> General-purpose utilities for date handling, retries, and string manipulation.

## Modules
### dates
Date parsing, formatting, timezone handling.
Key exports: `parse_iso`, `format_relative`, `to_utc`
→ Full doc: dates.md

### retry
Exponential backoff and circuit breaker patterns.
Key exports: `with_retry`, `CircuitBreaker`
→ Full doc: retry.md

---

# other-app [project]
> Similar app for reference patterns

## Modules
### auth
OAuth2 implementation patterns.
→ Full doc: auth.md
```

### 2. `get_design_doc`

Returns full content of a specific design document.

**Parameters:**
- `library` (string, required): Library name as shown in `list_libraries` response
- `topic` (string, required): Document name without .md extension

**Returns:** Full markdown content of the design doc

**When Claude should call this:** When the INDEX summary indicates relevant functionality exists and Claude needs implementation details

**Example call:** `get_design_doc(library="lib-utils", topic="dates")`

**Note:** For current project, use the project directory name as the library parameter.

### 3. `get_index_status`

Returns the status of INDEX.md compared to actual design doc files in the designs/ directory.

**Parameters:**
- `cwd` (string, required): Current working directory of the Claude session

**Returns:** Status report showing:
- Current INDEX.md content
- List of design docs in the directory
- Which docs are missing from INDEX.md (need adding)
- Which INDEX.md entries are stale (file doesn't exist)

**When Claude should call this:** Before updating INDEX.md to see what needs to be added or removed.

**Example response:**
```markdown
# Index Status for my-app

## Current INDEX.md

```markdown
# my-app
...
```

## Design docs in designs/

- api.md
- utils.md
- **auth.md** ← NEW (not in INDEX)

## Stale entries in INDEX (no file exists)

- legacy.md ← consider removing

## Summary

- **1 doc(s) need adding** to INDEX.md
- **1 stale entry(ies)** should be removed from INDEX.md
```

## MCP Prompts

### `update_index`

Provides guidelines and templates for updating INDEX.md files.

**When to use:** When Claude needs to add new modules to INDEX.md or clean up stale entries.

**Content includes:**
- Recommended format for INDEX.md entries
- Best practices (concise descriptions, key exports, ordering)
- How to add new entries
- How to remove stale entries
- Example entries

**Workflow:**
1. Claude calls `get_index_status(cwd)` to see what needs updating
2. Claude gets the `update_index` prompt for formatting guidance
3. Claude reads any new .md files to understand them
4. Claude updates INDEX.md using the Edit tool

## Configuration

Configuration is optional. Without config, the server discovers the current project from cwd and works immediately.

### Config location

The server searches for `config.yaml` in platform-specific locations:

| Platform | Primary | Fallback |
|----------|---------|----------|
| Linux | `~/.config/mcp-library-docs/` | - |
| macOS | `~/.config/mcp-library-docs/` | `~/Library/Application Support/mcp-library-docs/` |
| Windows | `%APPDATA%\mcp-library-docs\` | `~/.config/mcp-library-docs/` |

The first existing directory is used. Override with `MCP_LIBRARY_DOCS_CONFIG_DIR` env var.

### Config schema

```yaml
# Global defaults (all optional)
defaults:
  designs_dir: designs      # Directory name to look for
  index_file: INDEX.md      # Index file name
  cache: dynamic            # Default cache strategy: "static" or "dynamic"

# External libraries (optional - current project is auto-discovered)
libraries:
  lib-utils:
    path: ~/projects/lib-utils
    type: library           # "library" (default) or "project"
    # Uses global defaults for designs_dir, index_file, cache

  legacy-app:
    path: ~/projects/legacy-app
    type: project           # Reference for patterns, not for importing
    designs_dir: docs/architecture  # Override default
    index_file: README.md           # Override default
    cache: static                   # Never re-read after startup

  active-lib:
    path: ~/projects/active-lib
    type: library
    cache: dynamic          # Always read fresh
```

### Config field reference

| Field | Location | Default | Description |
|-------|----------|---------|-------------|
| `defaults.designs_dir` | global | `designs` | Directory name containing design docs |
| `defaults.index_file` | global | `INDEX.md` | Index file name |
| `defaults.cache` | global | `dynamic` | Default caching strategy |
| `libraries.{name}.path` | per-library | required | Path to library root (~ expanded) |
| `libraries.{name}.type` | per-library | `library` | `library` or `project` |
| `libraries.{name}.designs_dir` | per-library | from defaults | Override designs directory name |
| `libraries.{name}.index_file` | per-library | from defaults | Override index file name |
| `libraries.{name}.cache` | per-library | from defaults | `static` or `dynamic` |

### Caching behavior

| Cache setting | Behavior |
|---------------|----------|
| `dynamic` | Read from disk on every `list_libraries` call |
| `static` | Read once on server startup, cached in memory |

**Note:** Current project (discovered from cwd) is always read dynamically, regardless of any config setting.

## INDEX.md Standard Structure

Each library's `designs/INDEX.md` should follow this format:

```markdown
# {Library Name}

> One-line description of library purpose

Install: `pip install {package}` or `import from {path}`

## Modules

### {module_name}
Brief description of what this module does.
Key exports: `export1`, `export2`, `export3`
→ Full doc: {module_name}.md

### {another_module}
...
```

## Detailed Design Doc Structure

Each `designs/{topic}.md` should follow:

```markdown
# {Module/Topic Name}

> One-line purpose

## When to use this
- Use case 1
- Use case 2
- **Don't use for**: [common mistake to avoid]

## Key exports

### `function_name(param: Type, param2: Type) -> ReturnType`
What this function does.

```python
# Example usage
result = function_name(foo, bar)
```

### `ClassName`
What this class is for.

## Patterns and conventions
[How to use this module correctly, common patterns]

## Dependencies
- External: `package1`, `package2`
- Internal: `lib-x.module_y`

## Last verified
{date} against commit {short_sha}
```

## Implementation

### Tech stack

- Python 3.10+
- `mcp` - Official MCP SDK (not fastmcp)
- `pyyaml` - Config parsing
- Standard library only otherwise

### Package structure

```
mcp_library_docs/
  __init__.py
  __main__.py       # Entry point: python -m mcp_library_docs
  server.py         # MCP server setup and tool handlers
  discovery.py      # CWD walking, project detection
  config.py         # Config loading and validation
  cache.py          # Caching logic for static libraries
```

### Error handling

| Scenario | Behavior |
|----------|----------|
| No config file | Works fine - just discovers current project from cwd |
| No current project found | Return only external libraries (or helpful message if none) |
| Missing library path | Skip with warning in logs, don't fail |
| Missing INDEX.md | Return message: "Library {name} has no INDEX.md" |
| Missing topic doc | Return available topics: "Topic not found. Available: x, y, z" |
| Invalid config YAML | Fail with clear parse error message |

### Logging

- Use stderr for all logging (MCP protocol uses stdout)
- Log levels: INFO for startup, DEBUG for per-request details
- Log format: `[mcp-library-docs] {level}: {message}`

### Transport

- Default: stdio (for local Claude Code usage)

## Usage with Claude

### MCP server config

Add to Claude Code MCP config (`~/.config/claude/claude_desktop_config.json` or project `.mcp.json`):

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

### CLAUDE.md instruction

Add to project CLAUDE.md files:

```markdown
## Before implementing new functionality

1. Call `list_libraries` to see what utilities exist across the codebase
2. If something looks relevant, call `get_design_doc` for implementation details
3. For [library] entries: import and reuse the code
4. For [project] entries: use as inspiration for patterns, don't import
```

## Future enhancements (not for v1)

- **`search_libraries(query)`** - Search across all docs
- **`verify_doc(library, topic)`** - Check if doc is stale vs recent commits
- **`update_doc_timestamp(library, topic, commit_sha)`** - Mark doc as verified
- **Watch mode** - Reload config on changes
- **Remote transport** - SSE/WebSocket for non-local usage

## Success criteria

1. Works with zero config - just create `designs/INDEX.md` in any project
2. Claude sessions can discover existing utilities without human prompting
3. No reimplementation of logic that exists in other libraries
4. Developer maintains docs as part of normal workflow (Claude helps)
5. Context loading is selective - doesn't bloat every session
6. Clear distinction between "reuse this code" vs "learn from this pattern"
