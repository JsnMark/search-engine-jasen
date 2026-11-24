"""
posting.py



[uint32_t ] [uint32_t   ] [uint32_t       ] [uint32_t ] [uint32_t ]
[docid    ] [title_count] [important_count] [n_pos    ] [pos      ] * n_pos


downside:
    we lose position data related to title and important tokens
"""

import struct

U32 = struct.Struct("<I")
POSTING_HEADER = struct.Struct("<IIII") # docid, title_count, important_count, npos


class Posting():
    def __init__(self, did: int, positions = None, title_count = 0, important_count = 0):
        self.did = did # document id
        self.positions = positions if positions is not None else []
        self.title_count = title_count
        self.important_count = important_count

    @property
    def tf(self):
        return len(self.positions)

    @property
    def nbytes(self):
        """"Size of postings in bytes after serialization"""
        return POSTING_HEADER.size + U32.size * len(self.positions)

    def serialize(self):
        """
        Serializes posting into bytes
        """
        n = len(self.positions)
        header = POSTING_HEADER.pack(self.did, self.title_count, self.important_count, n)
        return header + struct.pack(f"<{n}I", *self.positions)

    @classmethod
    def deserialize(cls, buf, offset: int = 0):
        """
        Decodes one posting starting at buf[offset].
        Returns (posting, offset just past this posting).
        """
        did, title_count, important_count, n = POSTING_HEADER.unpack_from(buf, offset)
        offset += POSTING_HEADER.size
        positions = list(struct.unpack_from(f"<{n}I", buf, offset))
        offset += U32.size * n
        return cls(did, positions, title_count, important_count), offset

    def __eq__(self, other):
        return (isinstance(other, Posting)
                and self.did == other.did
                and self.positions == other.positions
                and self.title_count == other.title_count
                and self.important_count == other.important_count)

    def __repr__(self):
        return (f"Posting(did={self.did}, positions={self.positions}, "
                f"title_count={self.title_count}, important_count={self.important_count})")