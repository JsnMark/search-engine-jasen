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
        # same location the Indexer writes to: out/<name>/<name>.*
        out_dir = Path(OUT_ROOT_PATH) / name
        self.docTableReader = DocTableReader.open(out_dir, name)
        self.invIndexReader = InvIndexReader.open(out_dir, name)

    """
    Searches on inverted index, returning the top_k results
    """
    @abstractmethod
    def search(self, query: str, top_k=5) -> str:
        pass