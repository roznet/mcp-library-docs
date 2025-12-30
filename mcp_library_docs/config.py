"""Configuration loading and validation."""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

logger = logging.getLogger("mcp-library-docs")

# Default config location
CONFIG_DIR = Path.home() / ".config" / "mcp-library-docs"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Default values
DEFAULT_DESIGNS_DIR = "designs"
DEFAULT_INDEX_FILE = "INDEX.md"
DEFAULT_CACHE = "dynamic"
DEFAULT_TYPE = "library"


@dataclass
class LibraryConfig:
    """Configuration for a single library."""

    name: str
    path: Path
    type: Literal["library", "project"] = DEFAULT_TYPE
    designs_dir: str = DEFAULT_DESIGNS_DIR
    index_file: str = DEFAULT_INDEX_FILE
    cache: Literal["static", "dynamic"] = DEFAULT_CACHE


@dataclass
class Config:
    """Full configuration."""

    # Global defaults
    designs_dir: str = DEFAULT_DESIGNS_DIR
    index_file: str = DEFAULT_INDEX_FILE
    cache: Literal["static", "dynamic"] = DEFAULT_CACHE

    # External libraries
    libraries: dict[str, LibraryConfig] = field(default_factory=dict)


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file, or None for default location

    Returns:
        Config object with defaults applied
    """
    if config_path is None:
        config_path = CONFIG_FILE

    if not config_path.exists():
        logger.info(f"No config file at {config_path}, using defaults")
        return Config()

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in config file: {e}")
        sys.exit(1)

    if raw is None:
        return Config()

    # Parse defaults
    defaults = raw.get("defaults", {})
    config = Config(
        designs_dir=defaults.get("designs_dir", DEFAULT_DESIGNS_DIR),
        index_file=defaults.get("index_file", DEFAULT_INDEX_FILE),
        cache=defaults.get("cache", DEFAULT_CACHE),
    )

    # Parse libraries
    libraries_raw = raw.get("libraries", {})
    for name, lib_raw in libraries_raw.items():
        if not isinstance(lib_raw, dict):
            logger.warning(f"Invalid library config for '{name}', skipping")
            continue

        path_str = lib_raw.get("path")
        if not path_str:
            logger.warning(f"Library '{name}' has no path, skipping")
            continue

        # Expand ~ in path
        path = Path(path_str).expanduser().resolve()

        if not path.exists():
            logger.warning(f"Library '{name}' path does not exist: {path}, skipping")
            continue

        config.libraries[name] = LibraryConfig(
            name=name,
            path=path,
            type=lib_raw.get("type", DEFAULT_TYPE),
            designs_dir=lib_raw.get("designs_dir", config.designs_dir),
            index_file=lib_raw.get("index_file", config.index_file),
            cache=lib_raw.get("cache", config.cache),
        )

    logger.info(f"Loaded config with {len(config.libraries)} external libraries")
    return config
