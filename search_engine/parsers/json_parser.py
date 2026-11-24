import json
from pathlib import Path
from search_engine.parsers.base import DocumentParser, ParsedDocument
from search_engine.parsers.html_extractor import extract

class JSONDocumentParser(DocumentParser):
    def __init__(self):
        pass

    def parse(self, file_path: Path) -> ParsedDocument:
        return ParsedDocument("","","","")