"""
partial.py

For .pii files
This is the partial index files that will need to be merged. 
They will be kv pairs of tokens to postings. Entries will be 
guaranteed to be sorted by token.

[uint32_t  ] [str   ] [uint32_t      ] [uint32_t               ] [array<Postings> ]
[token_len ] [token ] [posting_count ] [posting_list_byte_size ] [postings        ]
"""

from typing import BinaryIO, NamedTuple
from pathlib import Path
import logging
import struct

from search_engine.posting import Posting
from search_engine.storage.common import pack_str, _Owned, U32

PII_POSTS_META = struct.Struct("<II") # posting_count, posting_list_byte_size

class PiiEntry(NamedTuple):
    token: str
    count: int
    postings_data: bytes

class PiiWriter(_Owned):
    def __init__(self, pii_file: BinaryIO):
        self.pii_file = pii_file
        self._files = (pii_file,)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @property
    def file_name(self):
        return getattr(self.pii_file, "name", None)

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
        if not token:
            self.logger.error("No token")
            raise ValueError("No token")
        result_data = pack_str(token) + PII_POSTS_META.pack(count, len(postings_data)) + postings_data
        self.pii_file.write(result_data) # raises on error



class PiiReader(_Owned):
    def __init__(self, pii_file: BinaryIO):
        self.pii_file = pii_file
        self._files = (pii_file,)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @property
    def file_name(self) -> str | None:
        return getattr(self.pii_file, "name", None)

    @classmethod
    def open(cls, path: Path) -> PiiReader:
        piiReader = cls(path.open("rb"))
        piiReader._owns = True
        return piiReader

    def _read_token_header(self):
        b = self.pii_file.read(U32.size)
        if not b: # clean EOF
            return None
        token_bytes = self._read_exact_len(U32.unpack(b)[0] if len(b) == U32.size else -1)
        token = token_bytes.decode("utf-8")
        if not token:
            self.logger.error("No token was read")
            raise ValueError("No token was read")
        pl_posting_count, pl_byte_len = PII_POSTS_META.unpack(self._read_exact_len(PII_POSTS_META.size))

        # file now points at posting bytes, need to read pl_byte_len later
        return token, pl_posting_count, pl_byte_len 

    def _read_exact_len(self, n):
        data = self.pii_file.read(n) if n >= 0 else b""
        if len(data) != n:
            raise ValueError(f"{self.file_name or "<stream>"}: truncated .pii (wanted {n} bytes, got {len(data)})")
        return data

    def __iter__(self):
        """
        Reads next kv pair of the .pii file
        """
        while (hdr := self._read_token_header()) is not None:
            token, count, nbytes = hdr
            yield PiiEntry(token, count, self._read_exact_len(nbytes))