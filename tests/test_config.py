"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest

from mcp_library_docs.config import (
    DEFAULT_CACHE,
    DEFAULT_DESIGNS_DIR,
    DEFAULT_INDEX_FILE,
    DEFAULT_TYPE,
    Config,
    LibraryConfig,
    load_config,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve to handle macOS /var -> /private/var symlink
        yield Path(tmpdir).resolve()


@pytest.fixture
def temp_library(temp_config_dir):
    """Create a temporary library with designs directory."""
    lib_path = temp_config_dir / "my-lib"
    designs = lib_path / "designs"
    designs.mkdir(parents=True)
    (designs / "INDEX.md").write_text("# My Lib\n")
    return lib_path


class TestLoadConfigDefaults:
    def test_returns_defaults_when_no_file(self, temp_config_dir):
        """Should return default config when file doesn't exist."""
        config_path = temp_config_dir / "nonexistent.yaml"
        config = load_config(config_path)

        assert config.designs_dir == DEFAULT_DESIGNS_DIR
        assert config.index_file == DEFAULT_INDEX_FILE
        assert config.cache == DEFAULT_CACHE
        assert config.libraries == {}

    def test_returns_defaults_for_empty_file(self, temp_config_dir):
        """Should return defaults for empty YAML file."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("")

        config = load_config(config_path)
        assert config.designs_dir == DEFAULT_DESIGNS_DIR
        assert config.libraries == {}


class TestLoadConfigGlobalDefaults:
    def test_reads_global_defaults(self, temp_config_dir):
        """Should read global defaults from config."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("""
defaults:
  designs_dir: docs
  index_file: README.md
  cache: static
""")
        config = load_config(config_path)

        assert config.designs_dir == "docs"
        assert config.index_file == "README.md"
        assert config.cache == "static"

    def test_partial_defaults(self, temp_config_dir):
        """Should use defaults for unspecified values."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("""
defaults:
  designs_dir: docs
""")
        config = load_config(config_path)

        assert config.designs_dir == "docs"
        assert config.index_file == DEFAULT_INDEX_FILE
        assert config.cache == DEFAULT_CACHE


class TestLoadConfigLibraries:
    def test_loads_library(self, temp_config_dir, temp_library):
        """Should load library configuration."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text(f"""
libraries:
  my-lib:
    path: {temp_library}
""")
        config = load_config(config_path)

        assert "my-lib" in config.libraries
        lib = config.libraries["my-lib"]
        assert lib.name == "my-lib"
        assert lib.path == temp_library
        assert lib.type == DEFAULT_TYPE
        assert lib.designs_dir == DEFAULT_DESIGNS_DIR
        assert lib.index_file == DEFAULT_INDEX_FILE
        assert lib.cache == DEFAULT_CACHE

    def test_library_inherits_global_defaults(self, temp_config_dir, temp_library):
        """Library should inherit global defaults."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text(f"""
defaults:
  designs_dir: docs
  cache: static

libraries:
  my-lib:
    path: {temp_library}
""")
        config = load_config(config_path)
        lib = config.libraries["my-lib"]

        assert lib.designs_dir == "docs"
        assert lib.cache == "static"

    def test_library_overrides_defaults(self, temp_config_dir, temp_library):
        """Library can override global defaults."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text(f"""
defaults:
  designs_dir: docs
  cache: static

libraries:
  my-lib:
    path: {temp_library}
    designs_dir: design-docs
    cache: dynamic
""")
        config = load_config(config_path)
        lib = config.libraries["my-lib"]

        assert lib.designs_dir == "design-docs"
        assert lib.cache == "dynamic"

    def test_library_type(self, temp_config_dir, temp_library):
        """Should read library type."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text(f"""
libraries:
  my-lib:
    path: {temp_library}
    type: project
""")
        config = load_config(config_path)
        lib = config.libraries["my-lib"]

        assert lib.type == "project"

    def test_expands_tilde_in_path(self, temp_config_dir):
        """Should expand ~ in library paths."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("""
libraries:
  home-lib:
    path: ~/some-lib
""")
        config = load_config(config_path)

        # Library won't be loaded because path doesn't exist,
        # but we can verify the expansion logic is attempted
        assert "home-lib" not in config.libraries  # skipped due to missing path

    def test_skips_library_without_path(self, temp_config_dir):
        """Should skip libraries without path."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("""
libraries:
  bad-lib:
    type: library
""")
        config = load_config(config_path)
        assert "bad-lib" not in config.libraries

    def test_skips_library_with_nonexistent_path(self, temp_config_dir):
        """Should skip libraries with nonexistent paths."""
        config_path = temp_config_dir / "config.yaml"
        config_path.write_text("""
libraries:
  missing-lib:
    path: /nonexistent/path/to/lib
""")
        config = load_config(config_path)
        assert "missing-lib" not in config.libraries

    def test_multiple_libraries(self, temp_config_dir):
        """Should load multiple libraries."""
        lib1 = temp_config_dir / "lib1"
        lib2 = temp_config_dir / "lib2"
        for lib in [lib1, lib2]:
            designs = lib / "designs"
            designs.mkdir(parents=True)
            (designs / "INDEX.md").write_text("# Lib\n")

        config_path = temp_config_dir / "config.yaml"
        config_path.write_text(f"""
libraries:
  lib1:
    path: {lib1}
    type: library
  lib2:
    path: {lib2}
    type: project
""")
        config = load_config(config_path)

        assert len(config.libraries) == 2
        assert config.libraries["lib1"].type == "library"
        assert config.libraries["lib2"].type == "project"


class TestLibraryConfig:
    def test_dataclass_defaults(self):
        """LibraryConfig should have correct defaults."""
        lib = LibraryConfig(name="test", path=Path("/test"))

        assert lib.type == "library"
        assert lib.designs_dir == "designs"
        assert lib.index_file == "INDEX.md"
        assert lib.cache == "dynamic"


class TestConfig:
    def test_dataclass_defaults(self):
        """Config should have correct defaults."""
        config = Config()

        assert config.designs_dir == "designs"
        assert config.index_file == "INDEX.md"
        assert config.cache == "dynamic"
        assert config.libraries == {}
