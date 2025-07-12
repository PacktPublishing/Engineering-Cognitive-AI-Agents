"""Transient state path management for chapter-specific directories.

This module provides utilities for managing temporary state across book chapters,
ensuring consistent directory structure and easy cleanup. Directories are only
created when actually needed at runtime.
"""

import shutil
from pathlib import Path

from loguru import logger


class TransientPaths:
    """Manages transient state paths for book chapters.

    Provides path resolution for chapter-specific directories under a root
    temporary directory. Directories are created lazily only when needed.

    Parameters
    ----------
    tmp_root : str, optional
        Root directory for all transient state (default: "./tmp")

    Examples
    --------
    >>> paths = TransientPaths()
    >>> log_path = paths.get_chapter_path("chapter02", "logs")
    >>> chroma_path = paths.get_chapter_path("chapter02", "chroma_db")
    """

    tmp_root: Path

    def __init__(self, tmp_root: str = "./tmp"):
        """Initialize transient paths manager.

        Parameters
        ----------
        tmp_root : str, optional
            Root directory for all transient state
        """
        self.tmp_root = Path(tmp_root)

    def get_chapter_path(
        self, chapter: str, facility: str, create: bool = False
    ) -> Path:
        """Get path for a specific chapter and facility.

        Parameters
        ----------
        chapter : str
            Chapter identifier (e.g., "chapter02")
        facility : str
            Facility name (e.g., "logs", "chroma_db", "cache")
        create : bool, optional
            Whether to create the directory if it doesn't exist (default: False)

        Returns
        -------
        Path
            Full path to the chapter-specific facility directory

        Examples
        --------
        >>> paths = TransientPaths()
        >>> log_path = paths.get_chapter_path("chapter02", "logs")
        >>> print(log_path)
        tmp/chapter02/logs

        >>> # Create the directory when needed
        >>> log_path = paths.get_chapter_path("chapter02", "logs", create=True)
        """
        chapter_path = self.tmp_root / chapter / facility

        if create:
            if not chapter_path.exists():
                chapter_path.mkdir(parents=True, exist_ok=True)

        return chapter_path

    def get_chapter_root(self, chapter: str, create: bool = False) -> Path:
        """Get root directory for a specific chapter.

        Parameters
        ----------
        chapter : str
            Chapter identifier (e.g., "chapter02")
        create : bool, optional
            Whether to create the directory if it doesn't exist (default: False)

        Returns
        -------
        Path
            Root directory for the chapter

        Examples
        --------
        >>> paths = TransientPaths()
        >>> chapter_root = paths.get_chapter_root("chapter02")
        >>> print(chapter_root)
        tmp/chapter02
        """
        chapter_root = self.tmp_root / chapter

        if create:
            chapter_root.mkdir(parents=True, exist_ok=True)

        return chapter_root

    def list_chapters(self) -> list[str]:
        """List all existing chapter directories.

        Returns
        -------
        list[str]
            List of chapter directory names that actually exist

        Examples
        --------
        >>> paths = TransientPaths()
        >>> # Assuming 'tmp/chapter01' and 'tmp/chapter02' exist
        >>> chapters = paths.list_chapters()
        >>> print(chapters)
        ['chapter01', 'chapter02']
        """
        if not self.tmp_root.exists():
            return []

        chapters = [
            d.name
            for d in self.tmp_root.iterdir()
            if d.is_dir() and d.name.startswith("chapter")
        ]
        return sorted(chapters)

    def list_facilities(self, chapter: str) -> list[str]:
        """List all existing facilities for a specific chapter.

        Parameters
        ----------
        chapter : str
            Chapter identifier

        Returns
        -------
        list[str]
            List of facility directory names that actually exist for the chapter

        Examples
        --------
        >>> paths = TransientPaths()
        >>> # Assuming 'tmp/chapter02/logs' and 'tmp/chapter02/chroma_db' exist
        >>> facilities = paths.list_facilities("chapter02")
        >>> print(facilities)
        ['chroma_db', 'logs']
        """
        chapter_root = self.tmp_root / chapter
        if not chapter_root.is_dir():
            return []

        facilities = [d.name for d in chapter_root.iterdir() if d.is_dir()]
        return sorted(facilities)

    def clean_chapter(self, chapter: str) -> None:
        """Remove all transient state for a specific chapter.

        Parameters
        ----------
        chapter : str
            Chapter identifier to clean

        Examples
        --------
        >>> paths = TransientPaths()
        >>> paths.clean_chapter("chapter01")
        """
        chapter_root = self.tmp_root / chapter
        if chapter_root.exists():
            shutil.rmtree(chapter_root)
            pass
        else:
            pass

    def clean_all(self) -> None:
        """Remove all transient state.

        Examples
        --------
        >>> paths = TransientPaths()
        >>> paths.clean_all()
        """
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
            pass
        else:
            pass

    def get_chapter_config(self, chapter: str) -> dict[str, str]:
        """Get environment variable style config for a chapter.

        Parameters
        ----------
        chapter : str
            Chapter identifier

        Returns
        -------
        dict[str, str]
            Dictionary with standard facility paths as strings

        Examples
        --------
        >>> paths = TransientPaths()
        >>> config = paths.get_chapter_config("chapter02")
        >>> print(config["LOG_PATH"])
        tmp/chapter02/logs
        """
        return {
            "LOG_PATH": str(self.get_chapter_path(chapter, "logs")),
            "CHROMA_PATH": str(self.get_chapter_path(chapter, "chroma_db")),
            "CACHE_PATH": str(self.get_chapter_path(chapter, "cache")),
            "DATA_PATH": str(self.get_chapter_path(chapter, "data")),
            "CHAPTER_ROOT": str(self.get_chapter_root(chapter)),
        }


# Singleton instance for easy importing
_transient_paths = TransientPaths()


def get_chapter_path(chapter: str, facility: str, create: bool = False) -> Path:
    """Convenience function to get chapter-specific facility path.

    Parameters
    ----------
    chapter : str
        Chapter identifier (e.g., "chapter02")
    facility : str
        Facility name (e.g., "logs", "chroma_db")
    create : bool, optional
        Whether to create the directory if it doesn't exist (default: False)

    Returns
    -------
    Path
        Full path to the chapter-specific facility directory

    Examples
    --------
    >>> log_path = get_chapter_path("chapter02", "logs", create=True)
    >>> chroma_path = get_chapter_path("chapter02", "chroma_db", create=True)
    """
    return _transient_paths.get_chapter_path(chapter, facility, create)


def get_chapter_config(chapter: str) -> dict[str, str]:
    """Convenience function to get environment config for a chapter.

    Parameters
    ----------
    chapter : str
        Chapter identifier

    Returns
    -------
    dict[str, str]
        Dictionary with standard facility paths as strings

    Examples
    --------
    >>> config = get_chapter_config("chapter02")
    >>> log_path = config["LOG_PATH"]
    >>> chroma_path = config["CHROMA_PATH"]
    """
    return _transient_paths.get_chapter_config(chapter)


def clean_chapter(chapter: str) -> None:
    """Convenience function to clean a chapter's transient state.

    Parameters
    ----------
    chapter : str
        Chapter identifier to clean

    Examples
    --------
    >>> clean_chapter("chapter02")
    """
    _transient_paths.clean_chapter(chapter)


def clean_all() -> None:
    """Convenience function to clean all transient state.

    Examples
    --------
    >>> clean_all()
    """
    _transient_paths.clean_all()
