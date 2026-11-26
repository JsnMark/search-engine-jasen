"""
partial.py

For .pii files
This is the partial index files that will need to be merged. 
They will be kv pairs of tokens to postings. Entries will be 
guaranteed to be sorted by token.

[uint32_t  ] [str   ] [uint32_t      ] [uint32_t               ] [array<Postings> ]
[token_len ] [token ] [posting_count ] [posting_list_byte_size ] [postings        ]
"""

from typing import BinaryIO
from pathlib import Path
import logging
import struct

from search_engine.posting import Posting
from search_engine.storage.common import pack_str, _Owned

PII_POSTS_META = struct.Struct("<II")

class PiiWriter(_Owned):
    def __init__(self, pii_file: BinaryIO):
        self.pii_file = pii_file
        self._files = (pii_file,)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @property
    def file_name(self):
        return self.pii_file.name

    @classmethod
    def open(cls, path: Path) -> PiiWriter:
        piiWriter = cls(path.open("wb"))
        piiWriter._owns = True
        return piiWriter

    def write_postings(self, token: str, postings: list[Posting]):
        """
        Takes in a list of postings to write to file
        """
        data = b"".join(p.serialize() for p in postings)
        self.write_raw(token, len(postings), data)

    def write_raw(self, token: str, count: int, postings_data: bytes | bytearray):
        """
        Takes in bytes of the posting list to write to file
        """
        result_data = pack_str(token) + PII_POSTS_META.pack(count, len(postings_data)) + postings_data
        self.pii_file.write(result_data) # raises on error



class PiiReader:
    pass