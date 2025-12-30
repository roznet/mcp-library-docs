"""Discovery logic for finding design documentation in the filesystem."""

import re
from pathlib import Path


def find_current_project(
    cwd: str | Path,
    designs_dir: str = "designs",
    index_file: str = "INDEX.md",
) -> Path | None:
    """
    Walk up from cwd to find the nearest designs/ directory with an index file.

    Args:
        cwd: Current working directory to start from
        designs_dir: Name of the designs directory to look for
        index_file: Name of the index file that must exist

    Returns:
        Path to the project root (parent of designs/), or None if not found
    """
    current = Path(cwd).resolve()
    home = Path.home()

    while current != current.parent:  # Stop at filesystem root
        designs_path = current / designs_dir
        index_path = designs_path / index_file

        if designs_path.is_dir() and index_path.is_file():
            return current

        if current == home:  # Stop at $HOME
            break

        current = current.parent

    return None


def get_project_name(project_path: Path) -> str:
    """Extract project name from path (uses directory name)."""
    return project_path.name


def list_topic_docs(
    project_path: Path,
    designs_dir: str = "designs",
    index_file: str = "INDEX.md",
) -> list[str]:
    """
    List available topic documents in a project's designs directory.

    Args:
        project_path: Path to project root
        designs_dir: Name of the designs directory
        index_file: Name of the index file (excluded from results)

    Returns:
        List of topic names (without .md extension)
    """
    designs_path = project_path / designs_dir

    if not designs_path.is_dir():
        return []

    topics = []
    for file in designs_path.iterdir():
        if file.is_file() and file.suffix == ".md" and file.name != index_file:
            topics.append(file.stem)

    return sorted(topics)


def read_index(
    project_path: Path,
    designs_dir: str = "designs",
    index_file: str = "INDEX.md",
) -> str | None:
    """
    Read the INDEX.md content for a project.

    Args:
        project_path: Path to project root
        designs_dir: Name of the designs directory
        index_file: Name of the index file

    Returns:
        Content of the index file, or None if not found
    """
    index_path = project_path / designs_dir / index_file

    if not index_path.is_file():
        return None

    return index_path.read_text(encoding="utf-8")


def read_topic_doc(
    project_path: Path,
    topic: str,
    designs_dir: str = "designs",
) -> str | None:
    """
    Read a specific topic document.

    Args:
        project_path: Path to project root
        topic: Topic name (without .md extension)
        designs_dir: Name of the designs directory

    Returns:
        Content of the topic file, or None if not found
    """
    topic_path = project_path / designs_dir / f"{topic}.md"

    if not topic_path.is_file():
        return None

    return topic_path.read_text(encoding="utf-8")


def extract_topics_from_index(index_content: str) -> set[str]:
    """
    Extract topic names mentioned in INDEX.md content.

    Looks for patterns like:
    - → Full doc: topic.md
    - → topic.md
    - [link](topic.md)

    Args:
        index_content: Content of the INDEX.md file

    Returns:
        Set of topic names (without .md extension)
    """
    topics = set()

    # Pattern: → Full doc: topic.md or → topic.md
    arrow_pattern = r"→\s*(?:Full doc:\s*)?(\w[\w-]*?)\.md"
    for match in re.finditer(arrow_pattern, index_content):
        topics.add(match.group(1))

    # Pattern: [text](topic.md)
    link_pattern = r"\[.*?\]\((\w[\w-]*?)\.md\)"
    for match in re.finditer(link_pattern, index_content):
        topics.add(match.group(1))

    return topics


def get_index_status(
    project_path: Path,
    designs_dir: str = "designs",
    index_file: str = "INDEX.md",
) -> dict:
    """
    Get the status of INDEX.md compared to actual design doc files.

    Args:
        project_path: Path to project root
        designs_dir: Name of the designs directory
        index_file: Name of the index file

    Returns:
        Dict with:
        - index_content: Current INDEX.md content (or None)
        - existing_docs: List of .md files in designs/
        - in_index: Topics mentioned in INDEX.md
        - missing_from_index: Docs that exist but aren't in INDEX
        - stale_in_index: Topics in INDEX but no file exists
    """
    index_content = read_index(project_path, designs_dir, index_file)
    existing_docs = set(list_topic_docs(project_path, designs_dir, index_file))

    if index_content:
        in_index = extract_topics_from_index(index_content)
    else:
        in_index = set()

    missing_from_index = existing_docs - in_index
    stale_in_index = in_index - existing_docs

    return {
        "index_content": index_content,
        "existing_docs": sorted(existing_docs),
        "in_index": sorted(in_index),
        "missing_from_index": sorted(missing_from_index),
        "stale_in_index": sorted(stale_in_index),
    }
