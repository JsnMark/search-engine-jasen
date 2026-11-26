"""
docTable.py

manages .docs and .urls

doc entry format
[uint64_t  ] [uint32_t] [uint32_t   ]
[url_offset] [url_len ] [token_count]

url entry format 
[str]
[url]
"""

import struct
from typing import BinaryIO

DOC_RECORD = struct.Struct("<QII") 

class DocTableWriter:
    def __init__(self, docs_file: BinaryIO, urls_file: BinaryIO):
        self.docs_file = docs_file
        self.urls_file = urls_file
        self.url_offset = 0

    def write(self, url: str, token_count: int):
        """
        Writes to .urls and .docs
        """
        url_bytes = url.encode("utf-8")
        self.urls_file.write(url_bytes)
        self.docs_file.write(DOC_RECORD.pack(self.url_offset, len(url_bytes), token_count))
        self.url_offset += len(url_bytes)

# TODO
class DocTableReader:
    pass