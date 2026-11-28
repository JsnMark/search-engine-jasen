"""
common.py
"""

import struct
from typing import BinaryIO

U32 = struct.Struct("<I")
U64 = struct.Struct("<Q")

def pack_str(s: str):
    """
    Takes a string and returns bytes in format
    [uint32][string  ]
    [strlen][strbytes]
    """
    b = s.encode("utf-8")
    result_bytes = bytearray()
    result_bytes += U32.pack(len(b))
    result_bytes += b
    return result_bytes


# Read helpers
# "what" is only used for error messages, e.g. "lex entry 12 token".

def _fname(f: BinaryIO) -> str:
    return getattr(f, "name", "<stream>")

def read_exact(f: BinaryIO, n: int, what: str = "bytes") -> bytes:
    """
    Reads exactly n bytes or raises ValueError (truncated file)
    """
    pos = f.tell()
    data = f.read(n)
    if len(data) != n:
        raise ValueError(f"{_fname(f)}: truncated reading {what} at offset {pos} "
                         f"(expected {n} bytes, got {len(data)})")
    return data


def read_struct(f: BinaryIO, st: struct.Struct, what: str = "struct") -> tuple:
    """
    Reads and unpacks one fixed-size struct, e.g.
        posts_offset, nbytes, count = read_struct(f, IDX_POSTS_META, "idx meta")
    """
    return st.unpack(read_exact(f, st.size, what))


def read_u32(f: BinaryIO, what: str = "u32") -> int:
    return read_struct(f, U32, what)[0]


def read_u64(f: BinaryIO, what: str = "u64") -> int:
    return read_struct(f, U64, what)[0]


def read_str(f: BinaryIO, what: str = "string") -> str:
    """
    Reads a string written by pack_str:
    [uint32][string  ]
    [strlen][strbytes]
    """
    n = read_u32(f, f"{what} length")
    return read_exact(f, n, what).decode("utf-8")


def try_read_str(f: BinaryIO, what: str = "string") -> str | None:
    """
    Like read_str, but returns None on a clean EOF (no bytes left at all).
    Use this for the first field of a record when scanning a file with no
    entry count (.pii, .idx). A partial length prefix is still an error.
    """
    pos = f.tell()
    b = f.read(U32.size)
    if not b:
        return None
    if len(b) != U32.size:
        raise ValueError(f"{_fname(f)}: truncated reading {what} length at offset {pos} "
                         f"(wanted {U32.size} bytes, got {len(b)})")
    return read_exact(f, U32.unpack(b)[0], what).decode("utf-8")


class _Owned:
    """
    Context-manager boilerplate: close the files only if we opened them.
    """
    _files: tuple[BinaryIO, ...] = ()
    _owns = False

    def close(self):
        if self._owns:
            for f in self._files:
                f.close()

    def __enter__(self): 
        return self
    
    def __exit__(self, *exc): 
        self.close()
        return False