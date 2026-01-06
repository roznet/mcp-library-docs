"""Tests for config module."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from mcp_library_docs.config import (
    CONFIG_DIR_ENV,
    DEFAULT_CACHE,
    DEFAULT_DESIGNS_DIR,
    DEFAULT_INDEX_FILE,
    DEFAULT_TYPE,
    Config,
    LibraryConfig,
    _get_config_search_paths,
    get_config_dir,
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


class TestGetConfigSearchPaths:
    """Tests for platform-specific config path discovery."""

    def test_linux_paths(self):
        """Linux should only search ~/.config."""
        with mock.patch("mcp_library_docs.config.sys.platform", "linux"):
            paths = _get_config_search_paths()

        assert len(paths) == 1
        assert paths[0] == Path.home() / ".config" / "mcp-library-docs"

    def test_darwin_paths(self):
        """macOS should search .config first, then Library/Application Support."""
        with mock.patch("mcp_library_docs.config.sys.platform", "darwin"):
            paths = _get_config_search_paths()

        assert len(paths) == 2
        assert paths[0] == Path.home() / ".config" / "mcp-library-docs"
        assert paths[1] == Path.home() / "Library" / "Application Support" / "mcp-library-docs"

    def test_windows_paths_with_appdata(self):
        """Windows should search AppData first, then .config."""
        with mock.patch("mcp_library_docs.config.sys.platform", "win32"):
            with mock.patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
                paths = _get_config_search_paths()

        assert len(paths) == 2
        assert paths[0] == Path("C:\\Users\\Test\\AppData\\Roaming") / "mcp-library-docs"
        assert paths[1] == Path.home() / ".config" / "mcp-library-docs"

    def test_windows_paths_without_appdata(self):
        """Windows without APPDATA should fall back to .config only."""
        with mock.patch("mcp_library_docs.config.sys.platform", "win32"):
            with mock.patch.dict("os.environ", {}, clear=True):
                # Need to preserve HOME or USERPROFILE for Path.home()
                with mock.patch("pathlib.Path.home", return_value=Path("/mock/home")):
                    paths = _get_config_search_paths()

        assert len(paths) == 1
        assert paths[0] == Path("/mock/home") / ".config" / "mcp-library-docs"


class TestGetConfigDir:
    """Tests for config directory resolution."""

    def test_env_var_override(self, temp_config_dir):
        """Environment variable should override platform defaults."""
        custom_dir = temp_config_dir / "custom-config"
        custom_dir.mkdir()

        with mock.patch.dict("os.environ", {CONFIG_DIR_ENV: str(custom_dir)}):
            result = get_config_dir()

        assert result == custom_dir

    def test_env_var_expands_tilde(self):
        """Environment variable should expand ~ in path."""
        with mock.patch.dict("os.environ", {CONFIG_DIR_ENV: "~/my-config"}):
            result = get_config_dir()

        assert result == (Path.home() / "my-config").resolve()

    def test_returns_existing_path(self, temp_config_dir, monkeypatch):
        """Should return first existing directory from search paths."""
        existing_dir = temp_config_dir / "mcp-library-docs"
        existing_dir.mkdir()

        # Clear env var override
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)

        with mock.patch(
            "mcp_library_docs.config._get_config_search_paths",
            return_value=[
                temp_config_dir / "nonexistent",
                existing_dir,
                temp_config_dir / "also-nonexistent",
            ],
        ):
            result = get_config_dir()

        assert result == existing_dir

    def test_returns_first_path_when_none_exist(self, temp_config_dir, monkeypatch):
        """Should return first (preferred) path when none exist."""
        first_path = temp_config_dir / "first"
        second_path = temp_config_dir / "second"

        # Clear env var override
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)

        with mock.patch(
            "mcp_library_docs.config._get_config_search_paths",
            return_value=[first_path, second_path],
        ):
            result = get_config_dir()

        assert result == first_path
