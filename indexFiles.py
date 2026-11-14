"""
indexFiles.py

Entry formats for the final index files (all ints are little-endian u32):

.postings:        every token's posting list back to back, in sorted token order
.postingsIdx:     [token_len][token][offset][byte_len][posting_count]    repeated, sorted by token
                  (offset/byte_len locate the token's list in .postings)
.postingsIdxIdx:  [token_len][token][postingsIdx_offset]                 every X-th .postingsIdx entry
"""

import struct

from posting import pack_token, read_token, read_exact

IDX_META = struct.Struct("<III")     # offset, byte_len, posting_count
IDX_IDX_META = struct.Struct("<I")   # postingsIdx_offset


def write_idx_entry(file, token: str, offset: int, byte_len: int, posting_count: int) -> int:
    """Writes one .postingsIdx entry. Returns the number of bytes written."""
    entry = pack_token(token) + IDX_META.pack(offset, byte_len, posting_count)
    file.write(entry)
    return len(entry)


def read_idx_entry(file):
    """Returns (token, offset, byte_len, posting_count), or None at end of file."""
    token = read_token(file)
    if token is None:
        return None
    return (token, *IDX_META.unpack(read_exact(file, IDX_META.size)))


def write_idx_idx_entry(file, token: str, idx_offset: int) -> int:
    """Writes one .postingsIdxIdx entry. Returns the number of bytes written."""
    entry = pack_token(token) + IDX_IDX_META.pack(idx_offset)
    file.write(entry)
    return len(entry)


def read_idx_idx_entry(file):
    """Returns (token, postingsIdx_offset), or None at end of file."""
    token = read_token(file)
    if token is None:
        return None
    (idx_offset,) = IDX_IDX_META.unpack(read_exact(file, IDX_IDX_META.size))
    return token, idx_offset
