# mcp-library-docs

An MCP server that gives Claude access to design documentation across multiple code libraries/repositories. This enables Claude to discover existing utilities, patterns, and conventions - preventing reimplementation of existing functionality.

For tips on how I use this server as part of a broader AI-assisted development workflow, see [AI Dev Workflow Tips](ai-dev-workflow.md).

## Installation

```bash
pip install mcp-library-docs
```

## Quick Start

**Zero config required** - just create a `designs/INDEX.md` in your project and the server will auto-discover it.

1. Create `designs/INDEX.md` in your project:

```markdown
# my-project

> Brief description of what this project provides

## Modules

### utils
Helper utilities for common operations.
Key exports: `retry`, `parse_date`, `format_currency`
→ Full doc: utils.md

### api
REST API client and authentication.
Key exports: `ApiClient`, `authenticate`
→ Full doc: api.md
```

2. Add the MCP server to your AI coding assistant (see [Setup](#setup) below)

3. Claude will now discover your project's design docs when working in that directory.

## Setup

### Claude Code

Add the server using the CLI:

```bash
claude mcp add library-docs -- python -m mcp_library_docs
```

Or manually add to your MCP config (`~/.claude/settings.json` or project `.mcp.json`):

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

### Cursor

Add to your Cursor MCP settings (`.cursor/mcp.json` in your project or global config):

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

Or use an absolute path to the Python interpreter if needed:

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

## How It Works

When Claude calls `list_libraries`, the server:

1. **Auto-discovers current project**: Walks up from Claude's working directory to find the nearest `designs/INDEX.md`
2. **Loads external libraries**: Reads any libraries configured in `config.yaml` (see [Config File Location](#config-file-location))
3. **Returns combined index**: All INDEX.md contents with type tags (`[current project]`, `[library]`, `[project]`)

Claude can then call `get_design_doc(library, topic)` to read detailed documentation.

## Configuration

Configuration is **optional**. Without it, the server just discovers the current project.

### Config File Location

The server searches for `config.yaml` in platform-specific locations:

| Platform | Primary Location | Fallback |
|----------|-----------------|----------|
| Linux | `~/.config/mcp-library-docs/` | - |
| macOS | `~/.config/mcp-library-docs/` | `~/Library/Application Support/mcp-library-docs/` |
| Windows | `%APPDATA%\mcp-library-docs\` | `~/.config/mcp-library-docs/` |

The first existing directory is used. If none exist, the primary location is used.

**Environment variable override:** Set `MCP_LIBRARY_DOCS_CONFIG_DIR` to use a custom location:

```bash
export MCP_LIBRARY_DOCS_CONFIG_DIR=/custom/path
```

### Config File Format

Create `config.yaml` in the config directory to register external libraries:

```yaml
# Global defaults (all optional)
defaults:
  designs_dir: designs      # Directory name to look for (default: designs)
  index_file: INDEX.md      # Index file name (default: INDEX.md)
  cache: dynamic            # "static" or "dynamic" (default: dynamic)

# External libraries
libraries:
  # A shared utility library - Claude should import from this
  lib-utils:
    path: ~/projects/lib-utils
    type: library           # "library" = Claude can import from this

  # Another project for reference - Claude should learn patterns, not import
  other-app:
    path: ~/projects/other-app
    type: project           # "project" = inspiration/patterns only

  # Library with custom doc location
  legacy-lib:
    path: ~/projects/legacy-lib
    designs_dir: docs/design    # Override designs directory
    index_file: README.md       # Override index file name
    cache: static               # Cache on startup, don't re-read
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `path` | required | Path to library root (~ is expanded) |
| `type` | `library` | `library` (import from) or `project` (patterns only) |
| `designs_dir` | `designs` | Directory containing design docs |
| `index_file` | `INDEX.md` | Name of the index file |
| `cache` | `dynamic` | `static` (read once) or `dynamic` (read each time) |

### Library Types

The type affects how Claude interprets the documentation:

- **`library`** → `[library]` tag → "I can/should import and reuse this code"
- **`project`** → `[project]` tag → "Learn patterns, but don't import from here"
- Current project → `[current project]` tag → "I'm working here, prioritize this"

## MCP Tools

### `list_libraries`

Returns all INDEX.md contents from discovered and configured libraries.

**Parameters:**
- `cwd` (string, required): Current working directory

**Example response:**
```markdown
# my-app [current project]
> Main application

## Modules
### api
REST endpoints...
→ Full doc: api.md

---

# lib-utils [library]
> Shared utilities

## Modules
### dates
Date parsing utilities...
→ Full doc: dates.md
```

### `get_design_doc`

Returns the full content of a specific design document.

**Parameters:**
- `library` (string, required): Library name from `list_libraries` response
- `topic` (string, required): Document name without `.md` extension

**Example:** `get_design_doc(library="lib-utils", topic="dates")`

### `get_index_status`

Returns the status of INDEX.md compared to actual files in designs/.

**Parameters:**
- `cwd` (string, required): Current working directory

**Returns:** Shows which docs need adding to INDEX.md and which entries are stale.

**Example:** Use this before updating INDEX.md to see what needs attention.

## MCP Prompts

### `update_index`

Provides guidelines for updating INDEX.md files. Includes:
- Recommended format for entries
- Best practices (concise descriptions, key exports)
- Examples

**Workflow for updating INDEX.md:**
1. Call `get_index_status(cwd)` to see what needs updating
2. Get the `update_index` prompt for formatting guidance
3. Read any new .md files to understand them
4. Update INDEX.md with properly formatted entries

## Writing Good Design Docs

### INDEX.md Structure

```markdown
# {Library Name}

> One-line description

Install: `pip install {package}` or `import from {path}`

## Modules

### {module_name}
Brief description of what this module does.
Key exports: `export1`, `export2`, `export3`
→ Full doc: {module_name}.md
```

### Topic Doc Structure

```markdown
# {Module Name}

> One-line purpose

## When to use this
- Use case 1
- Use case 2
- **Don't use for**: [common mistakes]

## Key exports

### `function_name(param: Type) -> ReturnType`
What this function does.

\```python
result = function_name(value)
\```

## Patterns and conventions
[How to use this module correctly]
```

## CLI Options

```bash
python -m mcp_library_docs [--debug] [--config PATH]
```

- `--debug`: Enable debug logging to stderr
- `--config PATH`: Use custom config file path

## Full Documentation

See [designs/mcp-library-docs-design.md](designs/mcp-library-docs-design.md) for complete design documentation.
