"""
searchEngine.py
"""

from abc import ABC, abstractmethod

from search_engine.storage.docTable import DocTableReader
from search_engine.storage.inverted import InvIndexReader

from pathlib import Path
OUT_ROOT_PATH         = "out"

class SearchEngine(ABC):
    def __init__(self, name: str):
        self.docTableReader = DocTableReader.open(Path(OUT_ROOT_PATH) / name, 
                                                  name)
        self.invIndexReader = InvIndexReader()

    """
    Searches on inverted index, returning the top_k results
    """
    @abstractmethod
    def search(self, query: str, top_k=5) -> str:
        pass