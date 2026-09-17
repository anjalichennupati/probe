from abc import ABC, abstractmethod
import os
from typing import Dict, Optional

from probe.model.models import ParseResult
from probe.utils.logging import get_logger

logger = get_logger("probe.parser.base")

# Standard extension to language mapping
EXTENSION_MAP: Dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}


def detect_language(file_path: str) -> Optional[str]:
    """Detects programming language identifier from file extension."""
    _, ext = os.path.splitext(file_path)
    lang = EXTENSION_MAP.get(ext.lower())
    if lang:
        logger.debug(f"Detected language [bold green]{lang}[/bold green] for [cyan]{file_path}[/cyan]")
    else:
        logger.debug(f"No language detected for [yellow]{file_path}[/yellow]")
    return lang


class BaseParser(ABC):
    """Abstract base class for language parsers."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Returns the canonical language identifier (e.g., 'python')."""
        pass

    def load_language(self, language: Optional[str] = None) -> None:
        """Loads and prepares language grammar or parser configuration."""
        target_lang = language or self.language
        logger.info(f"Loading parser configuration for [bold cyan]{target_lang}[/bold cyan]")

    @abstractmethod
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParseResult:
        """Parses a single file path or source content string into a ParseResult."""
        pass


class ParserRegistry:
    """Registry to manage and dispatch language parsers."""

    def __init__(self) -> None:
        self._parsers: Dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """Registers a parser instance for its language."""
        lang = parser.language
        parser.load_language(lang)
        self._parsers[lang] = parser
        logger.info(f"Registered parser [bold green]{parser.__class__.__name__}[/bold green] for language [bold cyan]{lang}[/bold cyan]")

    def get_parser(self, language: str) -> Optional[BaseParser]:
        """Retrieves a parser registered for a specific language."""
        return self._parsers.get(language)

    def get_parser_for_file(self, file_path: str) -> Optional[BaseParser]:
        """Detects file language and returns the matching registered parser."""
        lang = detect_language(file_path)
        if not lang:
            return None
        return self.get_parser(lang)
