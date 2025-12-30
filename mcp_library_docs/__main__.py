"""Entry point for mcp-library-docs server."""

import argparse
import asyncio
import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Configure logging to stderr."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "[mcp-library-docs] %(levelname)s: %(message)s"
    ))

    logger = logging.getLogger("mcp-library-docs")
    logger.setLevel(level)
    logger.addHandler(handler)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MCP server for library design documentation"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: ~/.config/mcp-library-docs/config.yaml)",
    )
    args = parser.parse_args()

    setup_logging(args.debug)

    from pathlib import Path

    from .server import run_server

    config_path = Path(args.config) if args.config else None

    asyncio.run(run_server(config_path))


if __name__ == "__main__":
    main()
