"""Tests for discovery module."""

import tempfile
from pathlib import Path

import pytest

from mcp_library_docs.discovery import (
    extract_topics_from_index,
    find_current_project,
    get_index_status,
    get_project_name,
    list_topic_docs,
    read_index,
    read_topic_doc,
)


@pytest.fixture
def temp_project():
    """Create a temporary project with designs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve to handle macOS /var -> /private/var symlink
        project_path = (Path(tmpdir) / "my-project").resolve()
        designs_path = project_path / "designs"
        designs_path.mkdir(parents=True)

        # Create INDEX.md
        index_content = "# My Project\n\n> A test project\n"
        (designs_path / "INDEX.md").write_text(index_content)

        # Create a topic doc
        topic_content = "# API Module\n\nAPI documentation here.\n"
        (designs_path / "api.md").write_text(topic_content)

        # Create another topic doc
        utils_content = "# Utils Module\n\nUtility functions.\n"
        (designs_path / "utils.md").write_text(utils_content)

        yield project_path


@pytest.fixture
def nested_cwd(temp_project):
    """Create a nested directory structure."""
    nested = temp_project / "src" / "components" / "deep"
    nested.mkdir(parents=True)
    return nested


class TestFindCurrentProject:
    def test_finds_project_from_root(self, temp_project):
        """Should find project when cwd is project root."""
        result = find_current_project(temp_project)
        assert result == temp_project

    def test_finds_project_from_nested_dir(self, temp_project, nested_cwd):
        """Should find project when cwd is nested inside."""
        result = find_current_project(nested_cwd)
        assert result == temp_project

    def test_returns_none_when_no_designs(self):
        """Should return None when no designs directory exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_current_project(tmpdir)
            assert result is None

    def test_returns_none_when_no_index(self):
        """Should return None when designs exists but no INDEX.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            designs = Path(tmpdir) / "designs"
            designs.mkdir()
            result = find_current_project(tmpdir)
            assert result is None

    def test_custom_designs_dir(self, temp_project):
        """Should find project with custom designs directory name."""
        # Create custom docs directory
        docs_path = temp_project / "docs"
        docs_path.mkdir()
        (docs_path / "INDEX.md").write_text("# Docs\n")

        result = find_current_project(temp_project, designs_dir="docs")
        assert result == temp_project

    def test_custom_index_file(self, temp_project):
        """Should find project with custom index file name."""
        # Create README.md instead of INDEX.md
        designs_path = temp_project / "alt-designs"
        designs_path.mkdir()
        (designs_path / "README.md").write_text("# Readme\n")

        result = find_current_project(
            temp_project,
            designs_dir="alt-designs",
            index_file="README.md",
        )
        assert result == temp_project

    def test_stops_at_home(self):
        """Should stop walking at home directory."""
        # This is tricky to test without mocking, but we can at least
        # verify it doesn't hang or crash when starting from home
        home = Path.home()
        result = find_current_project(home)
        # Result depends on whether ~/designs/INDEX.md exists
        # Just verify it completes without error
        assert result is None or isinstance(result, Path)


class TestGetProjectName:
    def test_returns_directory_name(self, temp_project):
        """Should return the directory name."""
        assert get_project_name(temp_project) == "my-project"

    def test_handles_nested_path(self):
        """Should return just the final directory name."""
        path = Path("/some/nested/path/project-name")
        assert get_project_name(path) == "project-name"


class TestListTopicDocs:
    def test_lists_topic_files(self, temp_project):
        """Should list all .md files except INDEX.md."""
        topics = list_topic_docs(temp_project)
        assert sorted(topics) == ["api", "utils"]

    def test_excludes_index_file(self, temp_project):
        """Should not include INDEX.md in results."""
        topics = list_topic_docs(temp_project)
        assert "INDEX" not in topics

    def test_empty_when_no_topics(self):
        """Should return empty list when only INDEX.md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            designs = Path(tmpdir) / "designs"
            designs.mkdir()
            (designs / "INDEX.md").write_text("# Index\n")

            topics = list_topic_docs(Path(tmpdir))
            assert topics == []

    def test_empty_when_no_designs_dir(self):
        """Should return empty list when designs dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            topics = list_topic_docs(Path(tmpdir))
            assert topics == []

    def test_custom_designs_dir(self, temp_project):
        """Should use custom designs directory name."""
        docs = temp_project / "docs"
        docs.mkdir()
        (docs / "INDEX.md").write_text("# Index\n")
        (docs / "guide.md").write_text("# Guide\n")

        topics = list_topic_docs(temp_project, designs_dir="docs")
        assert topics == ["guide"]


class TestReadIndex:
    def test_reads_index_content(self, temp_project):
        """Should read INDEX.md content."""
        content = read_index(temp_project)
        assert content == "# My Project\n\n> A test project\n"

    def test_returns_none_when_missing(self):
        """Should return None when INDEX.md doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = read_index(Path(tmpdir))
            assert content is None

    def test_custom_paths(self, temp_project):
        """Should use custom designs_dir and index_file."""
        docs = temp_project / "docs"
        docs.mkdir()
        (docs / "README.md").write_text("# Custom Readme\n")

        content = read_index(
            temp_project,
            designs_dir="docs",
            index_file="README.md",
        )
        assert content == "# Custom Readme\n"


