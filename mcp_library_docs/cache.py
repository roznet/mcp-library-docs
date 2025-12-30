"""Caching logic for library documentation."""

import logging
from dataclasses import dataclass, field

from .config import Config, LibraryConfig
from .discovery import read_index, read_topic_doc

logger = logging.getLogger("mcp-library-docs")


@dataclass
class LibraryCache:
    """Cache for library documentation."""

    # Cached index contents for static libraries (library_name -> content)
    _index_cache: dict[str, str] = field(default_factory=dict)

    # Config reference
    _config: Config | None = None

    def initialize(self, config: Config) -> None:
        """
        Initialize cache with config, loading static libraries.

        Args:
            config: Configuration object
        """
        self._config = config
        self._index_cache.clear()

        # Pre-load static libraries
        for name, lib_config in config.libraries.items():
            if lib_config.cache == "static":
                content = read_index(
                    lib_config.path,
                    lib_config.designs_dir,
                    lib_config.index_file,
                )
                if content:
                    self._index_cache[name] = content
                    logger.info(f"Cached index for '{name}'")
                else:
                    logger.warning(f"Could not read index for '{name}'")

    def get_index(self, library_name: str) -> str | None:
        """
        Get index content for a library.

        For static libraries, returns cached content.
        For dynamic libraries, reads fresh from disk.

        Args:
            library_name: Name of the library

        Returns:
            Index content or None if not found
        """
        if self._config is None:
            logger.error("Cache not initialized")
            return None

        lib_config = self._config.libraries.get(library_name)
        if lib_config is None:
            logger.warning(f"Library '{library_name}' not in config")
            return None

        # Return cached for static libraries
        if lib_config.cache == "static" and library_name in self._index_cache:
            return self._index_cache[library_name]

        # Read fresh for dynamic libraries
        return read_index(
            lib_config.path,
            lib_config.designs_dir,
            lib_config.index_file,
        )

    def get_topic_doc(self, library_name: str, topic: str) -> str | None:
        """
        Get topic document content.

        Always reads fresh (topic docs are not cached).

        Args:
            library_name: Name of the library
            topic: Topic name (without .md)

        Returns:
            Topic doc content or None if not found
        """
        if self._config is None:
            logger.error("Cache not initialized")
            return None

        lib_config = self._config.libraries.get(library_name)
        if lib_config is None:
            return None

        return read_topic_doc(lib_config.path, topic, lib_config.designs_dir)

    def get_library_config(self, library_name: str) -> LibraryConfig | None:
        """Get config for a library."""
        if self._config is None:
            return None
        return self._config.libraries.get(library_name)


# Global cache instance
cache = LibraryCache()
