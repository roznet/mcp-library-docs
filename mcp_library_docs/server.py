"""MCP server implementation."""

import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, PromptMessage, TextContent, Tool

from .cache import cache
from .config import Config, load_config
from .discovery import (
    find_current_project,
    get_index_status,
    get_project_name,
    list_topic_docs,
    read_index,
    read_topic_doc,
)

logger = logging.getLogger("mcp-library-docs")

# Create server instance
server = Server("mcp-library-docs")

# Store config globally for handlers
_config: Config | None = None

# Store current project info from last list_libraries call
# This allows get_design_doc to access current project without needing cwd
_current_project_path: Path | None = None
_current_project_name: str | None = None


def _format_library_entry(
    name: str,
    content: str,
    lib_type: str,
    related: list[str] | None = None,
) -> str:
    """Format a library entry for the response."""
    header = f"# {name} [{lib_type}]"
    if related:
        header += f"\nRelated: {', '.join(related)}"
    return f"{header}\n{content}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="list_libraries",
            description=(
                "Returns INDEX.md contents from the current project and all registered "
                "libraries. Call this at the start of a task to discover existing utilities "
                "and avoid reimplementing functionality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cwd": {
                        "type": "string",
                        "description": "Current working directory of the Claude session",
                    },
                },
                "required": ["cwd"],
            },
        ),
        Tool(
            name="get_design_doc",
            description=(
                "Returns the full content of a specific design document. Call this when "
                "you need implementation details for functionality discovered via list_libraries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "library": {
                        "type": "string",
                        "description": "Library name as shown in list_libraries response",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Topic/document name without .md extension",
                    },
                },
                "required": ["library", "topic"],
            },
        ),
        Tool(
            name="get_index_status",
            description=(
                "Returns the status of INDEX.md compared to actual design doc files. "
                "Shows which docs are missing from INDEX.md and which INDEX entries are stale. "
                "Use this before updating INDEX.md to see what needs to be added or removed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cwd": {
                        "type": "string",
                        "description": "Current working directory of the Claude session",
                    },
                },
                "required": ["cwd"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "list_libraries":
        return await _handle_list_libraries(arguments)
    elif name == "get_design_doc":
        return await _handle_get_design_doc(arguments)
    elif name == "get_index_status":
        return await _handle_get_index_status(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_list_libraries(arguments: dict) -> list[TextContent]:
    """Handle list_libraries tool call."""
    global _config, _current_project_path, _current_project_name

    cwd = arguments.get("cwd", ".")
    results: list[str] = []

    # 1. Find and read current project (always fresh)
    current_project = find_current_project(
        cwd,
        _config.designs_dir if _config else "designs",
        _config.index_file if _config else "INDEX.md",
    )

    # Store current project info for get_design_doc
    _current_project_path = current_project
    _current_project_name = get_project_name(current_project) if current_project else None

    if current_project and _current_project_name:
        content = read_index(
            current_project,
            _config.designs_dir if _config else "designs",
            _config.index_file if _config else "INDEX.md",
        )
        if content:
            results.append(_format_library_entry(
                _current_project_name,
                content,
                "current project",
            ))
            logger.debug(f"Found current project: {_current_project_name}")

    # 2. Read external libraries (cached or fresh per config)
    if _config:
        for name, lib_config in _config.libraries.items():
            # Skip if this is the same as current project
            if current_project and lib_config.path == current_project:
                continue

            content = cache.get_index(name)
            if content:
                results.append(_format_library_entry(
                    name, content, lib_config.type, lib_config.related
                ))
            else:
                related_str = f"\nRelated: {', '.join(lib_config.related)}" if lib_config.related else ""
                results.append(f"# {name} [{lib_config.type}]{related_str}\n> No INDEX.md found")

    if not results:
        return [TextContent(
            type="text",
            text=(
                "No design documentation found.\n\n"
                "To get started:\n"
                "1. Create a `designs/INDEX.md` file in your project\n"
                "2. Optionally configure external libraries in "
                "~/.config/mcp-library-docs/config.yaml"
            ),
        )]

    return [TextContent(type="text", text="\n\n---\n\n".join(results))]


async def _handle_get_design_doc(arguments: dict) -> list[TextContent]:
    """Handle get_design_doc tool call."""
    global _config, _current_project_path, _current_project_name

    library = arguments.get("library", "")
    topic = arguments.get("topic", "")

    if not library or not topic:
        return [TextContent(
            type="text",
            text="Error: Both 'library' and 'topic' parameters are required.",
        )]

    designs_dir = _config.designs_dir if _config else "designs"

    # Check if it's the current project
    if _current_project_path and library == _current_project_name:
        content = read_topic_doc(_current_project_path, topic, designs_dir)

        if content:
            return [TextContent(type="text", text=content)]

        # Topic not found - list available topics
        available = list_topic_docs(_current_project_path, designs_dir)
        if available:
            return [TextContent(
                type="text",
                text=f"Topic '{topic}' not found in '{library}'.\n\nAvailable topics: {', '.join(available)}",
            )]
        return [TextContent(
            type="text",
            text=f"No topic documents found in '{library}'.",
        )]

    # Check if it's an external library from config
    if _config and library in _config.libraries:
        lib_config = _config.libraries[library]
        content = read_topic_doc(lib_config.path, topic, lib_config.designs_dir)

        if content:
            return [TextContent(type="text", text=content)]

        # Topic not found - list available topics
        available = list_topic_docs(lib_config.path, lib_config.designs_dir)
        if available:
            return [TextContent(
                type="text",
                text=f"Topic '{topic}' not found in '{library}'.\n\nAvailable topics: {', '.join(available)}",
            )]
        return [TextContent(
            type="text",
            text=f"No topic documents found in '{library}'.",
        )]

    # Not found anywhere
    return [TextContent(
        type="text",
        text=(
            f"Library '{library}' not found.\n\n"
            "Make sure to call list_libraries first to discover available libraries, "
            "then use the library name exactly as shown in the response."
        ),
    )]


async def _handle_get_index_status(arguments: dict) -> list[TextContent]:
    """Handle get_index_status tool call."""
    global _config

    cwd = arguments.get("cwd", ".")
    designs_dir = _config.designs_dir if _config else "designs"
    index_file = _config.index_file if _config else "INDEX.md"

    # Find current project
    project_path = find_current_project(cwd, designs_dir, index_file)

    if not project_path:
        return [TextContent(
            type="text",
            text=(
                "No project with designs/ directory found.\n\n"
                "Create a `designs/INDEX.md` file in your project to get started."
            ),
        )]

    status = get_index_status(project_path, designs_dir, index_file)
    project_name = get_project_name(project_path)

    # Format the response
    lines = [f"# Index Status for {project_name}\n"]

    # Current INDEX.md content
    if status["index_content"]:
        lines.append("## Current INDEX.md\n")
        lines.append("```markdown")
        lines.append(status["index_content"].strip())
        lines.append("```\n")
    else:
        lines.append("## Current INDEX.md\n")
        lines.append("*No INDEX.md found*\n")

    # Design docs in directory
    lines.append("## Design docs in designs/\n")
    if status["existing_docs"]:
        for doc in status["existing_docs"]:
            if doc in status["missing_from_index"]:
                lines.append(f"- **{doc}.md** ← NEW (not in INDEX)")
            else:
                lines.append(f"- {doc}.md")
    else:
        lines.append("*No design docs found*")
    lines.append("")

    # Stale entries
    if status["stale_in_index"]:
        lines.append("## Stale entries in INDEX (no file exists)\n")
        for doc in status["stale_in_index"]:
            lines.append(f"- {doc}.md ← consider removing")
        lines.append("")

    # Summary
    if status["missing_from_index"] or status["stale_in_index"]:
        lines.append("## Summary\n")
        if status["missing_from_index"]:
            lines.append(f"- **{len(status['missing_from_index'])} doc(s) need adding** to INDEX.md")
        if status["stale_in_index"]:
            lines.append(f"- **{len(status['stale_in_index'])} stale entry(ies)** should be removed from INDEX.md")
    else:
        lines.append("## Summary\n")
        lines.append("INDEX.md is up to date!")

    return [TextContent(type="text", text="\n".join(lines))]


# ============================================================================
# Prompts
# ============================================================================

UPDATE_INDEX_PROMPT = """\
You are updating the INDEX.md file for a project's design documentation.

## Guidelines for INDEX.md entries

Each module/topic entry should follow this format:

```markdown
### {module_name}
Brief description of what this module does (1-2 sentences).
Key exports: `export1`, `export2`, `export3`
→ Full doc: {module_name}.md
```

## Best practices

1. **Keep descriptions concise** - 1-2 sentences max
2. **List key exports** - the main functions/classes users will import
3. **Order by importance** - most commonly used modules first
4. **Use consistent formatting** - follow the pattern above
5. **Include the arrow link** - `→ Full doc: name.md` helps discovery

## When adding new entries

1. Read the new .md file to understand what the module does
2. Identify the key exports (functions, classes, constants)
3. Write a brief description focused on the use case, not implementation
4. Add the entry in an appropriate location (group related modules)

## When removing stale entries

Simply delete the entire section for modules that no longer exist.

## Example entry

```markdown
### retry
Exponential backoff and circuit breaker patterns for resilient operations.
Key exports: `with_retry`, `CircuitBreaker`, `RetryConfig`
→ Full doc: retry.md
```
"""


@server.list_prompts()
async def list_prompts():
    """List available prompts."""
    from mcp.types import Prompt

    return [
        Prompt(
            name="update_index",
            description=(
                "Guidelines and template for updating INDEX.md. "
                "Use this when you need to add new modules or clean up stale entries."
            ),
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    """Get a specific prompt."""
    if name == "update_index":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=UPDATE_INDEX_PROMPT),
                )
            ]
        )

    raise ValueError(f"Unknown prompt: {name}")


async def run_server(config_path: Path | None = None) -> None:
    """Run the MCP server."""
    global _config

    # Load config
    _config = load_config(config_path)

    # Initialize cache
    cache.initialize(_config)

    logger.info("Starting mcp-library-docs server")

    # Run with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