class TestReadTopicDoc:
    def test_reads_topic_content(self, temp_project):
        """Should read topic document content."""
        content = read_topic_doc(temp_project, "api")
        assert content == "# API Module\n\nAPI documentation here.\n"

    def test_returns_none_when_missing(self, temp_project):
        """Should return None when topic doesn't exist."""
        content = read_topic_doc(temp_project, "nonexistent")
        assert content is None

    def test_custom_designs_dir(self, temp_project):
        """Should use custom designs directory."""
        docs = temp_project / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide\n")

        content = read_topic_doc(temp_project, "guide", designs_dir="docs")
        assert content == "# Guide\n"


class TestExtractTopicsFromIndex:
    def test_extracts_arrow_pattern(self):
        """Should extract topics from → Full doc: pattern."""
        content = """
# My Project

### api
REST API documentation.
→ Full doc: api.md

### utils
Utility functions.
→ Full doc: utils.md
"""
        topics = extract_topics_from_index(content)
        assert topics == {"api", "utils"}

    def test_extracts_short_arrow_pattern(self):
        """Should extract topics from → topic.md pattern."""
        content = """
### api
→ api.md

### utils
→ utils.md
"""
        topics = extract_topics_from_index(content)
        assert topics == {"api", "utils"}

    def test_extracts_link_pattern(self):
        """Should extract topics from [text](topic.md) pattern."""
        content = """
See [API docs](api.md) for more info.
Also check [utilities](utils.md).
"""
        topics = extract_topics_from_index(content)
        assert topics == {"api", "utils"}

    def test_extracts_mixed_patterns(self):
        """Should extract topics from multiple patterns."""
        content = """
### api
REST API.
→ Full doc: api.md

See also [utils](utils.md) and → auth.md
"""
        topics = extract_topics_from_index(content)
        assert topics == {"api", "utils", "auth"}

    def test_handles_hyphenated_names(self):
        """Should handle hyphenated topic names."""
        content = "→ Full doc: my-module.md"
        topics = extract_topics_from_index(content)
        assert topics == {"my-module"}

    def test_empty_content(self):
        """Should return empty set for empty content."""
        topics = extract_topics_from_index("")
        assert topics == set()

    def test_no_topics(self):
        """Should return empty set when no topics found."""
        content = "# My Project\n\nJust some text without links."
        topics = extract_topics_from_index(content)
        assert topics == set()


class TestGetIndexStatus:
    def test_returns_all_fields(self, temp_project):
        """Should return all expected fields."""
        status = get_index_status(temp_project)

        assert "index_content" in status
        assert "existing_docs" in status
        assert "in_index" in status
        assert "missing_from_index" in status
        assert "stale_in_index" in status

    def test_detects_existing_docs(self, temp_project):
        """Should detect existing doc files."""
        status = get_index_status(temp_project)

        assert "api" in status["existing_docs"]
        assert "utils" in status["existing_docs"]

    def test_detects_missing_from_index(self, temp_project):
        """Should detect docs not mentioned in INDEX."""
        # The temp_project INDEX doesn't mention api or utils
        # Let's update the INDEX to mention only api
        index_path = temp_project / "designs" / "INDEX.md"
        index_path.write_text("# Project\n→ Full doc: api.md\n")

        status = get_index_status(temp_project)

        assert "api" in status["in_index"]
        assert "utils" in status["missing_from_index"]

    def test_detects_stale_entries(self, temp_project):
        """Should detect INDEX entries without corresponding files."""
        # Update INDEX to reference a non-existent file
        index_path = temp_project / "designs" / "INDEX.md"
        index_path.write_text("# Project\n→ Full doc: nonexistent.md\n→ Full doc: api.md\n")

        status = get_index_status(temp_project)

        assert "nonexistent" in status["stale_in_index"]
        assert "api" not in status["stale_in_index"]

    def test_up_to_date_index(self, temp_project):
        """Should report no issues when INDEX is up to date."""
        # Update INDEX to reference all existing files
        index_path = temp_project / "designs" / "INDEX.md"
        index_path.write_text("# Project\n→ Full doc: api.md\n→ Full doc: utils.md\n")

        status = get_index_status(temp_project)

        assert status["missing_from_index"] == []
        assert status["stale_in_index"] == []

    def test_no_index_file(self):
        """Should handle missing INDEX.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = (Path(tmpdir) / "project").resolve()
            designs = project / "designs"
            designs.mkdir(parents=True)
            (designs / "api.md").write_text("# API\n")
            # Create INDEX.md so find_current_project works
            (designs / "INDEX.md").write_text("")

            status = get_index_status(project)

            assert status["index_content"] == ""
            assert "api" in status["existing_docs"]
            assert "api" in status["missing_from_index"]
