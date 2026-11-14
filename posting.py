"""
posting.py

A posting, plus the binary encoding shared by the partial index files and
the final .postings file. Every integer is an unsigned 4-byte
little-endian int (struct format "<I").

Posting:
    [docid u32][title_tf u32][important_tf u32][n_pos u32][pos u32] * n_pos

Partial index record (repeated, sorted by token):
    [token_len u32][token bytes (ASCII)][posting_count u32][byte_len u32][postings...]
"""

import struct

U32 = struct.Struct("<I")
POSTING_HEADER = struct.Struct("<IIII")      # docid, title_tf, important_tf, n_pos
RECORD_COUNTS = struct.Struct("<II")         # posting_count, byte_len


class Posting():
    def __init__(self, did: int, positions=None, title_tf: int = 0, important_tf: int = 0):
        self.did = did # document id
        self.positions = positions if positions is not None else []
        self.title_tf = title_tf
        self.important_tf = important_tf

    @property
    def tf(self):
        return len(self.positions)

    @property
    def nbytes(self):
        """Size of this posting once serialized."""
        return POSTING_HEADER.size + U32.size * len(self.positions)

    def serialize(self) -> bytes:
        n = len(self.positions)
        header = POSTING_HEADER.pack(self.did, self.title_tf, self.important_tf, n)
        return header + struct.pack(f"<{n}I", *self.positions)

    @classmethod
    def deserialize(cls, buf, offset: int = 0):
        """
        Decodes one posting starting at buf[offset].
        Returns (posting, offset just past this posting).
        """
        did, title_tf, important_tf, n = POSTING_HEADER.unpack_from(buf, offset)
        offset += POSTING_HEADER.size
        positions = list(struct.unpack_from(f"<{n}I", buf, offset))
        offset += U32.size * n
        return cls(did, positions, title_tf, important_tf), offset

    def __eq__(self, other):
        return (isinstance(other, Posting)
                and self.did == other.did
                and self.positions == other.positions
                and self.title_tf == other.title_tf
                and self.important_tf == other.important_tf)

    def __repr__(self):
        return (f"Posting(did={self.did}, positions={self.positions}, "
                f"title_tf={self.title_tf}, important_tf={self.important_tf})")


# ------------------ posting lists ------------------------

def serialize_postings(postings) -> bytes:
    """Encodes a list of postings back to back."""
    return b"".join(p.serialize() for p in postings)


def deserialize_postings(buf) -> list:
    """Decodes every posting in buf (buf must hold whole postings only)."""
    postings = []
    offset = 0
    while offset < len(buf):
        posting, offset = Posting.deserialize(buf, offset)
        postings.append(posting)
    if offset != len(buf):
        raise ValueError("posting list bytes are truncated")
    return postings


# ------------------ partial index records ------------------------

def write_partial_record(file, token: str, postings) -> int:
    """
    Writes one partial index record to a file opened in binary mode.
    Returns the number of bytes written.
    """
    return write_partial_record_raw(file, token, len(postings), [serialize_postings(postings)])


def write_partial_record_raw(file, token: str, posting_count: int, chunks) -> int:
    """
    Writes one partial index record whose postings are already serialized.
    chunks is a list of postings byte strings, written back to back (the
    merge passes one chunk per partial the token appeared in).
    Returns the number of bytes written.
    """
    byte_len = sum(len(c) for c in chunks)
    header = pack_token(token) + RECORD_COUNTS.pack(posting_count, byte_len)
    file.write(header)
    for c in chunks:
        file.write(c)
    return len(header) + byte_len


# ------------------ shared low-level helpers ------------------------

def pack_token(token: str) -> bytes:
    """[token_len u32][token ASCII bytes]"""
    token_bytes = token.encode("ascii")
    return U32.pack(len(token_bytes)) + token_bytes


def read_exact(file, n: int) -> bytes:
    data = file.read(n)
    if len(data) != n:
        raise ValueError(f"unexpected end of file: wanted {n} bytes, got {len(data)}")
    return data


def read_token(file):
    """Reads [token_len u32][token]. Returns the token, or None at end of file."""
    first = file.read(U32.size)
    if not first:
        return None
    if len(first) != U32.size:
        raise ValueError("unexpected end of file in record header")
    (token_len,) = U32.unpack(first)
    return read_exact(file, token_len).decode("ascii")


def read_partial_record(file):
    """
    Reads the next partial index record from a file opened in binary mode.
    Returns (token, posting_count, postings_bytes), or None at end of file.
    postings_bytes is left raw so the merge can join lists without decoding;
    use deserialize_postings() to get Posting objects.
    """
    token = read_token(file)
    if token is None:
        return None
    posting_count, byte_len = RECORD_COUNTS.unpack(read_exact(file, RECORD_COUNTS.size))
    postings_bytes = read_exact(file, byte_len)
    return token, posting_count, postings_bytes
