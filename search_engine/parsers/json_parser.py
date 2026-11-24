"""
json_parser.py

Assume all json files have [url, content]
"""

import json
from pathlib import Path
from urllib.parse import urldefrag

from search_engine.parsers.base import DocumentParser, ParsedDocument
from search_engine.parsers.html_extractor import extract

class JSONDocumentParser(DocumentParser):
    def __init__(self):
        pass

    def parse(self, file_path: Path) -> ParsedDocument:
        with file_path.open("r", encoding="utf-8") as f:
            doc = json.load(f)
        url, _ = urldefrag(doc["url"])
        return ParsedDocument(url, **extract(doc["content"]))