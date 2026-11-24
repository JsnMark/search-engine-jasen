"""
base.py

Abstract Class for document parserss
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ParsedDocument:
    url: str
    title: str
    important: str
    body: str

class DocumentParser(ABC):
    @abstractmethod 
    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Reads a file and returns its text fields
        """

