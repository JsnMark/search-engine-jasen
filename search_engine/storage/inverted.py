"""
inverted.py

for .posts, .idx, .lex

.idx
[uint32_t ] [str  ] [uint64_t    ] [uint32_t               ] [uint32_t     ]
[token_len] [token] [posts_offset] [posting_list_byte_size ] [posting_count]


"""

import logging
import struct
from typing import BinaryIO, NamedTuple
from pathlib import Path

from search_engine.posting import Posting
from search_engine.storage.common import pack_str, _Owned, U32, U64

# class IdxEntry(NamedTuple):
#     token: str
#     posts_offset: int
#     postings_byte_size: int
#     postings_count: int

IDX_POSTS_META = struct.Struct("<QII") # posts_offset, posting_list_byte_size, posting_count
POSTING_LIST_FEXT     = ".posts"
INDEX_FEXT            = ".idx" 
LEXICON_FEXT          = ".lex"


# .posts, .idx, .lex
class InvIndexWriter(_Owned):
    def __init__(self, posts_file: BinaryIO, idx_file: BinaryIO, lex_file: BinaryIO, interval=128):
        self.posts_file, self.idx_file, self.lex_file = posts_file, idx_file, lex_file
        self.interval = interval
        self._files = (posts_file, idx_file, lex_file)
        self._lex = [] # in memory lex until the end
        self._n = 0 # number of total tokens written
        self._closed = False # set by close(); guards against writing .lex twice
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @property
    def posts_file_name(self):
        return getattr(self.posts_file, "name", None)
    @property
    def idx_file_name(self):
        return getattr(self.idx_file, "name", None)
    @property
    def lex_file_name(self):
        return getattr(self.lex_file, "name", None)

    @classmethod
    def open(cls, out_dir: Path, name: str, interval=128):
        invIndexWriter = cls(
            open(out_dir / f"{name}{POSTING_LIST_FEXT}", "wb"),
            open(out_dir / f"{name}{INDEX_FEXT}", "wb"),
            open(out_dir / f"{name}{LEXICON_FEXT}", "wb"),
            interval,
        )
        invIndexWriter._owns = True
        return invIndexWriter

    def write(self, token: str, count: int, postings_data: bytes):
        """
        Write to .posts and .idx, save lex to in memory
        """
        if self._closed:
            raise ValueError("write() called after close()")
        if not token:
            raise ValueError("empty token")
        posts_pos, idx_pos = self.posts_file.tell(), self.idx_file.tell()
        self.posts_file.write(postings_data)
        self.idx_file.write(pack_str(token) + IDX_POSTS_META.pack(posts_pos, len(postings_data), count))
        if self._n % self.interval == 0:
            self._lex.append(pack_str(token) + U64.pack(idx_pos))
        self._n += 1

    def close(self):
        """
        Finishes the index: writes the buffered .lex entries, then closes the
        files if this writer opened them. Must always be called (or use `with`),
        even with borrowed files, or .lex is never written. Safe to call twice.
        """
        if self._closed:
            return
        self._closed = True
        self.lex_file.write(U32.pack(len(self._lex)) + b"".join(self._lex))
        super().close()



class InvIndexReader:
    pass